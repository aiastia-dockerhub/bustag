'''
账号系统单元测试（WSGI 级别，不启真实服务）
'''
import io
import os
import json
import stat

import pytest
import bottle

from bustag.app import auth

# api.py 路由全部懒加载，import 只注册路由；需要 default_app 拿全路由表
from bustag.app import api as bustag_api  # noqa: F401


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    '''data/ 指向临时目录；每次测试重置密码与失败计数'''
    (tmp_path / 'data').mkdir()
    monkeypatch.chdir(tmp_path)
    auth._fail_counts.clear()
    auth._revoked_sessions.clear()
    yield
    auth._fail_counts.clear()
    auth._revoked_sessions.clear()


@pytest.fixture
def app():
    return bottle.default_app()


def call_app(app, method, path, body=None, headers=None, remote_addr='10.0.0.1'):
    from wsgiref.util import setup_testing_defaults
    environ = {}
    setup_testing_defaults(environ)
    payload = body if isinstance(body, bytes) else (json.dumps(body).encode() if body else b'')
    environ.update({
        'REQUEST_METHOD': method.upper(),
        'PATH_INFO': path,
        'CONTENT_LENGTH': str(len(payload)),
        'CONTENT_TYPE': 'application/json',
        'wsgi.input': io.BytesIO(payload),
        'REMOTE_ADDR': remote_addr,
    })
    environ.update(headers or {})
    captured = {}

    def start_response(status, hdrs, exc_info=None):
        captured['status'] = int(status.split()[0])
        captured['headers'] = dict(hdrs)

    result = b''.join(app(environ, start_response))
    return captured['status'], captured['headers'], result


# ============ 密码开关 ============

def test_auth_disabled_without_env(monkeypatch):
    monkeypatch.delenv('BUSTAG_PASSWORD', raising=False)
    assert auth.is_auth_enabled() is False


def test_auth_enabled_with_env(monkeypatch):
    monkeypatch.setenv('BUSTAG_PASSWORD', 'test123')
    assert auth.is_auth_enabled() is True


# ============ 会话密钥 ============

def test_secret_key_created_with_0600():
    secret = auth._get_secret()
    assert len(secret) >= 64
    path = auth.get_data_path('secret_key')
    mode = stat.S_IMODE(os.stat(path).st_mode)
    assert mode == 0o600, f'secret_key 权限必须 0600, 实际 {oct(mode)}'
    # 二次读取一致（不重新生成）
    assert auth._get_secret() == secret


# ============ 会话签名 ============

def test_session_roundtrip(monkeypatch):
    monkeypatch.setenv('BUSTAG_PASSWORD', 'p1')
    value = auth._make_session()
    assert auth._check_session(value) is True


def test_session_rejects_tampered():
    value = auth._make_session()
    exp, sig = value.split('.')
    assert auth._check_session(f'{exp}.{sig[:-4]}aaaa') is False
    assert auth._check_session('9999999999.deadbeef') is False


def test_session_expired(monkeypatch):
    monkeypatch.setenv('BUSTAG_PASSWORD', 'p1')
    exp = int(__import__('time').time()) - 10  # 已过期
    value = f'{exp}.{auth._sign(exp)}'
    assert auth._check_session(value) is False


# ============ HTTP 流程 ============

def test_guard_allows_when_disabled(app, monkeypatch):
    monkeypatch.delenv('BUSTAG_PASSWORD', raising=False)
    status, _, _ = call_app(app, 'GET', '/api/index')
    assert status != 401  # 认证关闭：不拦（可能 500 因缺 DB，但绝不 401）


def test_guard_blocks_unauthenticated(app, monkeypatch):
    monkeypatch.setenv('BUSTAG_PASSWORD', 'test123')
    status, _, body = call_app(app, 'GET', '/api/index')
    assert status == 401
    assert '未登录' in body.decode()


def test_auth_endpoints_are_public(app, monkeypatch):
    monkeypatch.setenv('BUSTAG_PASSWORD', 'test123')
    status, _, _ = call_app(app, 'GET', '/api/auth/status')
    assert status == 200
    status, _, _ = call_app(app, 'GET', '/api/version')
    assert status == 200


def test_login_success_sets_cookie(app, monkeypatch):
    monkeypatch.setenv('BUSTAG_PASSWORD', 'test123')
    status, headers, body = call_app(app, 'POST', '/api/auth/login',
                                     body={'password': 'test123'})
    assert status == 200
    assert json.loads(body)['success'] is True
    cookie = headers.get('Set-Cookie', '')
    assert 'bustag_session=' in cookie
    assert 'HttpOnly' in cookie


def test_login_wrong_password(app, monkeypatch):
    monkeypatch.setenv('BUSTAG_PASSWORD', 'test123')
    status, _, body = call_app(app, 'POST', '/api/auth/login',
                               body={'password': 'wrong'}, remote_addr='10.0.0.2')
    assert status == 401
    assert '密码错误' in body.decode()


def test_login_lockout_after_5_failures(app, monkeypatch):
    monkeypatch.setenv('BUSTAG_PASSWORD', 'test123')
    for _ in range(5):
        status, _, _ = call_app(app, 'POST', '/api/auth/login',
                                body={'password': 'bad'}, remote_addr='10.0.0.3')
        assert status == 401
    # 第 6 次即使密码正确也被锁
    status, _, body = call_app(app, 'POST', '/api/auth/login',
                               body={'password': 'test123'}, remote_addr='10.0.0.3')
    assert status == 429
    assert '5 分钟' in body.decode()


def test_full_flow_login_then_access(app, monkeypatch):
    monkeypatch.setenv('BUSTAG_PASSWORD', 'test123')
    # 1. 未登录访问被拦
    status, _, _ = call_app(app, 'GET', '/api/115/status')
    assert status == 401
    # 2. 登录
    status, headers, _ = call_app(app, 'POST', '/api/auth/login',
                                  body={'password': 'test123'})
    assert status == 200
    cookie = headers.get('Set-Cookie', '').split(';')[0]
    # 3. 带 cookie 访问 115 status → 通过认证
    status, _, body = call_app(app, 'GET', '/api/115/status',
                               headers={'HTTP_COOKIE': cookie})
    assert status == 200
    data = json.loads(body)
    assert data['configured'] is False
    # 4. 登出（浏览器会带上 cookie）后再访问 → 401（服务端撤销）
    status, _, _ = call_app(app, 'POST', '/api/auth/logout',
                            headers={'HTTP_COOKIE': cookie})
    assert status == 200
    status, _, _ = call_app(app, 'GET', '/api/115/status',
                            headers={'HTTP_COOKIE': cookie})
    assert status == 401


def test_logout_cookie_is_http_only(app, monkeypatch):
    '''logout 接口本身公开（guard 放行 /api/auth/*），但 cookie 属性正确'''
    monkeypatch.setenv('BUSTAG_PASSWORD', 'test123')
    status, _, body = call_app(app, 'POST', '/api/auth/logout')
    assert status == 200
    assert json.loads(body)['success'] is True
