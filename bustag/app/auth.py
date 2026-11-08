'''
Bustag 简单账号系统

- 密码来源：环境变量 BUSTAG_PASSWORD；未设置时认证关闭（保持原有无登录用法）
- 会话：bustag_session cookie（HttpOnly / SameSite=Lax / 30 天），
  值为 `exp.hmac_sha256(secret, str(exp))`，secret 为首次自动生成的随机数存 data/secret_key
- 保护范围：所有 /api/* 路由（放行 /api/auth/* 与 /api/version），未登录返回 401 JSON
- 防爆破：按 IP 内存计数，5 次失败锁 5 分钟
'''
import os
import hmac
import hashlib
import secrets
import time
import threading
import json
from bottle import route, request, response, hook, HTTPResponse
from bustag.util import get_data_path, logger

SESSION_COOKIE = 'bustag_session'
SESSION_DAYS = 30
SESSION_TTL = SESSION_DAYS * 86400

# 登录失败锁定：同一 IP 5 次失败锁 5 分钟
FAIL_LIMIT = 5
FAIL_LOCK_SECONDS = 300

_secret_lock = threading.Lock()
_fail_counts = {}  # ip -> {'count': int, 'locked_until': float}
_revoked_sessions = set()  # 登出撤销的会话（进程内存，重启自动清空）


def _get_secret():
    '''读取（或首次生成）会话签名密钥，存 data/secret_key，权限 0600'''
    path = get_data_path('secret_key')
    with _secret_lock:
        if os.path.exists(path):
            with open(path, 'r') as f:
                secret = f.read().strip()
                if secret:
                    return secret
        secret = secrets.token_hex(32)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(secret)
    return secret


def is_auth_enabled():
    '''BUSTAG_PASSWORD 未设置或为空时，认证关闭（向后兼容）'''
    return bool(os.environ.get('BUSTAG_PASSWORD', '').strip())


def _get_password():
    return os.environ.get('BUSTAG_PASSWORD', '').strip()


def _sign(exp):
    secret = _get_secret()
    msg = str(exp).encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


def _make_session():
    exp = int(time.time()) + SESSION_TTL
    return f'{exp}.{_sign(exp)}'


def _check_session(value):
    '''校验会话 cookie：格式合法、签名匹配、未过期、未被登出撤销'''
    if not value or '.' not in value:
        return False
    exp_str, _, sig = value.rpartition('.')
    if not exp_str.isdigit():
        return False
    if value in _revoked_sessions:
        return False
    exp = int(exp_str)
    if exp < time.time():
        return False
    return hmac.compare_digest(sig, _sign(exp))


def is_logged_in():
    return _check_session(request.get_cookie(SESSION_COOKIE, ''))


def _client_ip():
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def _is_locked(ip):
    entry = _fail_counts.get(ip)
    if not entry:
        return False
    if entry.get('locked_until', 0) > time.time():
        return True
    # 锁定期过后清零
    if entry.get('locked_until', 0) and entry.get('locked_until', 0) <= time.time():
        _fail_counts.pop(ip, None)
    return False


def _record_fail(ip):
    entry = _fail_counts.setdefault(ip, {'count': 0, 'locked_until': 0})
    entry['count'] += 1
    if entry['count'] >= FAIL_LIMIT:
        entry['locked_until'] = time.time() + FAIL_LOCK_SECONDS
        entry['count'] = 0
        logger.warning(f'IP {ip} 登录失败次数过多，锁定 {FAIL_LOCK_SECONDS} 秒')


def _json(data, status=200):
    response.status = status
    response.content_type = 'application/json; charset=utf-8'
    return json.dumps(data, ensure_ascii=False).encode('utf-8')


def _json_abort(data, status):
    '''以异常方式终止请求并返回 JSON（before_request hook 的返回值会被
    bottle 忽略，必须 raise HTTPResponse 才能阻止路由执行）'''
    body = json.dumps(data, ensure_ascii=False)
    return HTTPResponse(body=body, status=status,
                        headers={'Content-Type': 'application/json; charset=utf-8'})


# ============ 认证保护钩子 ============

PUBLIC_PATHS = ('/api/auth/', '/api/version')


@hook('before_request')
def auth_guard():
    '''保护 /api/*：未登录抛 401（认证关闭时直接放行）'''
    path = request.path
    if not path.startswith('/api'):
        return
    for p in PUBLIC_PATHS:
        if path.startswith(p):
            return
    if not is_auth_enabled():
        return
    if is_logged_in():
        return
    raise _json_abort({'error': '未登录或会话已过期'}, status=401)


# ============ 登录路由 ============

@route('/api/auth/status')
def auth_status():
    return _json({'enabled': is_auth_enabled(), 'authed': is_logged_in()})


@route('/api/auth/login', method='POST')
def auth_login():
    ip = _client_ip()
    if _is_locked(ip):
        return _json({'error': '失败次数过多，请 5 分钟后再试'}, status=429)

    data = request.json or {}
    password = str(data.get('password', ''))
    time.sleep(0.3)  # 恒定延迟，略微增加爆破成本
    if password and hmac.compare_digest(password, _get_password()):
        _fail_counts.pop(ip, None)
        response.set_cookie(
            SESSION_COOKIE, _make_session(),
            max_age=SESSION_TTL, path='/', httponly=True, samesite='Lax',
        )
        logger.info(f'IP {ip} 登录成功')
        return _json({'success': True})

    _record_fail(ip)
    return _json({'error': '密码错误'}, status=401)


@route('/api/auth/logout', method='POST')
def auth_logout():
    value = request.get_cookie(SESSION_COOKIE, '')
    if value:
        _revoked_sessions.add(value)
    response.delete_cookie(SESSION_COOKIE, path='/')
    return _json({'success': True})
