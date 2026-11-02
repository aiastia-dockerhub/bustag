'''
115 生活开放平台客户端

- PKCE 手机扫码授权（无需 AppSecret，自部署场景友好）
- 凭证服务端存储 data/115_token.json（0600、tmp+rename 原子写）
- access_token 自动刷新：单飞锁 + 60s 冷却；refresh_token 轮换后原子保存、停用旧凭证
- 官方终态错误码（40140116/40140119/40140120/40140137）→ need_reauth，停止重试引导重新扫码
- 定时保活：keepalive() 供调度器调用，长期保持登录态

安全约定：access_token / refresh_token 不入日志、不回传前端（get_status 只返回脱敏状态）
'''
import os
import json
import time
import base64
import hashlib
import secrets
import threading
import requests as req_lib
from bustag.util import get_data_path, logger

# ============ 常量 ============

TOKEN_FILE = '115_token.json'

PASSPORT_BASE = 'https://passportapi.115.com/open'
PROAPI_BASE = 'https://proapi.115.com/open'
QR_STATUS_URL = 'https://qrcodeapi.115.com/get/status/'

URL_AUTH_DEVICE_CODE = PASSPORT_BASE + '/authDeviceCode'
URL_DEVICE_CODE_TO_TOKEN = PASSPORT_BASE + '/deviceCodeToToken'
URL_REFRESH_TOKEN = PASSPORT_BASE + '/refreshToken'
URL_ADD_TASK_URLS = PROAPI_BASE + '/offline/add_task_urls'
URL_GET_QUOTA_INFO = PROAPI_BASE + '/offline/get_quota_info'

# 官方错误码语义（见 刷新access_token.md 注意事项）
TERMINAL_REFRESH_CODES = {40140116, 40140119, 40140120, 40140137}
TOKEN_EXPIRED_CODES = {40140125, 40140126}

ACCESS_TTL_BUFFER = 300      # 剩余不足 300s 时提前刷新
REFRESH_COOLDOWN = 60        # 官方：60 秒内重复刷新触发限流
PENDING_TTL = 1800           # 扫码会话内存有效期 30 分钟
REFRESH_TOKEN_LIFETIME = 365 * 86400  # 官方：refresh_token 有效期 1 年且刷新不延长

HTTP_TIMEOUT = 30
POLL_TIMEOUT = 25            # 服务端长轮询 115 状态的单次等待


class Open115Error(Exception):
    '''115 集成业务错误，kind: not_configured / not_authorized / need_reauth / api_error'''
    def __init__(self, message, kind='api_error', code=None):
        super().__init__(message)
        self.kind = kind
        self.code = code


# ============ PKCE 工具 ============

def gen_code_verifier():
    '''生成 43-128 位 url-safe 随机串（RFC 7636）'''
    return secrets.token_urlsafe(72)[:96]


def gen_code_challenge(verifier):
    '''code_challenge = urlsafe_b64(sha256(verifier))，去掉尾部 ='''
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode()


# ============ 凭证存储（服务端文件，0600 原子写） ============

_state_lock = threading.RLock()


def _token_path():
    return get_data_path(TOKEN_FILE)


def load_state():
    '''读取凭证状态（内存缓存 + 文件为权威源）'''
    with _state_lock:
        path = _token_path()
        if not os.path.exists(path):
            return {}
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f'115 凭证文件损坏，忽略: {e}')
            return {}


def save_state(state):
    '''原子写盘：tmp + rename，权限 0600'''
    with _state_lock:
        path = _token_path()
        tmp = path + '.tmp'
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.chmod(tmp, 0o600)
        os.rename(tmp, path)


def is_configured():
    return bool(load_state().get('client_id', '').strip())


def is_connected():
    state = load_state()
    return bool(state.get('access_token')) and not state.get('need_reauth')


def save_config(client_id, wp_path_id=''):
    '''保存应用配置（AppID / 保存目录 ID），与凭证同文件'''
    with _state_lock:
        state = load_state()
        state['client_id'] = (client_id or '').strip()
        state['wp_path_id'] = str(wp_path_id or '0').strip() or '0'
        save_state(state)


