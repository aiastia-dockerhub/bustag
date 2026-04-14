'''
javbus-api 客户端封装
使用 https://github.com/ovnrain/javbus-api 提供的 REST API
替代原有的网站爬虫方式
'''
import requests
from bustag.util import logger, APP_CONFIG


def get_api_base_url():
    '''获取 API 基础 URL'''
    return APP_CONFIG.get('download.api_base_url', 'http://localhost:3000')


def get_auth_token():
    '''获取认证 Token（可选）'''
    return APP_CONFIG.get('download.auth_token', '')


def _get_headers():
    '''构建请求头'''
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'bustag/0.3.0'
    }
    token = get_auth_token()
    if token:
        headers['j-auth-token'] = token
    return headers


def _request(endpoint, params=None):
    '''
    发送 API 请求

    Args:
        endpoint: API 端点路径（如 /api/movies）
        params: 查询参数字典

    Returns:
        dict/list: JSON 响应数据

    Raises:
        requests.RequestException: 请求失败时抛出
    '''
    base_url = get_api_base_url().rstrip('/')
    url = f'{base_url}{endpoint}'
    headers = _get_headers()

    logger.debug(f'API request: {url} params={params}')

    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f'API request failed: {url}, error: {e}')
        raise


def get_movies(page=1, magnet='exist', filter_type=None, filter_value=None, movie_type='normal'):
    '''
    获取影片列表

    Args:
        page: 页码，默认 1
        magnet: 'exist' 只返回有磁力链接的，'all' 返回全部
        filter_type: 筛选类型 (star/genre/director/studio/label/series)
        filter_value: 筛选值
        movie_type: 'normal' 有码, 'uncensored' 无码

    Returns:
        dict: 包含 movies 和 pagination 的字典
    '''
    params = {
        'page': page,
        'magnet': magnet,
        'type': movie_type
    }
    if filter_type and filter_value:
        params['filterType'] = filter_type
        params['filterValue'] = filter_value

    return _request('/api/movies', params)


def search_movies(keyword, page=1, magnet='exist', movie_type='normal'):
    '''
    搜索影片

    Args:
        keyword: 搜索关键字
        page: 页码
        magnet: 'exist' 或 'all'
        movie_type: 'normal' 或 'uncensored'

    Returns:
        dict: 搜索结果
    '''
    params = {
        'keyword': keyword,
        'page': page,
        'magnet': magnet,
        'type': movie_type
    }
    return _request('/api/movies/search', params)


def get_movie_detail(movie_id):
    '''
    获取影片详情

    Args:
        movie_id: 番号（如 SSIS-406）

    Returns:
        dict: 影片详情，包含标题、封面、标签、演员等
    '''
    return _request(f'/api/movies/{movie_id}')


def get_magnets(movie_id, gid, uc, sort_by=None, sort_order=None):
    '''
    获取影片磁力链接

    Args:
        movie_id: 番号
        gid: 从影片详情获取的 gid
        uc: 从影片详情获取的 uc
        sort_by: 排序方式 ('date' 或 'size')
        sort_order: 排序方向 ('asc' 或 'desc')

    Returns:
        list: 磁力链接列表
    '''
    params = {
        'gid': gid,
        'uc': uc
    }
    if sort_by and sort_order:
        params['sortBy'] = sort_by
        params['sortOrder'] = sort_order

    return _request(f'/api/magnets/{movie_id}', params)


def get_star_detail(star_id, movie_type='normal'):
    '''
    获取演员详情

    Args:
        star_id: 演员 ID
        movie_type: 'normal' 或 'uncensored'

    Returns:
        dict: 演员详情
    '''
    params = {'type': movie_type}
    return _request(f'/api/stars/{star_id}', params)