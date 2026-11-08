"""
Bustag REST API - JSON 接口，供 Vue 前端调用
"""
import os
import sys
import re
import threading
import time
from collections import OrderedDict
import bottle
from bottle import route, run, static_file, request, response, redirect, hook
from bustag.util import APP_CONFIG

# ============ 简易内存缓存 ============
_api_cache = OrderedDict()
_api_cache_lock = threading.Lock()

def _cache_get(key, max_age=30):
    """获取缓存，max_age 秒内有效"""
    with _api_cache_lock:
        entry = _api_cache.get(key)
        if entry and time.monotonic() - entry['time'] < max_age:
            _api_cache.move_to_end(key)
            return entry['data']
        _api_cache.pop(key, None)
    return None

def _cache_set(key, data):
    """设置缓存"""
    with _api_cache_lock:
        _api_cache[key] = {'data': data, 'time': time.monotonic()}
        _api_cache.move_to_end(key)
        while len(_api_cache) > 256:
            _api_cache.popitem(last=False)

def _invalidate_data():
    from bustag.spider.db import touch_data
    touch_data()
    with _api_cache_lock:
        _api_cache.clear()


@hook('after_request')
def _close_db_connection():
    module = sys.modules.get('bustag.spider.db')
    if module is not None and not module.db.is_closed():
        module.db.close()


# 增大 POST 请求体限制
bottle.BaseRequest.MEMFILE_MAX = 10 * 1024 * 1024  # 10MB


def _remove_extra_tags(item):
    limit = 10
    tags_dict = item.tags_dict
    tags = ['genre', 'star']
    for t in tags:
        tags_dict[t] = tags_dict.get(t, [])[:limit]


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


# 番号规范化正则：与 bustag/app/local.py 的上传流程保持一致
_FANHAO_PATTERN = re.compile(r'([A-Z]+)-?([0-9]+)')


def _normalize_fanhao(raw):
    '''
    规范化番号输入：转大写并补齐连字符。
    例: 'ssis-001' -> 'SSIS-001', 'SSIS001' -> 'SSIS-001'
    无法识别出「字母+数字」结构时返回 None（交由模糊匹配兜底）。
    '''
    fanhao = raw.strip().upper()
    match = _FANHAO_PATTERN.search(fanhao)
    if match and len(match.groups()) == 2:
        series, num = match.groups()
        return f'{series}-{num}'
    return None


def _json_response(data):
    """统一 JSON 响应格式"""
    import json
    json_str = json.dumps(data, ensure_ascii=False)
    response.content_type = 'application/json; charset=utf-8'
    return json_str.encode('utf-8')


# ============ API 路由 ============

@route('/api/')
@route('/api/index')
def api_index():
    """推荐列表"""
    rate_value = int(request.query.get('like', 1))
    page = int(request.query.get('page', 1))
    movie_type = request.query.get('type', 'normal')

    # 绕过缓存（打标后刷新）
    bust = request.query.get('_t', None)
    from bustag.spider.db import data_revision
    cache_key = f'index:{data_revision()}:{rate_value}:{page}:{movie_type}'

    if not bust:
        cached = _cache_get(cache_key, max_age=30)
        if cached:
            return _json_response(cached)

    from bustag.spider.db import get_items, RATE_TYPE
    from bustag.spider import db as db_module

    rate_type = RATE_TYPE.SYSTEM_RATE.value
    movie_type_config = APP_CONFIG.get('download.movie_type', 'normal')
    movie_types = [t.strip() for t in movie_type_config.split(',') if t.strip()]
    if movie_type not in movie_types:
        movie_type = movie_types[0] if movie_types else 'normal'

    items, page_info = get_items(
        rate_type=rate_type, rate_value=rate_value, page=page, movie_type=movie_type)
    for item in items:
        _remove_extra_tags(item)

    today_update_count = db_module.get_today_update_count() if page == 1 else 0
    today_recommend_count = db_module.get_today_recommend_count() if page == 1 else 0

    result = {
        'items': [_item_rate_to_dict(item) for item in items],
        'page_info': _page_info_to_dict(page_info),
        'like': rate_value,
        'movie_types': movie_types,
        'movie_type': movie_type,
        'today_update': today_update_count,
        'today_recommend': today_recommend_count,
    }
    _cache_set(cache_key, result)
    return _json_response(result)