def clear_auth():
    '''解除授权：清除凭证，保留 AppID/目录配置'''
    with _state_lock:
        state = load_state()
        for key in ('access_token', 'refresh_token', 'expires_at', 'authed_at'):
            state.pop(key, None)
        state['need_reauth'] = False
        save_state(state)


def get_status():
    '''对外状态（脱敏，绝不包含 token 明文）'''
    state = load_state()
    connected = bool(state.get('access_token')) and not state.get('need_reauth')
    authed_at = state.get('authed_at')
    return {
        'configured': bool(state.get('client_id', '').strip()),
        'connected': connected,
        'need_reauth': bool(state.get('need_reauth')),
        'expires_at': state.get('expires_at'),
        # refresh_token 自首次授权起 1 年有效且刷新不延长，到期必须重新扫码
        'refresh_token_expires_at': (authed_at + REFRESH_TOKEN_LIFETIME) if authed_at else None,
        'client_id': state.get('client_id', ''),
        'wp_path_id': state.get('wp_path_id', '0'),
    }


# ============ token 刷新引擎 ============

_refresh_lock = threading.Lock()
_last_refresh = {'ts': 0.0, 'success': False}


def _mark_terminal(state):
    state['need_reauth'] = True
    save_state(state)
    logger.warning('115 refresh_token 已永久失效，需要重新扫码授权')


def refresh_access_token(force=False):
    '''刷新 access_token。成功返回 True；失败返回 False（终态失败会置 need_reauth）

    - 单飞：并发调用合并为一次实际刷新
    - 冷却：60s 内不重复请求刷新接口（官方限流要求）
    - 轮换：新 access+refresh 原子保存，旧凭证立即停用
    '''
    with _refresh_lock:
        state = load_state()
        # 其他线程刚刷新过，直接用新凭证
        if not force and time.time() - _last_refresh['ts'] < REFRESH_COOLDOWN:
            return _last_refresh['success']
        refresh_token = state.get('refresh_token')
        if not refresh_token or state.get('need_reauth'):
            return False

        try:
            r = req_lib.post(URL_REFRESH_TOKEN, data={'refresh_token': refresh_token},
                             timeout=HTTP_TIMEOUT)
            data = r.json()
        except (req_lib.RequestException, ValueError) as e:
            logger.warning(f'115 刷新请求失败: {e}')
            _last_refresh.update(ts=time.time(), success=False)
            return False

        code = data.get('code')
        if data.get('state') in (0, False) or (isinstance(code, int) and code != 0):
            if code in TERMINAL_REFRESH_CODES:
                _mark_terminal(state)
            else:
                logger.warning(f'115 刷新被拒绝: code={code} message={data.get("message", "")}')
            _last_refresh.update(ts=time.time(), success=False)
            return False

        payload = data.get('data') or {}
        new_access = payload.get('access_token')
        new_refresh = payload.get('refresh_token')
        expires_in = payload.get('expires_in', 7200)
        if not new_access or not new_refresh:
            logger.warning('115 刷新响应缺少凭证字段')
            _last_refresh.update(ts=time.time(), success=False)
            return False

        # 轮换：新旧凭证原子替换（保留 authed_at —— refresh_token 有效期不延长）
        with _state_lock:
            state = load_state()
            state['access_token'] = new_access
            state['refresh_token'] = new_refresh
            state['expires_at'] = int(time.time()) + int(expires_in)
            state['need_reauth'] = False
            save_state(state)
        _last_refresh.update(ts=time.time(), success=True)
        logger.info('115 access_token 刷新成功')
        return True


def ensure_token():
    '''确保有可用 token：临期自动刷新（供 API 调用与保活任务共用）'''
    state = load_state()
    if state.get('need_reauth'):
        raise Open115Error('授权已失效，请重新扫码', kind='need_reauth')
    if not state.get('access_token'):
        raise Open115Error('尚未授权 115 账号', kind='not_authorized')
    expires_at = state.get('expires_at', 0)
    if expires_at - time.time() < ACCESS_TTL_BUFFER:
        if not refresh_access_token():
            if load_state().get('need_reauth'):
                raise Open115Error('授权已失效，请重新扫码', kind='need_reauth')
            raise Open115Error('token 刷新失败，请稍后重试', kind='api_error')


