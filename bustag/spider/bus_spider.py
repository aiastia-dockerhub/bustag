'''
数据抓取调度模块
使用 javbus-api 替代原有的 aspider 网站爬虫
'''
import time
from datetime import datetime
import requests
from .api_client import get_movies, get_movie_detail, search_movies
from .parser import parse_movie_detail, parse_preview_item
from .db import save, Item, SkipItem
from bustag.util import APP_CONFIG, logger

MAXPAGE = 30
MAX_CONSECUTIVE_FAILURES = 3  # 连续失败超过此数则提前终止


def get_url_by_fanhao(fanhao):
    '''
    保留兼容接口：通过番号获取影片详情并保存
    现在使用 API 而非 URL

    Args:
        fanhao: 番号

    Returns:
        str: 番号（保持接口兼容）
    '''
    return fanhao


def fetch_and_save_movie(movie_id, movie_type='normal'):
    '''
    获取单个影片详情并保存到数据库

    Args:
        movie_id: 番号
        movie_type: 影片类型（normal=有码, uncensored=无码）

    Returns:
        bool: 是否成功保存
    '''
    # 检查是否在跳过列表中（之前 404 的番号）
    if SkipItem.is_skipped(movie_id):
        logger.debug(f'Movie {movie_id} is in skip list, skipping')
        return False

    # 检查是否已存在
    exists = Item.get_by_fanhao(movie_id)
    if exists:
        logger.debug(f'Movie already exists: {movie_id}, skipping')
        return False

    try:
        detail = get_movie_detail(movie_id)
        if not detail:
            logger.warning(f'No detail returned for: {movie_id}')
            return False

        meta, tags = parse_movie_detail(detail)
        # URL 指向 javbus 网站（可通过环境变量配置）
        javbus_url = APP_CONFIG.get('download.javbus_url', 'https://www.javbus.com')
        meta['url'] = f'{javbus_url}/{movie_id}'

        save(meta, tags, movie_type=movie_type)
        logger.info(f'Saved movie: {movie_id}')
        print(f'item {movie_id} is processed')
        return True
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            # 404 说明该影片在 API 中不存在（已下架或番号无效）
            # 加入跳过列表，防止反复重试
            logger.warning(f'Movie {movie_id} not found (404), adding to skip list')
            SkipItem.add_skip(movie_id, reason='not_found')
        else:
            logger.error(f'Failed to fetch/save movie {movie_id}: {e}')
        return False
    except Exception as e:
        logger.error(f'Failed to fetch/save movie {movie_id}: {e}')
        return False


def download_movies(pages=None):
    '''
    批量下载影片数据
    遍历 API 影片列表分页，获取详情并保存

    Args:
        pages: 要下载的页数，None 则使用配置中的 count
    '''
    if pages is None:
        pages = int(APP_CONFIG.get('download.count', 10))

    total_saved = 0
    total_processed = 0

    magnet = APP_CONFIG.get('download.magnet', 'exist')
    # 支持多种类型：normal,uncensored（逗号分隔）
    movie_type_config = APP_CONFIG.get('download.movie_type', 'normal')
    movie_types = [t.strip() for t in movie_type_config.split(',') if t.strip()]

    for i, mt in enumerate(movie_types):
        # 类型间添加延迟，避免对外部 API 造成过载
        if i > 0:
            type_delay = 10
            logger.info(f'Waiting {type_delay}s before starting next type ({mt})...')
            time.sleep(type_delay)

        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f'[{now_str}] Starting download for movie_type: {mt}')
        saved, processed = _download_by_type(pages=pages, magnet=magnet, movie_type=mt)
        total_saved += saved
        total_processed += processed

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f'[{now_str}] Download complete: processed {total_processed}, saved {total_saved}')
    print(f'Download complete: processed {total_processed}, saved {total_saved}')
    return total_saved


def _resolve_movie_type(movie_type=None):
    '''影片类型：显式指定优先，否则用配置 download.movie_type（默认 normal）'''
    return movie_type or APP_CONFIG.get('download.movie_type', 'normal')


def _clean_sources(sources):
    '''清洗批量来源列表：去空白、丢空值'''
    cleaned = []
    for source in sources or []:
        value = (source.get('value') or '').strip()
        if value:
            cleaned.append({'type': source.get('type', 'keyword'), 'value': value})
    return cleaned