@route('/api/correct/<fanhao>', method='POST')
def api_correct(fanhao):
    """推荐反馈"""
    from bustag.spider.db import ItemRate

    data = request.json or {}
    is_correct = data.get('is_correct', True)

    item_rate = ItemRate.get_by_fanhao(fanhao)
    if item_rate:
        value = item_rate.rate_value if is_correct else 1 - item_rate.rate_value
        ItemRate.set_user_rating(fanhao, value)

    # 清除相关缓存
    _invalidate_data()
    return _json_response({'success': True})


@route('/api/tagit')
def api_tagit():
    """打标列表"""
    rate_value = request.query.get('like', None)
    rate_value = None if rate_value == 'None' or rate_value == '' else rate_value
    page = int(request.query.get('page', 1))
    movie_type = request.query.get('type', 'normal')

    from bustag.spider.db import data_revision
    cache_key = f'tagit:{data_revision()}:{rate_value}:{page}:{movie_type}'
    cached = _cache_get(cache_key, max_age=30)
    if cached:
        return _json_response(cached)

    from bustag.spider.db import get_items, RATE_TYPE

    rate_type = None
    if rate_value is not None:
        rate_value = int(rate_value)
        rate_type = RATE_TYPE.USER_RATE

    movie_type_config = APP_CONFIG.get('download.movie_type', 'normal')
    movie_types = [t.strip() for t in movie_type_config.split(',') if t.strip()]
    if movie_type not in movie_types:
        movie_type = movie_types[0] if movie_types else 'normal'

    items, page_info = get_items(
        rate_type=rate_type, rate_value=rate_value, page=page, movie_type=movie_type)
    for item in items:
        _remove_extra_tags(item)

    result = {
        'items': [_item_rate_to_dict(item) for item in items],
        'page_info': _page_info_to_dict(page_info),
        'like': rate_value,
        'movie_types': movie_types,
        'movie_type': movie_type,
    }
    _cache_set(cache_key, result)
    return _json_response(result)


@route('/api/tag/<fanhao>', method='POST')
def api_tag(fanhao):
    """打标操作"""
    from bustag.spider.db import ItemRate

    data = request.json or {}
    rate_value = data.get('rate_value', 1)

    if rate_value not in (0, 1):
        response.status = 400
        return _json_response({'error': '评分只能为 0 或 1'})
    ItemRate.set_user_rating(fanhao, rate_value)

    # 清除相关缓存
    _invalidate_data()
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
            add_download_job(missed_fanhao, movie_type=movie_type)
        msg = f'上传 {len(missed_fanhao)} 个番号, {local_file_count} 个本地文件'
        if tag_like:
            msg += f', {tag_file_count} 个打标为喜欢'

    if request.method == 'POST':
        _invalidate_data()
    return _json_response({'msg': msg})


@route('/api/model')
def api_model():
    """模型信息"""
    try:
        import bustag.model.classifier as clf
        from bustag.util import get_data_path
        stat = os.stat(get_data_path(clf.MODEL_FILE))
        key = ('model', stat.st_mtime_ns, stat.st_size)
        model_scores = _cache_get(key, max_age=300)
        if model_scores is None:
            _, model_scores = clf.load()
            _cache_set(key, model_scores)
    except (FileNotFoundError, Exception):
        model_scores = None

    result = {'model_scores': None}
    if model_scores:
        result['model_scores'] = {
            'accuracy': model_scores.get('accuracy', None),
            'precision': model_scores.get('precision', None),
            'recall': model_scores.get('recall', None),
            'f1': model_scores.get('f1', None),
            'auc': model_scores.get('auc', None),
            'cv_f1_mean': model_scores.get('cv_f1_mean', None),
            'cv_f1_std': model_scores.get('cv_f1_std', None),
        }
        top_features = model_scores.get('top_features', None)
        if top_features:
            result['model_scores']['top_features'] = [
                {'name': name, 'importance': imp} for name, imp in top_features
            ]

    return _json_response(result)


