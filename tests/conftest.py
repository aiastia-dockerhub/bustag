"""All tests run against disposable data, never the user's database or credentials."""
import json
import os
from pathlib import Path
import tempfile

import pytest

_TEST_ROOT = tempfile.TemporaryDirectory(prefix='bustag-tests-')
_TEST_DATA = Path(_TEST_ROOT.name) / 'data'
_TEST_DATA.mkdir()
(_TEST_DATA / 'config.ini').write_text('[database]\ntype=sqlite\n[download]\napi_interval=0\nbatch_interval=0\n')
os.environ['BUSTAG_DATA_DIR'] = str(_TEST_DATA)


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    from bustag import util
    from bustag.spider import db as store
    from bustag.app.tasks import Job
    directory = tmp_path / 'test-data'
    directory.mkdir()
    (directory / 'config.ini').write_text('[database]\ntype=sqlite\n[download]\napi_interval=0\n')
    monkeypatch.setattr(util, 'TESTING', True)
    monkeypatch.setattr(util, 'DATA_PATH', str(directory))
    monkeypatch.setenv('BUSTAG_DATA_DIR', str(directory))
    monkeypatch.setenv('BUSTAG_EXTERNAL_WORKER', '1')
    monkeypatch.delenv('BUSTAG_PASSWORD', raising=False)
    store.db.close()
    store.db.init(str(directory / 'bus.db'))
    store.init()
    store.db.create_tables([Job])
    from bustag.app import api
    api._api_cache.clear()
    yield
    store.db.close()


@pytest.fixture
def seeded_data():
    from datetime import date, datetime, timedelta
    from bustag.spider.db import Item, ItemTag, Tag, ItemRate, RATE_TYPE, db
    with db.atomic():
        genre = Tag.create(type_='genre', value='test-genre', url='/genre/test')
        star = Tag.create(type_='star', value='test-star', url='/star/test')
        for index in range(240):
            fanhao = f'TEST-{index:04d}'
            item = Item.create(fanhao=fanhao, title=f'Movie {index}', url=f'https://example.com/{fanhao}',
                               release_date=date(2025, 1, 1), add_date=datetime.now()-timedelta(days=index % 3),
                               meta_info=json.dumps({'cover_img_url': 'https://example.com/cover.jpg'}))
            ItemTag.create(item=item.fanhao, tag=genre if index % 2 else star)
            ItemRate.create(item=item.fanhao, rate_type=RATE_TYPE.USER_RATE, rate_value=index % 2)
    return Item
