"""
Bustag REST API - JSON 接口，供 Vue 前端调用
"""
import os
import sys
import hashlib
import threading
import traceback
import bottle
import requests as req_lib
from bottle import route, run, template, static_file, request, response, redirect, hook
from bustag.util import APP_CONFIG

# 增大 POST 请求体限制
bottle.BaseRequest.MEMFILE_MAX = 10 * 1024 * 1024  # 10MB


def _remove_extra_tags(item):
    limit = 10
    tags_dict = item.tags_dict
    tags = ['genre', 'star']
    for t in tags:
        tags_dict[t] = tags_dict[t][:limit]


def _item_to_dict(item):
    """将 Item 对象转为可序列化的字典"""
    return {
        'id': item.id,
        'fanhao': item.fanhao,
        'title': item.title,
        'cover_img_url': item.cover_img_url,
        'url': item.url,
        'release_date': str(item.release_date) if item.release_date else '',
        'add_date': str(item.add_date) if item.add_date else '',
        'tags_dict': item.tags_dict if hasattr(item, 'tags_dict') else {'genre': [], 'star': []},
    }


def _item_rate_to_dict(item):
    """将带评分的 Item 对象转为字典"""
    d = _item_to_dict(item)
    if hasattr(item, 'rate_value') and item.rate_value is not None:
        d['rate_value'] = item.rate_value
    if hasattr(item, 'rate_type') and item.rate_type is not None:
        d['rate_type'] = item.rate_type
    return d


def _local_item_to_dict(local_item):
    """将 LocalItem 对象转为字典"""
    return {
        'id': local_item.id,
        'path': local_item.path,
        'last_view_date': str(local_item.last_view_date) if local_item.last_view_date else '',
        'view_times': local_item.view_times if hasattr(local_item, 'view_times') else 0,
        'item': _item_to_dict(local_item.item),
    }


def _page_info_to_dict(page_info):
    """将分页信息转为字典"""
    return {
        'total_items': page_info[0],
        'max_page': page_info[1],
        'current_page': page_info[2],
    }


def _json_response(data):
    """统一 JSON 响应格式"""
    response.content_type = 'application/json; charset=utf-8'
    return data


# ============ API 路由 ============

@route('/api/')
@route('/api/index')
def api_index():
    """推荐列表"""
    from bustag.spider.db import get_items, RATE_TYPE, RATE_VALUE
    from bustag.spider import db as db_module

    rate_type = RATE_TYPE.SYSTEM_RATE.value
    rate_value = int(request.query.get('like', RATE_VALUE.LIKE.value))
    page = int(request.query.get('page', 1))

    movie_type_config = APP_CONFIG.get('download.movie_type', 'normal')
    movie_types = [t.strip() for t in movie_type_config.split(',') if t.strip()]
    movie_type = request.query.get('type', movie_types[0] if movie_types else 'normal')
    if movie_type not in movie_types:
        movie_type = movie_types[0] if movie_types else 'normal'

    items, page_info = get_items(
        rate_type=rate_type, rate_value=rate_value, page=page, movie_type=movie_type)
    for item in items:
        _remove_extra_tags(item)

    today_update_count = db_module.get_today_update_count()
    today_recommend_count = db_module.get_today_recommend_count()

    return _json_response({
        'items': [_item_rate_to_dict(item) for item in items],
        'page_info': _page_info_to_dict(page_info),
        'like': rate_value,
        'movie_types': movie_types,
        'movie_type': movie_type,
        'today_update': today_update_count,
        'today_recommend': today_recommend_count,
    })


@route('/api/correct/<fanhao>', method='POST')
def api_correct(fanhao):
    """推荐反馈"""
    from bustag.spider.db import ItemRate, RATE_TYPE

    data = request.json or {}
    is_correct = data.get('is_correct', True)

    item_rate = ItemRate.get_by_fanhao(fanhao)
    if item_rate:
        item_rate.rate_type = RATE_TYPE.USER_RATE
        if not is_correct:
            rate_value = item_rate.rate_value
            rate_value = 1 if rate_value == 0 else 0
            item_rate.rate_value = rate_value
        item_rate.save()

    return _json_response({'success': True})