def _submit_task(kind, payload=None):
    from bustag.app.tasks import submit, ensure_worker
    try:
        job = submit(kind, payload)
        ensure_worker()
    except ValueError as exc:
        response.status = 429
        return _json_response({'error': str(exc)})
    response.status = 202
    return _json_response({'job': job})


@route('/api/do-training', method=['GET', 'POST'])
def api_do_training():
    payload = (request.json or {}) if request.method == 'POST' else {}
    return _submit_task('train', {'full_evaluation': bool(payload.get('full_evaluation', False))})


@route('/api/jobs')
def api_jobs():
    from bustag.app.tasks import Job, initialize, serialize
    initialize()
    jobs = Job.select().order_by(Job.created_at.desc()).limit(20)
    return _json_response({'jobs': [serialize(job) for job in jobs]})


@route('/api/jobs/<job_id>')
def api_job(job_id):
    from bustag.app.tasks import Job, initialize, serialize
    initialize()
    job = Job.get_or_none(Job.id == job_id)
    if job is None:
        response.status = 404
        return _json_response({'error': '任务不存在'})
    return _json_response({'job': serialize(job)})


@route('/api/load_db', method='POST')
def api_load_db():
    """上传数据库"""
    from bustag.app.local import load_tags_db
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
            add_download_job(missed_fanhaos)
            msg = f'上传 {tag_file_added} 条用户打标数据, {len(missed_fanhaos)} 个番号'
    else:
        errmsg = '请上传数据库文件'

    _invalidate_data()
    return _json_response({'msg': msg, 'errmsg': errmsg})


def _parse_batch_input(value):
    '''
    解析批量添加输入：字符串（换行/逗号分隔）或列表，统一返回去重后的干净列表
    '''
    if value is None:
        return []
    if isinstance(value, str):
        parts = re.split(r'[\n\r,，、;；]+', value)
    elif isinstance(value, (list, tuple)):
        parts = value
    else:
        return []
    seen = set()
    result = []
    for part in parts:
        item = str(part).strip()
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


MOVIE_TYPES = ('normal', 'uncensored')


def _add_data_params(payload):
    '''
    解析批量添加/预览请求的公共参数

    Returns:
        tuple: (stars, keywords, pages, movie_type)
    '''
    stars = _parse_batch_input(payload.get('stars'))
    keywords = _parse_batch_input(payload.get('keywords'))
    try:
        pages = max(1, min(int(payload.get('pages') or 1), 30))
    except (TypeError, ValueError):
        pages = 1
    movie_type = payload.get('movie_type')
    if movie_type not in MOVIE_TYPES:
        movie_type = None
    return stars, keywords, pages, movie_type


@route('/api/add_data', method='POST')
def api_add_data():
    """批量添加数据：按演员 ID/搜索关键词抓取，或按预览勾选的番号入库（仅含有磁力链接的）"""
    payload = request.json or {}
    fanhaos = _parse_batch_input(payload.get('fanhaos'))
    stars, keywords, pages, movie_type = _add_data_params(payload)

    if fanhaos:
        # 预览勾选后的番号直接入库，类型沿用预览时选择的
        return _submit_task('download', {'fanhaos': fanhaos, 'movie_type': movie_type or 'mixed'})

    if not stars and not keywords:
        response.status = 400
        return _json_response({'error': '请至少输入一个演员 ID 或搜索关键词'})

    return _submit_task('download', {'stars': stars, 'keywords': keywords,
                                     'pages': pages, 'movie_type': movie_type})


