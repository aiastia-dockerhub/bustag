"""Run with python -m bustag.app.worker (one worker per data directory)."""
import datetime
import fcntl
import json
import os
import signal
import time
from bustag.app.tasks import Job, initialize
from bustag.spider.db import db, Item, fn, touch_data
from bustag.util import get_data_path, logger


def execute(job):
    from bustag.model import classifier as clf
    payload = json.loads(job.payload)

    def progress(**values):
        Job.update(progress=json.dumps(values, ensure_ascii=False),
                   updated_at=datetime.datetime.now()).where(Job.id == job.id).execute()

    if job.kind == 'train':
        _, scores = clf.train(progress=progress, full_evaluation=payload.get('full_evaluation', False))
        return {'model_scores': scores}
    if job.kind == 'recommend':
        result = clf.recommend(reset=True, progress=progress)
        if result is None:
            raise RuntimeError('模型任务正在执行，请稍后重试')
        return result
    if job.kind == 'clear':
        return clf.clear_recommend()
    if job.kind == 'preview':
        from bustag.spider import bus_spider
        sources = ([{'type': 'star', 'value': s} for s in payload.get('stars') or []]
                   + [{'type': 'keyword', 'value': k} for k in payload.get('keywords') or []])
        progress(stage='预览候选影片', processed=0)
        return bus_spider.preview_sources(
            sources, pages=payload.get('pages', 1),
            movie_type=payload.get('movie_type'), progress=progress)
    if job.kind == 'download':
        from bustag.spider import bus_spider
        before = Item.select(fn.MAX(Item.id)).scalar() or 0
        fanhaos = payload.get('fanhaos')
        stars = payload.get('stars') or []
        keywords = payload.get('keywords') or []
        if stars or keywords:
            # 按演员 ID / 搜索关键词批量添加（仅含有磁力链接的影片）
            sources = ([{'type': 'star', 'value': s} for s in stars]
                       + [{'type': 'keyword', 'value': k} for k in keywords])
            progress(stage='批量抓取影片', processed=0)
            saved = bus_spider.batch_download(
                sources, pages=payload.get('pages', 1), progress=progress)
        elif fanhaos:
            progress(stage='爬取影片', processed=0)
            saved = bus_spider.download_by_fanhaos(fanhaos, movie_type=payload.get('movie_type', 'mixed'))
        else:
            progress(stage='爬取影片', processed=0)
            saved = bus_spider.download_movies()
        result = {'saved': saved}
        if saved:
            try:
                # New rows first. A full cursor pass also repairs work interrupted by a restart.
                result['recommendation'] = clf.recommend(after_id=before, progress=progress)
                clf.recommend(max_id=before, progress=progress)
            except FileNotFoundError:
                result['warning'] = '还没有训练好的模型，已保存影片，暂未推荐'
        return result
    raise ValueError('未知任务类型')


def run_one():
    job = Job.select().where(Job.state == 'queued').order_by(Job.created_at, Job.id).first()
    if not job:
        return False
    claimed = Job.update(state='running', updated_at=datetime.datetime.now()).where(
        Job.id == job.id, Job.state == 'queued').execute()
    if not claimed:
        return False
    try:
        result = execute(job)
        Job.update(state='succeeded', active_key=None, result=json.dumps(result, ensure_ascii=False),
                   updated_at=datetime.datetime.now()).where(Job.id == job.id).execute()
    except Exception as exc:
        logger.exception('Background %s task failed', job.kind)
        Job.update(state='failed', active_key=None, error=str(exc),
                   updated_at=datetime.datetime.now()).where(Job.id == job.id).execute()
    finally:
        touch_data()
    cutoff = datetime.datetime.now() - datetime.timedelta(days=7)
    Job.delete().where(Job.state.in_(['succeeded', 'failed']), Job.updated_at < cutoff).execute()
    return True


def main():
    os.makedirs(get_data_path('model'), exist_ok=True)
    with open(get_data_path('model/worker.lock'), 'a') as guard:
        try:
            fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return  # A worker already owns this data directory.
        initialize()
        # Never silently retry destructive tasks after a crash.
        Job.update(state='failed', active_key=None, error='服务重启中断了任务，请重新提交',
                   updated_at=datetime.datetime.now()).where(Job.state == 'running').execute()
        stopping = False

        def stop(*_):
            nonlocal stopping
            stopping = True
            raise SystemExit(0)

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        last_cleanup = 0
        while not stopping:
            parent = os.environ.get('BUSTAG_PARENT_PID')
            if parent and os.getppid() != int(parent):
                return
            try:
                with db.connection_context():
                    worked = run_one()
                    if time.monotonic() - last_cleanup > 60:
                        from bustag.app.images import prune_cache
                        prune_cache(force=True)
                        last_cleanup = time.monotonic()
            except Exception:
                logger.exception('Background worker iteration failed')
                worked = False
            if not worked:
                time.sleep(1)


if __name__ == '__main__':
    main()