@route('/api/tagit')
def api_tagit():
    """打标列表"""
    from bustag.spider.db import get_items, RATE_TYPE, RATE_VALUE

    rate_value = request.query.get('like', None)
    rate_value = None if rate_value == 'None' or rate_value == '' else rate_value
    rate_type = None
    if rate_value is not None:
        rate_value = int(rate_value)
        rate_type = RATE_TYPE.USER_RATE
    page = int(request.query.get('page', 1))

    # 影片类型筛选（参考推荐页）
    movie_type_config = APP_CONFIG.get('download.movie_type', 'normal')
    movie_types = [t.strip() for t in movie_type_config.split(',') if t.strip()]
    movie_type = request.query.get('type', movie_types[0] if movie_types else 'normal')
    if movie_type not in movie_types:
        movie_type = movie_types[0] if movie_types else 'normal'

    items, page_info = get_items(
        rate_type=rate_type, rate_value=rate_value, page=page, movie_type=movie_type)
    for item in items:
        _remove_extra_tags(item)

    return _json_response({
        'items': [_item_rate_to_dict(item) for item in items],
        'page_info': _page_info_to_dict(page_info),
        'like': rate_value,
        'movie_types': movie_types,
        'movie_type': movie_type,
    })


@route('/api/tag/<fanhao>', method='POST')
def api_tag(fanhao):
    """打标操作"""
    from bustag.spider.db import ItemRate, RATE_TYPE

    data = request.json or {}
    rate_value = data.get('rate_value', 1)

    item_rate = ItemRate.get_by_fanhao(fanhao)
    if not item_rate:
        rate_type = RATE_TYPE.USER_RATE
        ItemRate.saveit(rate_type, rate_value, fanhao)
    else:
        item_rate.rate_value = rate_value
        item_rate.save()

    return _json_response({'success': True})


@route('/api/local')
def api_local():
    """本地文件列表"""
    from bustag.spider.db import get_local_items, LocalItem

    page = int(request.query.get('page', 1))
    items, page_info = get_local_items(page=page)
    for local_item in items:
        LocalItem.loadit(local_item)
        _remove_extra_tags(local_item.item)

    return _json_response({
        'items': [_local_item_to_dict(item) for item in items],
        'page_info': _page_info_to_dict(page_info),
    })


@route('/api/local_fanhao', method=['GET', 'POST'])
def api_local_fanhao():
    """上传番号"""
    from bustag.app.local import add_local_fanhao
    from bustag.spider import bus_spider
    from bustag.app.schedule import add_download_job

    msg = ''
    if request.method == 'POST':
        data = request.json or {}
        fanhao_list = data.get('fanhao', '')
        tag_like = data.get('tag_like', False)
        movie_type = data.get('movie_type', 'mixed')

        missed_fanhao, local_file_count, tag_file_count = add_local_fanhao(
            fanhao_list, tag_like)
        if len(missed_fanhao) > 0:
            urls = [bus_spider.get_url_by_fanhao(fanhao) for fanhao in missed_fanhao]
            add_download_job(urls)
        msg = f'上传 {len(missed_fanhao)} 个番号, {local_file_count} 个本地文件'
        if tag_like:
            msg += f', {tag_file_count} 个打标为喜欢'

    return _json_response({'msg': msg})


@route('/api/model')
def api_model():
    """模型信息"""
    import bustag.model.classifier as clf

    try:
        _, model_scores = clf.load()
    except FileNotFoundError:
        model_scores = None

    result = {'model_scores': None}
    if model_scores:
        result['model_scores'] = {
            'accuracy': model_scores.get('accuracy', None),
            'precision': model_scores.get('precision', None),
            'recall': model_scores.get('recall', None),
            'f1': model_scores.get('f1', None),
        }

    return _json_response(result)


@route('/api/do-training')
def api_do_training():
    """训练模型"""
    import bustag.model.classifier as clf

    error_msg = None
    model_scores = None
    try:
        _, model_scores = clf.train()
    except ValueError as ex:
        error_msg = ' '.join(ex.args)

    result = {'error_msg': error_msg, 'model_scores': None}
    if model_scores:
        result['model_scores'] = {
            'accuracy': model_scores.get('accuracy', None),
            'precision': model_scores.get('precision', None),
            'recall': model_scores.get('recall', None),
            'f1': model_scores.get('f1', None),
        }

    return _json_response(result)