@route('/api/add_data/preview', method='POST')
def api_add_data_preview():
    """预览批量添加候选：按演员 ID/搜索关键词抓取列表（不入库，仅含有磁力链接的）"""
    payload = request.json or {}
    stars, keywords, pages, movie_type = _add_data_params(payload)

    if not stars and not keywords:
        response.status = 400
        return _json_response({'error': '请至少输入一个演员 ID 或搜索关键词'})

    return _submit_task('preview', {'stars': stars, 'keywords': keywords,
                                    'pages': pages, 'movie_type': movie_type})


def _enrich_items_with_rate(items, rate_filter=''):
    '''
    为搜索结果添加打标状态（筛选已在数据库层面完成）
    '''
    from bustag.spider.db import ItemRate

    rates = {rate.item_id: rate for rate in ItemRate.select().where(
        ItemRate.item.in_([item.fanhao for item in items]))} if items else {}
    for it in items:
        _remove_extra_tags(it)
        it_rate = rates.get(it.fanhao)
        it.rate_value = it_rate.rate_value if it_rate else None
        it.rate_type = it_rate.rate_type if it_rate else None


@route('/api/search')
def api_search():
    """搜索"""
    from bustag.spider.db import Item
    from bustag.spider import db as db_module

    query = request.query.getunicode('q', '').strip()
    tag_id = request.query.get('tag_id', '').strip()
    star_id = request.query.get('star_id', '').strip()
    rate_filter = request.query.get('rate_filter', '').strip()
    page = int(request.query.get('page', 1))
    include_tags = request.query.get('include_tags', 'false') == 'true'
    dictionary = _tag_dictionary() if include_tags else {}

    item = None
    tag_items = []
    page_info = None
    tag_value = ''

    if query:
        # 规范化番号（大写 + 补连字符），尽量精确命中
        normalized = _normalize_fanhao(query)
        item = Item.get_by_fanhao(normalized) if normalized else None
        if item:
            matches, _ = db_module.get_items_by_keyword(
                query, rate_filter=rate_filter, exact_fanhao=item.fanhao)
            item = matches[0] if matches else None
            _enrich_items_with_rate(matches)
        else:
            tag_items, page_info = db_module.get_items_by_keyword(
                query, page=page, rate_filter=rate_filter)
            _enrich_items_with_rate(tag_items)
    elif tag_id:
        tag_items, page_info = db_module.get_items_by_tag_id(
            int(tag_id), page=page, rate_filter=rate_filter or None)
        tag = db_module.Tag.get_or_none(db_module.Tag.id == int(tag_id))
        tag_value = tag.value if tag else ''
        _enrich_items_with_rate(tag_items)
    elif star_id:
        tag_items, page_info = db_module.get_items_by_tag_id(
            int(star_id), page=page, rate_filter=rate_filter or None)
        tag = db_module.Tag.get_or_none(db_module.Tag.id == int(star_id))
        tag_value = tag.value if tag else ''
        _enrich_items_with_rate(tag_items)

    result = {
        'query': query,
        'tag_value': tag_value,
        'tag_id': tag_id,
        'star_id': star_id,
        'rate_filter': rate_filter,
        'item': _item_rate_to_dict(item) if item else None,
        'tag_items': [_item_rate_to_dict(it) for it in tag_items],
        'page_info': _page_info_to_dict(page_info) if page_info else None,
    }

    if include_tags:
        result.update(dictionary)
    return _json_response(result)


def _tag_dictionary():
    from bustag.spider import db as db_module
    key = f'tags:{db_module.data_revision()}'
    data = _cache_get(key, max_age=300)
    if data is None:
        data = {'genre_tags': db_module.get_genre_tags(), 'star_tags': db_module.get_star_tags()}
        _cache_set(key, data)
    return data


@route('/api/tags')
def api_tags():
    from bustag.spider.db import data_revision
    etag = f'"tags-{data_revision()}"'
    response.set_header('ETag', etag)
    response.set_header('Cache-Control', 'private, max-age=60')
    if request.get_header('If-None-Match') == etag:
        response.status = 304
        return ''
    return _json_response(_tag_dictionary())


