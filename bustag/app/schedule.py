'''
定时任务调度模块
使用 javbus-api 替代原有的 aspider 爬虫
'''
import threading
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from bustag.spider import bus_spider
from bustag.util import logger, APP_CONFIG

scheduler = None


def download(fanhaos=None, movie_type='mixed'):
    '''
    下载更新数据

    Args:
        fanhaos: list - 指定要下载的番号列表，为 None 则批量下载
        movie_type: str - 'normal'=有码, 'uncensored'=无码, 'mixed'=混合（自动判断）
    '''
    print('start download')
    if fanhaos:
        logger.info(f'Downloading specified fanhaos: {len(fanhaos)} items, movie_type={movie_type}')
        bus_spider.download_by_fanhaos(fanhaos, movie_type=movie_type)
    else:
        pages = int(APP_CONFIG.get('download.count', 10))
        bus_spider.download_movies(pages=pages)

    # 下载完成后尝试推荐
    try:
        import bustag.model.classifier as clf
        clf.recommend()
    except FileNotFoundError:
        print('还没有训练好的模型, 无法推荐')


def start_scheduler():
    '''
    启动定时调度器
    '''
    global scheduler

    interval = int(APP_CONFIG.get('download.interval', 1800))

    scheduler = BackgroundScheduler()

    # 启动后立即执行一次
    t1 = datetime.now() + timedelta(seconds=1)
    date_trigger = DateTrigger(run_date=t1)
    scheduler.add_job(download, trigger=date_trigger)

    # 定时执行
    int_trigger = IntervalTrigger(seconds=interval)
    scheduler.add_job(download, trigger=int_trigger)

    scheduler.start()
    logger.info(f'Scheduler started, interval={interval}s')


def add_download_job(fanhaos):
    '''
    添加指定番号的下载任务

    Args:
        fanhaos: list - 番号列表
    '''
    t1 = datetime.now() + timedelta(seconds=10)
    date_trigger = DateTrigger(run_date=t1)
    if scheduler:
        scheduler.add_job(download, trigger=date_trigger, args=(fanhaos,))
        logger.info(f'Added download job for {len(fanhaos)} fanhaos')
    else:
        logger.warning('Scheduler not running, downloading directly')
        download(fanhaos)