def _process_movie_pages(fetch_page, pages, label, handle_movie, progress=None):
    '''
    逐页抓取影片列表并逐部处理（公共骨架）

    Args:
        fetch_page: callable(page) -> dict，返回含 movies 列表的结果
        pages: 要抓取的页数
        label: 日志与进度显示用的来源描述
        handle_movie: callable(movie) -> bool，返回 True 表示是新处理的有效影片
        progress: 可选回调 progress(stage=..., processed=...)，每处理一部影片调用一次

    Returns:
        tuple: (new_count, processed_count)
    '''
    total_new = 0
    total_processed = 0
    consecutive_failures = 0

    for page in range(1, pages + 1):
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f'[{now_str}] Fetching movie list page {page}/{pages} ({label})')
        print(f'[{now_str}] process page {page} ({label})')

        try:
            result = fetch_page(page)
            consecutive_failures = 0  # 请求成功，重置计数
        except Exception as e:
            consecutive_failures += 1
            logger.error(f'Failed to fetch page {page}: {e}')
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                logger.error(
                    f'API consecutive failures reached {MAX_CONSECUTIVE_FAILURES}, '
                    f'stopping download ({label}). '
                    f'Please check if javbus-api service is running.'
                )
                print(f'Too many failures, stopping ({label})')
                break
            continue

        movies = result.get('movies', [])
        if not movies:
            logger.info(f'No more movies on page {page}, stopping')
            break

        for movie in movies:
            movie_id = movie.get('id', '')
            if not movie_id:
                continue

            total_processed += 1
            if handle_movie(movie):
                total_new += 1

            if progress:
                progress(stage=label, processed=total_processed)

            # 请求间隔已由 api_client 全局控制，无需额外等待

        # 分页间隔
        time.sleep(2)

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f'[{now_str}] Process {label} complete: processed {total_processed}, new {total_new}')
    return total_new, total_processed


def _save_movies_from_pages(fetch_page, pages, label, movie_type='normal', progress=None):
    '''
    逐页抓取影片列表并保存详情

    Args:
        fetch_page: callable(page) -> dict，返回含 movies 列表的结果
        pages: 要抓取的页数
        label: 来源描述（如 '演员 qs6'）
        movie_type: 影片类型（normal/uncensored）
        progress: 可选回调 progress(stage=..., processed=...)

    Returns:
        tuple: (saved_count, processed_count)
    '''

    def handle_movie(movie):
        return fetch_and_save_movie(movie.get('id', ''), movie_type=movie_type)

    return _process_movie_pages(
        fetch_page, pages, f'抓取{label}', handle_movie, progress)


def _download_by_type(pages, magnet, movie_type):
    '''
    按影片类型批量下载

    Args:
        pages: 要下载的页数
        magnet: 磁力链接筛选
        movie_type: 影片类型（normal/uncensored）

    Returns:
        tuple: (saved_count, processed_count)
    '''

    def fetch_page(page):
        return get_movies(page=page, magnet=magnet, movie_type=movie_type)

    return _save_movies_from_pages(fetch_page, pages, f'type={movie_type}', movie_type=movie_type)


def detect_movie_type(fanhao):
    '''
    自动判断番号是有码还是无码
    通过搜索无码接口，如果能搜到则认为是无码

    Args:
        fanhao: 番号

    Returns:
        str: 'uncensored' 或 'normal'
    '''
    try:
        result = search_movies(keyword=fanhao, movie_type='uncensored')
        movies = result.get('movies', [])
        for movie in movies:
            if movie.get('id', '').upper() == fanhao.upper():
                logger.info(f'Detected {fanhao} as uncensored')
                return 'uncensored'
    except Exception as e:
        logger.warning(f'Failed to detect type for {fanhao}: {e}')
    return 'normal'


def download_by_fanhaos(fanhaos, movie_type='mixed'):
    '''
    根据番号列表下载影片数据
    超过 batch_size 时自动分批处理，批次间暂停避免过快

    Args:
        fanhaos: list - 番号列表
        movie_type: str - 'normal'=有码, 'uncensored'=无码, 'mixed'=混合（自动判断）

    Returns:
        int: 成功保存的数量
    '''
    total_saved = 0
    batch_size = int(APP_CONFIG.get('download.batch_size', '100'))
    batch_interval = float(APP_CONFIG.get('download.batch_interval', '5'))

    total = len(fanhaos)
    for i, fanhao in enumerate(fanhaos):
        total_processed = i + 1

        # 确定影片类型
        if movie_type == 'mixed':
            mt = detect_movie_type(fanhao)
        else:
            mt = movie_type

        if fetch_and_save_movie(fanhao, movie_type=mt):
            total_saved += 1

        # 分批处理：每 batch_size 个暂停
        if total_processed % batch_size == 0 and total_processed < total:
            batch_num = total_processed // batch_size
            logger.info(f'Batch {batch_num} done ({total_processed}/{total}), '
                       f'waiting {batch_interval}s before next batch')
            print(f'Batch {batch_num} done ({total_processed}/{total}), pausing...')
            time.sleep(batch_interval)

    logger.info(f'Download by fanhaos complete: saved {total_saved}/{len(fanhaos)}')
    return total_saved