@route('/api/img_proxy')
@route('/img_proxy')
def api_img_proxy():
    from urllib.parse import urlsplit
    from bustag.app.images import get_image, cache_dir, can_accelerate
    url = request.query.get('url', '')
    if urlsplit(url).scheme not in ('http', 'https'):
        response.status = 400
        return 'Invalid image URL'
    try:
        width = int(request.query.get('w', 0))
        path, data, mime = get_image(url, width, referer=request.query.get('referer'))
    except (ValueError, TypeError) as exc:
        response.status = 400
        return str(exc)
    except Exception:
        response.status = 502
        return 'Failed to fetch image'
    if path:
        result = static_file(os.path.basename(path), root=cache_dir(), mimetype=mime)
        result.set_header('Cache-Control', 'public, max-age=86400')
        if can_accelerate(path):
            result.set_header('X-Accel-Redirect', '/_image_cache/' + os.path.basename(path))
        return result
    response.content_type = mime
    response.set_header('Cache-Control', 'public, max-age=86400')
    return data


@route('/api/local_play/<id:int>')
def api_local_play(id):
    """播放本地文件"""
    from bustag.spider.db import LocalItem
    local_item = LocalItem.update_play(id)
    file_path = local_item.path
    redirect(file_path)


@route('/api/clear-recommend', method='POST')
def api_clear_recommend():
    return _submit_task('clear')


@route('/api/re-recommend', method='POST')
def api_re_recommend():
    return _submit_task('recommend')


def _parse_magnet_size(m):
    """解析磁力链接的大小字符串，返回字节数"""
    size_str = m.get('size', '0')
    if isinstance(size_str, (int, float)):
        return float(size_str)
    size_str = str(size_str).upper().strip()
    if 'GB' in size_str:
        return float(size_str.replace('GB', '').strip()) * 1024 * 1024 * 1024
    elif 'MB' in size_str:
        return float(size_str.replace('MB', '').strip()) * 1024 * 1024
    elif 'KB' in size_str:
        return float(size_str.replace('KB', '').strip()) * 1024
    try:
        return float(size_str)
    except (ValueError, TypeError):
        return 0


def _get_best_magnet(fanhao):
    """获取影片的最大磁力链接（实时从 javbus-api 获取，不存数据库）

    返回 (magnet_dict, error)；成功时 error 为 None
    """
    from bustag.spider import api_client

    # 1. 获取影片详情，拿到 gid 和 uc
    detail = api_client.get_movie_detail(fanhao)
    gid = detail.get('gid')
    uc = detail.get('uc')
    if not gid or uc is None:
        return None, '无法获取影片信息'

    # 2. 获取磁力链接列表，找文件最大的磁力（按 size 排序）
    magnets = api_client.get_magnets(fanhao, gid, uc)
    if not magnets or not isinstance(magnets, list) or len(magnets) == 0:
        return None, '暂无磁力链接'

    best = max(magnets, key=_parse_magnet_size)
    return {
        'magnet': best.get('link', ''),
        'size': best.get('size', ''),
        'name': best.get('name', ''),
        'count': len(magnets),
    }, None


@route('/api/magnet/<fanhao>')
def api_magnet(fanhao):
    """获取影片的最大磁力链接"""
    try:
        result, error = _get_best_magnet(fanhao)
        if error:
            return _json_response({'error': error})
        return _json_response(result)
    except Exception as e:
        return _json_response({'error': f'获取失败: {str(e)}'})


# ============ 115 云下载 API ============

def _115_error_response(e):
    """Open115Error → HTTP 响应（need_reauth 用 401 语义码便于前端识别）"""
    status = 401 if e.kind in ('need_reauth', 'not_authorized') else 400
    return _json_response({'error': str(e), 'kind': e.kind, 'code': e.code})


@route('/api/115/status')
def api_115_status():
    """115 连接状态（脱敏，不含 token）"""
    from bustag.app import open115
    return _json_response(open115.get_status())


