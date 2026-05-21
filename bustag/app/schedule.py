'''
定时任务调度模块
使用 javbus-api 替代原有的 aspider 爬虫
'''
import os
import threading
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from bustag.spider import bus_spider
from bustag.util import logger, APP_CONFIG

# 获取时区：优先使用 TZ 环境变量，默认 Asia/Shanghai
def _get_timezone():
    tz = os.environ.get('TZ', 'Asia/Shanghai')
    try:
        from pytz import timezone
        return timezone(tz)
    except Exception:
        return None

scheduler = None


def download(fanhaos=None, movie_type='mixed'):
    '''
    下载更新数据

    Args:
        fanhaos: list - 指定要下载的番号列表，为 None 则批量下载
        movie_type: str - 'normal'=有码, 'uncensored'=无码, 'mixed'=混合（自动判断）
    '''
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f'===== 开始爬取 [{now_str}] =====')
    saved_count = 0
    if fanhaos:
        logger.info(f'Downloading specified fanhaos: {len(fanhaos)} items, movie_type={movie_type}')
        saved_count = bus_spider.download_by_fanhaos(fanhaos, movie_type=movie_type)
    else:
        pages = int(APP_CONFIG.get('download.count', 10))
        saved_count = bus_spider.download_movies(pages=pages)

    # 只有保存了新影片才运行推荐
    if saved_count > 0:
        try:
            import bustag.model.classifier as clf
            clf.recommend()
        except FileNotFoundError:
            print('还没有训练好的模型, 无法推荐')
        except (KeyError, AttributeError) as e:
            print(f'模型版本不兼容，请重新训练模型。错误: {e}')
    else:
        logger.info('没有新影片保存，跳过推荐')

    end_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f'===== 爬取完成 [{end_str}]，本次保存 {saved_count} 部影片 =====')

    # 输出下次预计执行时间
    if scheduler:
        jobs = scheduler.get_jobs()
        for job in jobs:
            if job.next_run_time:
                next_str = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f'下次爬取预计时间: {next_str}')
                break


def start_scheduler():
    '''
    启动定时调度器
    '''
    global scheduler

    interval = int(APP_CONFIG.get('download.interval', 1800))

    tz = _get_timezone()
    scheduler = BackgroundScheduler(timezone=tz)
    logger.info(f'Scheduler timezone: {tz}')

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