@route('/api/load_db', method='POST')
def api_load_db():
    """上传数据库"""
    from bustag.app.local import load_tags_db
    from bustag.spider import bus_spider
    from bustag.app.schedule import add_download_job
    from bustag.spider.db import DBError
    from bustag.util import get_data_path

    msg = ''
    errmsg = ''
    upload = request.files.get('dbfile')
    if upload:
        name = get_data_path('uploaded.db')
        upload.save(name, overwrite=True)
        try:
            tag_file_added, missed_fanhaos = load_tags_db()
        except DBError:
            errmsg = '数据库文件错误, 请检查文件是否正确上传'
        else:
            urls = [bus_spider.get_url_by_fanhao(fanhao) for fanhao in missed_fanhaos]
            add_download_job(urls)
            msg = f'上传 {tag_file_added} 条用户打标数据, {len(missed_fanhaos)} 个番号'
    else:
        errmsg = '请上传数据库文件'

    return _json_response({'msg': msg, 'errmsg': errmsg})


@route('/api/search')
def api_search():
    """搜索"""
    from bustag.spider.db import Item
    from bustag.spider import db as db_module

    query = request.query.get('q', '').strip()
    tag_value = request.query.get('tag', '').strip()
    page = int(request.query.get('page', 1))
    genre_tags = db_module.get_genre_tags()

    item = None
    tag_items = []
    page_info = None

    if query:
        item = Item.get_by_fanhao(query)
        if item:
            Item.loadit(item)
            Item.get_tags_dict(item)
    elif tag_value:
        tag_items, page_info = db_module.get_items_by_tag(tag_value, page=page)
        for it in tag_items:
            _remove_extra_tags(it)

    result = {
        'query': query,
        'tag_value': tag_value,
        'genre_tags': genre_tags,
        'item': _item_to_dict(item) if item else None,
        'tag_items': [_item_to_dict(it) for it in tag_items],
        'page_info': _page_info_to_dict(page_info) if page_info else None,
    }

    return _json_response(result)


# 图片代理（复用原有的逻辑）
_img_semaphore = threading.Semaphore(10)


def _get_img_cache_dir():
    cache_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'data', 'img_cache')
    cache_dir = os.path.abspath(cache_dir)
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _get_cached_img_path(img_url):
    url_hash = hashlib.md5(img_url.encode()).hexdigest()
    ext = '.jpg'
    for e in ['.png', '.gif', '.webp', '.jpeg']:
        if img_url.lower().endswith(e):
            ext = e
            break
    return os.path.join(_get_img_cache_dir(), f'{url_hash}{ext}')


@route('/api/img_proxy')
@route('/img_proxy')
def api_img_proxy():
    """图片代理"""
    img_url = request.query.get('url', '')
    if not img_url:
        response.status = 400
        return 'Missing url parameter'

    cache_enabled = APP_CONFIG.get('download.img_cache_enabled', 'true').lower() != 'false'
    cache_path = _get_cached_img_path(img_url)

    if cache_enabled and os.path.exists(cache_path):
        ext = os.path.splitext(cache_path)[1]
        content_types = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
                         '.gif': 'image/gif', '.webp': 'image/webp'}
        response.content_type = content_types.get(ext, 'image/jpeg')
        response.headers['Cache-Control'] = 'public, max-age=86400'
        with open(cache_path, 'rb') as f:
            return f.read()

    with _img_semaphore:
        try:
            headers = {
                'Referer': 'https://www.javbus.com/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            r = req_lib.get(img_url, headers=headers, timeout=15)
            r.raise_for_status()
            img_data = r.content
        except Exception as e:
            response.status = 502
            return f'Failed to fetch image: {e}'

    if cache_enabled:
        try:
            tmp_path = cache_path + '.tmp'
            with open(tmp_path, 'wb') as f:
                f.write(img_data)
            os.rename(tmp_path, cache_path)
        except Exception:
            pass

    content_type = r.headers.get('Content-Type', 'image/jpeg')
    response.content_type = content_type
    response.headers['Cache-Control'] = 'public, max-age=86400'
    return img_data


@route('/api/local_play/<id:int>')
def api_local_play(id):
    """播放本地文件"""
    from bustag.spider.db import LocalItem
    local_item = LocalItem.update_play(id)
    file_path = local_item.path
    redirect(file_path)


@route('/api/version')
def api_version():
    """版本信息"""
    from bustag import __version__
    return _json_response({'version': __version__})