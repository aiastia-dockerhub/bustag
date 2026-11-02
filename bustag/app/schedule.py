'''
定时任务调度模块
使用 javbus-api 替代原有的 aspider 爬虫
'''
import os
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
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
    from bustag.app.tasks import submit, ensure_worker
    job = submit('download', {'fanhaos': list(fanhaos) if fanhaos else None,
                              'movie_type': movie_type})
    ensure_worker()
    return job


def start_scheduler():
    '''
    启动定时调度器
    支持两种模式：
    - schedule 模式：指定固定时间点执行，如 schedule = 8:00,12:00,15:00,22:00
    - interval 模式：按固定间隔执行，如 interval = 10800（秒）
    优先使用 schedule 配置，若为空则回退到 interval 模式
    '''
    global scheduler

    tz = _get_timezone()
    scheduler = BackgroundScheduler(timezone=tz)
    logger.info(f'Scheduler timezone: {tz}')

    # 115 token 定时保活：每 30 分钟检查，临期自动刷新（未授权时为 no-op）
    try:
        from bustag.app import open115
        scheduler.add_job(open115.keepalive, IntervalTrigger(seconds=1800),
                          id='open115_keepalive')
    except Exception as e:
        logger.warning(f'115 保活任务注册失败: {e}')

    # 启动后立即执行一次
    t1 = datetime.now() + timedelta(seconds=1)
    date_trigger = DateTrigger(run_date=t1)
    scheduler.add_job(download, trigger=date_trigger)

    # 读取定时配置
    schedule_config = APP_CONFIG.get('download.schedule', '').strip()

    if schedule_config:
        # 定时模式：解析时间点，如 "8:00,12:00,15:00,22:00"
        times = [t.strip() for t in schedule_config.split(',') if t.strip()]
        hours = []
        minutes = []
        for t in times:
            try:
                parts = t.split(':')
                h = int(parts[0])
                m = int(parts[1]) if len(parts) > 1 else 0
                hours.append(h)
                minutes.append(m)
            except (ValueError, IndexError):
                logger.warning(f'Invalid schedule time format: {t}, skipping')

        if hours:
            # 为每个时间点创建 CronTrigger
            for h, m in zip(hours, minutes):
                trigger = CronTrigger(hour=h, minute=m)
                scheduler.add_job(download, trigger=trigger, id=f'cron_{h}:{m:02d}')
                logger.info(f'Scheduled at {h}:{m:02d} every day')

            scheduler.start()
            logger.info(f'Scheduler started in CRON mode, times: {[f"{h}:{m:02d}" for h, m in zip(hours, minutes)]}')
        else:
            # 解析失败，回退到 interval 模式
            _start_interval_mode(scheduler)
    else:
        # interval 模式
        _start_interval_mode(scheduler)


def _start_interval_mode(scheduler):
    '''
    使用固定间隔模式启动调度
    '''
    interval = int(APP_CONFIG.get('download.interval', 1800))
    int_trigger = IntervalTrigger(seconds=interval)
    scheduler.add_job(download, trigger=int_trigger)

    if not scheduler.running:
        scheduler.start()
    logger.info(f'Scheduler started in INTERVAL mode, interval={interval}s ({interval // 3600}h {(interval % 3600) // 60}m)')


def add_download_job(fanhaos, movie_type='mixed'):
    if not fanhaos:
        return None
    return download(fanhaos, movie_type)