def search_and_download(keyword, pages=1, progress=None, movie_type=None):
    '''
    搜索并下载影片数据（仅含有磁力链接的影片）

    Args:
        keyword: 搜索关键字
        pages: 下载页数
        progress: 可选回调 progress(stage=..., processed=...)
        movie_type: 'normal'/'uncensored'，不传则用配置 download.movie_type

    Returns:
        int: 成功保存的数量
    '''
    movie_type = _resolve_movie_type(movie_type)
    magnet = APP_CONFIG.get('download.magnet', 'exist')

    def fetch_page(page):
        return search_movies(keyword=keyword, page=page, magnet=magnet, movie_type=movie_type)

    saved, _ = _save_movies_from_pages(
        fetch_page, pages, f'关键词 {keyword}', movie_type=movie_type, progress=progress)
    return saved


def download_by_star(star_id, pages=1, progress=None, movie_type=None):
    '''
    按演员 ID 下载影片数据（仅含有磁力链接的影片）

    Args:
        star_id: 演员 ID（JavBus 演员页 /star/<id> 中的 ID，如 qs6）
        pages: 下载页数
        progress: 可选回调 progress(stage=..., processed=...)
        movie_type: 'normal'/'uncensored'，不传则用配置 download.movie_type

    Returns:
        int: 成功保存的数量
    '''
    movie_type = _resolve_movie_type(movie_type)
    magnet = APP_CONFIG.get('download.magnet', 'exist')

    def fetch_page(page):
        return get_movies(page=page, magnet=magnet, movie_type=movie_type,
                          filter_type='star', filter_value=star_id)

    saved, _ = _save_movies_from_pages(
        fetch_page, pages, f'演员 {star_id}', movie_type=movie_type, progress=progress)
    return saved


def batch_download(sources, pages=1, progress=None, movie_type=None):
    '''
    按演员 ID / 搜索关键词混合批量下载影片（仅含有磁力链接的影片）

    Args:
        sources: list of dict，每项为 {'type': 'star'|'keyword', 'value': str}
        pages: 每个来源下载的页数
        progress: 可选回调 progress(stage=..., processed=...)
        movie_type: 'normal'/'uncensored'，不传则用配置 download.movie_type

    Returns:
        int: 成功保存的数量
    '''
    cleaned = _clean_sources(sources)
    movie_type = _resolve_movie_type(movie_type)

    total_saved = 0
    for i, source in enumerate(cleaned):
        if progress:
            # 外层标注整体进度（第几个来源），内层继续更新 processed
            source_progress = lambda stage, processed, i=i: progress(
                stage=f'{stage}（{i + 1}/{len(cleaned)}）', processed=processed)
        else:
            source_progress = None

        if source['type'] == 'star':
            total_saved += download_by_star(
                source['value'], pages=pages, progress=source_progress, movie_type=movie_type)
        else:
            total_saved += search_and_download(
                source['value'], pages=pages, progress=source_progress, movie_type=movie_type)

    return total_saved


def preview_sources(sources, pages=1, movie_type=None, progress=None):
    '''
    抓取演员 ID / 搜索关键词的候选影片列表（不入库），供批量添加前预览勾选。
    只返回有磁力链接的影片；已入库或已在跳过列表中的影片会被过滤。

    Args:
        sources: list of dict，每项为 {'type': 'star'|'keyword', 'value': str}
        pages: 每个来源抓取的页数
        movie_type: 'normal'/'uncensored'，不传则用配置 download.movie_type
        progress: 可选回调 progress(stage=..., processed=...)

    Returns:
        dict: {'movies': [{'fanhao', 'title', 'img', 'date', 'source'}], 'skipped': 过滤数量}
    '''
    movie_type = _resolve_movie_type(movie_type)
    magnet = APP_CONFIG.get('download.magnet', 'exist')
    cleaned = _clean_sources(sources)

    candidates = []
    seen = set()
    skipped = 0

    for i, source in enumerate(cleaned):
        value = source['value']
        if progress:
            source_progress = lambda stage, processed, i=i: progress(
                stage=f'{stage}（{i + 1}/{len(cleaned)}）', processed=processed)
        else:
            source_progress = None

        if source['type'] == 'star':
            label = f'演员 {value}'

            def fetch_page(page, value=value):
                return get_movies(page=page, magnet=magnet, movie_type=movie_type,
                                  filter_type='star', filter_value=value)
        else:
            label = f'关键词 {value}'

            def fetch_page(page, value=value):
                return search_movies(keyword=value, page=page, magnet=magnet, movie_type=movie_type)

        def handle_movie(movie):
            nonlocal skipped
            movie_id = movie.get('id', '')
            if movie_id in seen:
                return False
            seen.add(movie_id)
            if Item.get_by_fanhao(movie_id) or SkipItem.is_skipped(movie_id):
                skipped += 1
                return False
            item = parse_preview_item(movie)
            javbus_url = APP_CONFIG.get('download.javbus_url', 'https://www.javbus.com')
            item['url'] = f"{javbus_url}/{item['fanhao']}"
            item['source'] = label
            candidates.append(item)
            return True

        _process_movie_pages(fetch_page, pages, f'预览{label}', handle_movie, source_progress)

    return {'movies': candidates, 'skipped': skipped}