# ============ API 请求封装 ============

def _115_request(method, url, retry_auth=True, **kwargs):
    '''带 Bearer 注入与自动重认证的 115 API 调用，返回解析后的 JSON dict'''
    ensure_token()
    token = load_state()['access_token']
    headers = dict(kwargs.pop('headers', {}))
    headers['Authorization'] = f'Bearer {token}'

    try:
        r = req_lib.request(method, url, headers=headers, timeout=HTTP_TIMEOUT, **kwargs)
        data = r.json()
    except (req_lib.RequestException, ValueError) as e:
        raise Open115Error(f'115 API 请求失败: {e}')

    code = data.get('code')
    if code in TOKEN_EXPIRED_CODES and retry_auth:
        # 官方指引：收到 40140125/40140126 应刷新凭证后重试（仅一次）
        if refresh_access_token(force=True):
            return _115_request(method, url, retry_auth=False, **kwargs)
        raise Open115Error('token 已过期且刷新失败', kind='api_error', code=code)
    if code in TERMINAL_REFRESH_CODES:
        _mark_terminal(load_state())
        raise Open115Error('授权已永久失效，请重新扫码', kind='need_reauth', code=code)
    return data


# ============ 扫码授权（PKCE） ============

_pending_auth = {}       # uid -> {verifier, time, sign, qrcode, created_at}
_pending_lock = threading.Lock()


def start_qr_auth():
    '''第一步：获取设备码与二维码内容（qrcode 内容由前端渲染成图片）'''
    state = load_state()
    client_id = (state.get('client_id') or '').strip()
    if not client_id:
        raise Open115Error('请先填写 AppID', kind='not_configured')

    verifier = gen_code_verifier()
    try:
        r = req_lib.post(URL_AUTH_DEVICE_CODE, data={
            'client_id': client_id,
            'code_challenge': gen_code_challenge(verifier),
            'code_challenge_method': 'sha256',
        }, timeout=HTTP_TIMEOUT)
        data = r.json()
    except (req_lib.RequestException, ValueError) as e:
        raise Open115Error(f'获取设备码失败: {e}')

    payload = data.get('data') or {}
    uid = payload.get('uid')
    if data.get('state') != 1 or not uid:
        raise Open115Error(
            f'获取设备码被拒绝: {data.get("code")} {data.get("message", "")}')
    if not payload.get('qrcode'):
        raise Open115Error('115 未返回二维码内容')

    with _pending_lock:
        # 清理过期会话
        now = time.time()
        for k in [k for k, v in _pending_auth.items() if now - v['created_at'] > PENDING_TTL]:
            _pending_auth.pop(k, None)
        _pending_auth[uid] = {
            'verifier': verifier,
            'time': payload.get('time', 0),
            'sign': payload.get('sign', ''),
            'qrcode': payload['qrcode'],
            'created_at': now,
        }
    return {'uid': uid, 'qrcode': payload['qrcode']}


def get_pending_qrcode(uid):
    with _pending_lock:
        pending = _pending_auth.get(uid)
        if not pending or time.time() - pending['created_at'] > PENDING_TTL:
            _pending_auth.pop(uid, None)
            return None
        return pending['qrcode']


