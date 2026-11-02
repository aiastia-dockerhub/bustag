"""Offline reproducible benchmarks; always uses a disposable database.

Run: .venv/bin/python scripts/benchmark_performance.py --sizes 10000 100000
"""
import argparse
from datetime import datetime, timedelta
import json
import logging
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time


def measure(action, repeats=15):
    samples = []
    for _ in range(repeats):
        started = time.perf_counter()
        action()
        samples.append((time.perf_counter() - started) * 1000)
    samples.sort()
    return {'median_ms': round(statistics.median(samples), 3),
            'p95_ms': round(samples[min(len(samples)-1, int(len(samples)*0.95))], 3)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sizes', nargs='+', type=int, default=[10000, 100000])
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    with tempfile.TemporaryDirectory(prefix='bustag-benchmark-') as folder:
        data = Path(folder)
        (data / 'config.ini').write_text('[database]\ntype=sqlite\n[download]\napi_interval=0\n')
        os.environ['BUSTAG_DATA_DIR'] = folder
        os.environ.pop('TESTING', None)
        from bustag.spider import db as store
        from bustag.app.api import _enrich_items_with_rate
        from peewee import JOIN, fn
        from scipy import sparse
        import numpy as np
        logging.getLogger('peewee').setLevel(logging.WARNING)
        results = []
        for size in args.sizes:
            store.db.close()
            store.db.init(str(data / f'{size}.db'))
            store.init()
            now = datetime(2026, 11, 2, 12)
            with store.db.atomic():
                for start in range(0, size, 100):
                    rows = []
                    rates = []
                    for index in range(start, min(start + 100, size)):
                        stamp = now - timedelta(days=index % 365, seconds=index % 86400)
                        fanhao = f'BENCH-{index:06}'
                        rows.append({'fanhao': fanhao, 'title': f'Movie {index}',
                                     'url': f'https://example.com/{index}', 'add_date': stamp,
                                     'add_day': stamp.date(), 'release_date': stamp.date(),
                                     'movie_type': 'normal',
                                     'meta_info': json.dumps({'cover_img_url': 'https://example.com/img.jpg'})})
                        if index % 3:
                            rates.append({'item': fanhao, 'rate_type': 2, 'rate_value': index % 2})
                    store.Item.insert_many(rows).execute()
                    if rates:
                        store.ItemRate.insert_many(rates).execute()
            old = ('SELECT item.* FROM item LEFT JOIN item_rate ON item_rate.item_id=item.fanhao '
                   'WHERE item_rate.rate_type IS NULL AND item.movie_type="normal" '
                   'ORDER BY DATE(item.add_date) DESC, item.release_date DESC, item.id ASC LIMIT 10')
            new = old.replace('DATE(item.add_date)', 'item.add_day')
            items = list(store.Item.select().limit(50))
            for item in items:
                item.tags_dict = {}
            def old_prediction_batch():
                query = (store.Item.select(store.Item, store.ItemRate)
                         .join(store.ItemRate, JOIN.LEFT_OUTER, attr='item_rate')
                         .where(store.ItemRate.rate_type.is_null())
                         .order_by(fn.DATE(store.Item.add_date).desc(), store.Item.release_date.desc(), store.Item.id))
                query.count()
                batch = store.get_tags_for_items(query.limit(1000))
                for item in batch:
                    store.Item.loadit(item)
                return batch

            result = {
                'rows': size,
                'sort_before': measure(lambda: store.db.execute_sql(old).fetchall()),
                'sort_after': measure(lambda: store.db.execute_sql(new).fetchall()),
                'ratings_50_before': measure(lambda: [store.ItemRate.get_by_fanhao(item.fanhao) for item in items]),
                'ratings_50_after': measure(lambda: _enrich_items_with_rate(items)),
                'prediction_batch_before': measure(lambda: old_prediction_batch(), 5),
                'prediction_batch_after': measure(lambda: store.get_feature_items(page_size=1000), 5),
                'sort_plan_after': store.db.execute_sql('EXPLAIN QUERY PLAN ' + new).fetchall(),
            }
            results.append(result)
        rng = np.random.default_rng(42)
        rows = np.repeat(np.arange(1000), 20)
        cols = rng.integers(0, 10000, size=len(rows))
        matrix = sparse.csr_matrix((np.ones(len(rows), np.float32), (rows, cols)), shape=(1000, 10000))
        memory = {'shape': list(matrix.shape), 'dense_float64_bytes': 1000 * 10000 * 8,
                  'sparse_float32_bytes': matrix.data.nbytes + matrix.indices.nbytes + matrix.indptr.nbytes}
        print(json.dumps({'database': results, 'feature_memory': memory}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
