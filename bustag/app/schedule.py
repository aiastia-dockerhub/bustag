'''
定时任务调度模块
使用 javbus-api 替代原有的 aspider 爬虫
'''
import threading
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from bustag.spider import bus_spider
from bustag.util import logger, APP_CONFIG

scheduler = None


def download(fanhaos=None):
    '''
    下载更新数据

    Args:
        fanhaos: list - 指定要下载的番号列表，为 None 则批量下载
    '''
    print('start download')
    if fanhaos:
        logger.info(f'Downloading specified fanhaos: {len(fanhaos)} items')
        bus_spider.download_by_fanhaos(fanhaos)
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
    支持 interval（每隔N秒）和 cron（每天固定时间）两种调度模式
    '''
    global scheduler

    schedule_mode = APP_CONFIG.get('download.schedule_mode', 'interval').lower().strip()

    scheduler = BackgroundScheduler()

    # 启动后立即执行一次
    t1 = datetime.now() + timedelta(seconds=1)
    date_trigger = DateTrigger(run_date=t1)
    scheduler.add_job(download, trigger=date_trigger)

    if schedule_mode == 'cron':
        # 定时模式：每天固定时间执行
        times = APP_CONFIG.get('download.schedule_times', '8,20')
        hours = [int(h.strip()) for h in times.split(',')]
        cron_trigger = CronTrigger(hour=hours)
        scheduler.add_job(download, trigger=cron_trigger)
        logger.info(f'Scheduler started (cron mode), daily at hours: {hours}')
    else:
        # 间隔模式：每隔 N 秒执行
        interval = int(APP_CONFIG.get('download.interval', 1800))
        int_trigger = IntervalTrigger(seconds=interval)
        scheduler.add_job(download, trigger=int_trigger)
        logger.info(f'Scheduler started (interval mode), interval={interval}s')

    scheduler.start()


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