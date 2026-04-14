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


def fetch_and_save_movie(movie_id):
    '''
    获取单个影片详情并保存到数据库

    Args:
        movie_id: 番号

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

        save(meta, tags)
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

    for page in range(1, pages + 1):
        logger.info(f'Fetching movie list page {page}/{pages}')
        print(f'process page {page}')

        try:
            result = get_movies(page=page, magnet='all')
        except Exception as e:
            logger.error(f'Failed to fetch page {page}: {e}')
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
            if fetch_and_save_movie(movie_id):
                total_saved += 1

            # 请求间隔，避免过快
            time.sleep(0.5)

        # 分页间隔
        time.sleep(1)

    logger.info(f'Download complete: processed {total_processed}, saved {total_saved}')
    print(f'Download complete: processed {total_processed}, saved {total_saved}')
    return total_saved


def download_by_fanhaos(fanhaos):
    '''
    根据番号列表下载影片数据

    Args:
        fanhaos: list - 番号列表

    Returns:
        int: 成功保存的数量
    '''
    total_saved = 0

    for fanhao in fanhaos:
        if fetch_and_save_movie(fanhao):
            total_saved += 1
        time.sleep(0.5)

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

    for page in range(1, pages + 1):
        try:
            result = search_movies(keyword=keyword, page=page, magnet='all')
        except Exception as e:
            logger.error(f'Search failed for "{keyword}" page {page}: {e}')
            continue

        movies = result.get('movies', [])
        for movie in movies:
            movie_id = movie.get('id', '')
            if movie_id and fetch_and_save_movie(movie_id):
                total_saved += 1
            time.sleep(0.5)

    return total_saved