@route('/api/115/config', method='POST')
def api_115_config():
    """保存 115 应用配置（AppID / 保存目录 ID，服务端存储多设备共享）"""
    from bustag.app import open115

    data = request.json or {}
    client_id = str(data.get('client_id', '')).strip()
    if not client_id:
        return _json_response({'error': 'AppID 不能为空'})
    wp_path_id = str(data.get('wp_path_id', '0')).strip() or '0'
    open115.save_config(client_id, wp_path_id)
    return _json_response({'success': True, **open115.get_status()})


@route('/api/115/quota')
def api_115_quota():
    """115 云下载配额"""
    from bustag.app import open115
    try:
        return _json_response(open115.get_quota())
    except open115.Open115Error as e:
        return _115_error_response(e)
    except Exception as e:
        return _json_response({'error': str(e)})


@route('/api/115/auth/start', method='POST')
def api_115_auth_start():
    """发起扫码授权：返回 uid + 二维码内容"""
    from bustag.app import open115
    try:
        result = open115.start_qr_auth()
        return _json_response(result)
    except open115.Open115Error as e:
        return _115_error_response(e)
    except Exception as e:
        return _json_response({'error': str(e)})


@route('/api/115/auth/qr.svg')
def api_115_auth_qr():
    """渲染待授权二维码（SVG）"""
    from bustag.app import open115

    uid = request.query.get('uid', '')
    qrcode_content = open115.get_pending_qrcode(uid)
    if not qrcode_content:
        response.status = 404
        response.content_type = 'text/plain; charset=utf-8'
        return '二维码不存在或已过期'
    try:
        svg = open115.render_qr_svg(qrcode_content)
    except ImportError:
        response.status = 500
        return '缺少 qrcode 依赖，请 pip install qrcode'
    response.content_type = 'image/svg+xml'
    return svg


@route('/api/115/auth/poll')
def api_115_auth_poll():
    """轮询扫码授权状态（服务端长轮询 115，最长约 25 秒）"""
    from bustag.app import open115

    uid = request.query.get('uid', '')
    if not uid:
        return _json_response({'status': 'expired'})
    try:
        status = open115.poll_qr_auth(uid)
        return _json_response({'status': status})
    except open115.Open115Error as e:
        return _json_response({'status': 'error', 'error': str(e)})
    except Exception as e:
        return _json_response({'status': 'error', 'error': str(e)})


@route('/api/115/auth/logout', method='POST')
def api_115_auth_logout():
    """解除 115 授权（清除凭证，保留 AppID 配置）"""
    from bustag.app import open115
    open115.clear_auth()
    return _json_response({'success': True, **open115.get_status()})


@route('/api/115/push/<fanhao>', method='POST')
def api_115_push(fanhao):
    """推送影片的最大磁力到 115 云下载"""
    from bustag.app import open115

    if not open115.is_connected():
        return _json_response({'error': '尚未授权 115 账号', 'kind': 'not_authorized'})
    try:
        result, error = _get_best_magnet(fanhao)
        if error:
            return _json_response({'error': error})
        magnet = result['magnet']
        if not magnet:
            return _json_response({'error': '暂无磁力链接'})

        task = open115.add_magnet_task(magnet)
        return _json_response({
            'success': True,
            'info_hash': task.get('info_hash', ''),
            'name': result.get('name', ''),
            'size': result.get('size', ''),
        })
    except open115.Open115Error as e:
        return _115_error_response(e)
    except Exception as e:
        return _json_response({'error': f'推送失败: {str(e)}'})


@route('/api/version')
def api_version():
    """版本信息"""
    from bustag import __version__
    return _json_response({'version': __version__})


def start_app():
    """启动 Bottle API 服务 + 定时任务调度"""
    from bustag.app.schedule import start_scheduler
    from bustag.util import logger
    import bustag.app.auth  # noqa: F401  注册登录保护钩子与 /api/auth/* 路由

    host = APP_CONFIG.get('app.host', '127.0.0.1')
    port = int(APP_CONFIG.get('app.port', 8000))
    logger.info(f'Starting bustag API on {host}:{port}')

    from bustag.app.tasks import ensure_worker
    ensure_worker()
    start_scheduler()
    run(host=host, port=port, server='paste', quiet=True)