def poll_qr_auth(uid):
    '''轮询扫码状态（服务端长轮询 115）。

    返回: waiting / scanned / authorized / expired
    '''
    with _pending_lock:
        pending = _pending_auth.get(uid)
    if not pending or time.time() - pending['created_at'] > PENDING_TTL:
        with _pending_lock:
            _pending_auth.pop(uid, None)
        return 'expired'

    try:
        r = req_lib.get(QR_STATUS_URL, params={
            'uid': uid, 'time': pending['time'], 'sign': pending['sign'],
        }, timeout=POLL_TIMEOUT + 10)
        data = r.json()
    except (req_lib.RequestException, ValueError):
        # 长轮询超时不代表授权失败，前端可继续轮询
        return 'waiting'

    if data.get('state') == 0:
        with _pending_lock:
            _pending_auth.pop(uid, None)
        return 'expired'

    status = (data.get('data') or {}).get('status')
    if status == 2:
        return _exchange_device_code(uid, pending['verifier'])
    if status == 1:
        return 'scanned'
    return 'waiting'


def _exchange_device_code(uid, verifier):
    '''用设备码 + code_verifier 换取凭证（verifier 单次使用，换完即删）'''
    try:
        r = req_lib.post(URL_DEVICE_CODE_TO_TOKEN, data={
            'uid': uid, 'code_verifier': verifier,
        }, timeout=HTTP_TIMEOUT)
        data = r.json()
    except (req_lib.RequestException, ValueError) as e:
        raise Open115Error(f'换取凭证失败: {e}')

    with _pending_lock:
        _pending_auth.pop(uid, None)

    payload = data.get('data') or {}
    access = payload.get('access_token')
    refresh = payload.get('refresh_token')
    if data.get('state') != 1 or not access or not refresh:
        raise Open115Error(
            f'授权失败: {data.get("code")} {data.get("message", "")}')

    with _state_lock:
        state = load_state()
        state.update({
            'access_token': access,
            'refresh_token': refresh,
            'expires_at': int(time.time()) + int(payload.get('expires_in', 7200)),
            'authed_at': int(time.time()),
            'need_reauth': False,
        })
        save_state(state)
    logger.info('115 扫码授权成功')
    return 'authorized'


# ============ 云下载业务 ============

def add_magnet_task(magnet):
    '''提交磁力（或 http/ftp/ed2k）链接到 115 云下载，返回 data 内该链接的结果'''
    state = load_state()
    wp_path_id = str(state.get('wp_path_id') or '0')
    # 官方要求 multipart/form-data；files+None filename 让 requests 走 multipart
    data = _115_request('POST', URL_ADD_TASK_URLS, files={
        'urls': (None, magnet),
        'wp_path_id': (None, wp_path_id),
    })
    results = data.get('data') or []
    if not isinstance(results, list) or not results:
        raise Open115Error(
            f'添加任务失败: {data.get("code")} {data.get("message", "")}',
            code=data.get('code'))
    first = results[0]
    if not first.get('state'):
        msg_map = {
            91006: '115 存储空间不足',
            1000012: '115 云下载配额已用完',
            990002: '115 参数错误（检查授权信息）',
        }
        err_code = first.get('code')
        raise Open115Error(
            msg_map.get(err_code) or first.get('message') or f'添加任务失败 (code={err_code})',
            code=err_code)
    return first


def get_quota():
    '''云下载配额（surplus 剩余 / used 已用 / count 总量）'''
    data = _115_request('GET', URL_GET_QUOTA_INFO)
    if not data.get('state'):
        raise Open115Error(f'获取配额失败: {data.get("message", "")}')
    return data.get('data') or {}


def keepalive():
    '''定时保活：已授权时确保 token 新鲜（临期刷新）。任何异常只记日志不抛出。'''
    try:
        state = load_state()
        if not state.get('access_token') or state.get('need_reauth'):
            return
        expires_at = state.get('expires_at', 0)
        if expires_at - time.time() < ACCESS_TTL_BUFFER:
            if refresh_access_token():
                logger.info('115 保活刷新成功')
            else:
                logger.warning('115 保活刷新失败')
    except Exception as e:
        logger.warning(f'115 保活异常: {e}')


# ============ 二维码渲染（SVG，纯 Python 无需 Pillow） ============

def render_qr_svg(content):
    import qrcode
    import qrcode.image.svg
    img = qrcode.make(content, image_factory=qrcode.image.svg.SvgPathImage,
                      box_size=12, border=2)
    return img.to_string().decode()
