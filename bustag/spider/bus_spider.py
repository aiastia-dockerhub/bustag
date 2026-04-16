'''
数据抓取调度模块
使用 javbus-api 替代原有的 aspider 网站爬虫
'''
import time
from .api_client import get_movies, get_movie_detail, search_movies
from .parser import parse_movie_detail
from .db import save, Item
from bustag.util import APP_CONFIG, logger

MAXPAGE = 30


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

    for mt in movie_types:
        logger.info(f'Starting download for movie_type: {mt}')
        saved, processed = _download_by_type(pages=pages, magnet=magnet, movie_type=mt)
        total_saved += saved
        total_processed += processed

    logger.info(f'Download complete: processed {total_processed}, saved {total_saved}')
    print(f'Download complete: processed {total_processed}, saved {total_saved}')
    return total_saved


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
    total_saved = 0
    total_processed = 0

    for page in range(1, pages + 1):
        logger.info(f'Fetching movie list page {page}/{pages} (type={movie_type})')
        print(f'process page {page} (type={movie_type})')

        try:
            result = get_movies(page=page, magnet=magnet, movie_type=movie_type)
        except Exception as e:
            logger.error(f'Failed to fetch page {page}: {e}')
            continue

        movies = result.get('movies', [])
        if not movies:
            logger.info(f'No more movies on page {page}, stopping')
            break

        page_saved = 0
        for movie in movies:
            movie_id = movie.get('id', '')
            if not movie_id:
                continue

            total_processed += 1
            if fetch_and_save_movie(movie_id, movie_type=movie_type):
                total_saved += 1
                page_saved += 1

            # 请求间隔已由 api_client 全局控制，无需额外等待

        # 如果整页都是重复的，说明后面的页更旧，提前停止
        if page_saved == 0:
            logger.info(f'Page {page} has no new movies, stopping early')
            print(f'Page {page} all duplicates, stopping early')
            break

        # 分页间隔
        time.sleep(2)

    logger.info(f'Download type={movie_type} complete: processed {total_processed}, saved {total_saved}')
    return total_saved, total_processed


def download_by_fanhaos(fanhaos):
    '''
    根据番号列表下载影片数据
    超过 batch_size 时自动分批处理，批次间暂停避免过快

    Args:
        fanhaos: list - 番号列表

    Returns:
        int: 成功保存的数量
    '''
    total_saved = 0
    batch_size = int(APP_CONFIG.get('download.batch_size', '100'))
    batch_interval = float(APP_CONFIG.get('download.batch_interval', '5'))

    total = len(fanhaos)
    for i, fanhao in enumerate(fanhaos):
        total_processed = i + 1
        if fetch_and_save_movie(fanhao):
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


def search_and_download(keyword, pages=1):
    '''
    搜索并下载影片数据

    Args:
        keyword: 搜索关键字
        pages: 下载页数

    Returns:
        int: 成功保存的数量
    '''
    total_saved = 0
    magnet = APP_CONFIG.get('download.magnet', 'exist')
    movie_type = APP_CONFIG.get('download.movie_type', 'normal')

    for page in range(1, pages + 1):
        try:
            result = search_movies(keyword=keyword, page=page, magnet=magnet, movie_type=movie_type)
        except Exception as e:
            logger.error(f'Search failed for "{keyword}" page {page}: {e}')
            continue

        movies = result.get('movies', [])
        for movie in movies:
            movie_id = movie.get('id', '')
            if movie_id and fetch_and_save_movie(movie_id):
                total_saved += 1

    return total_saved