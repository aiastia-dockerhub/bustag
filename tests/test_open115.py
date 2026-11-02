'''
115 客户端单元测试（全部 mock HTTP，不打真实 API）
'''
import os
import json
import time
import stat

import pytest

from bustag.app import open115


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    '''把 data/ 指到临时目录，避免测试写坏真实凭证文件'''
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    monkeypatch.chdir(tmp_path)
    # 重置模块级缓存状态
    open115._last_refresh.update(ts=0.0, success=False)
    open115._pending_auth.clear()
    yield
    open115._last_refresh.update(ts=0.0, success=False)
    open115._pending_auth.clear()


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class FakeLib:
    '''requests 替身：按 (method, url) 注册响应，记录调用'''
    def __init__(self):
        self.responses = {}
        self.calls = []

    def register(self, method, url, payload):
        self.responses[(method.upper(), url)] = payload

    def _do(self, method, url, **kwargs):
        self.calls.append((method.upper(), url, kwargs))
        payload = self.responses.get((method.upper(), url), {})
        return FakeResponse(payload)

    def post(self, url, **kwargs):
        return self._do('post', url, **kwargs)

    def get(self, url, **kwargs):
        return self._do('get', url, **kwargs)

    def request(self, method, url, **kwargs):
        return self._do(method, url, **kwargs)


@pytest.fixture
def fake_lib(monkeypatch):
    lib = FakeLib()
    monkeypatch.setattr(open115, 'req_lib', lib)
    yield lib


# ============ PKCE ============

def test_pkce_rfc7636_vector():
    '''RFC 7636 附录 B 官方测试向量'''
    verifier = 'dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk'
    assert open115.gen_code_challenge(verifier) == 'E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM'


def test_gen_code_verifier_length():
    for _ in range(10):
        v = open115.gen_code_verifier()
        assert 43 <= len(v) <= 128
        # url-safe 字符集
        assert all(c.isalnum() or c in '-_.' for c in v)


# ============ 凭证存储 ============

def test_save_state_atomic_and_permissions():
    open115.save_state({'client_id': 'app123', 'access_token': 'at'})
    path = open115._token_path()
    assert os.path.exists(path)
    mode = stat.S_IMODE(os.stat(path).st_mode)
    assert mode == 0o600, f'凭证文件权限必须 0600, 实际 {oct(mode)}'
    with open(path) as f:
        assert json.load(f)['client_id'] == 'app123'
    # 不残留 tmp 文件
    assert not os.path.exists(path + '.tmp')


def test_save_config_preserves_tokens():
    open115.save_state({'client_id': 'old', 'access_token': 'at', 'refresh_token': 'rt'})
    open115.save_config('new_app', '12345')
    state = open115.load_state()
    assert state['client_id'] == 'new_app'
    assert state['wp_path_id'] == '12345'
    assert state['access_token'] == 'at'  # token 不受影响


def test_clear_auth_keeps_config():
    open115.save_state({
        'client_id': 'app1', 'wp_path_id': '5',
        'access_token': 'at', 'refresh_token': 'rt',
        'expires_at': 1, 'authed_at': 2, 'need_reauth': True,
    })
    open115.clear_auth()
    state = open115.load_state()
    assert state['client_id'] == 'app1'
    assert state['wp_path_id'] == '5'
    assert 'access_token' not in state
    assert 'refresh_token' not in state
    assert state['need_reauth'] is False


def test_get_status_never_exposes_tokens():
    open115.save_state({
        'client_id': 'app1', 'wp_path_id': '0',
        'access_token': 'SECRET_AT', 'refresh_token': 'SECRET_RT',
        'expires_at': int(time.time()) + 1000, 'authed_at': int(time.time()),
    })
    s = open115.get_status()
    assert s['connected'] is True
    assert s['configured'] is True
    dumped = json.dumps(s)
    assert 'SECRET_AT' not in dumped
    assert 'SECRET_RT' not in dumped
    assert 'access_token' not in s
    assert 'refresh_token' not in s


# ============ 刷新引擎 ============

def _make_connected_state():
    open115.save_state({
        'client_id': 'app1',
        'access_token': 'old_at',
        'refresh_token': 'old_rt',
        'expires_at': int(time.time()) + 3600,
        'authed_at': int(time.time()),
        'need_reauth': False,
    })


def test_refresh_success_rotates_tokens(fake_lib):
    _make_connected_state()
    fake_lib.register('post', open115.URL_REFRESH_TOKEN, {
        'state': 1, 'code': 0, 'message': '',
        'data': {'access_token': 'new_at', 'refresh_token': 'new_rt', 'expires_in': 7200},
    })
    assert open115.refresh_access_token() is True
    state = open115.load_state()
    assert state['access_token'] == 'new_at'
    assert state['refresh_token'] == 'new_rt'  # 轮换：旧凭证被替换
    assert state['expires_at'] > time.time() + 7000


def test_refresh_terminal_code_marks_reauth(fake_lib):
    _make_connected_state()
    fake_lib.register('post', open115.URL_REFRESH_TOKEN, {
        'state': 0, 'code': 40140137, 'message': 'refresh token 永久失效',
    })
    assert open115.refresh_access_token() is False
    assert open115.load_state()['need_reauth'] is True
    # 终态后再次刷新直接拒绝（不再打接口）
    calls_before = len(fake_lib.calls)
    assert open115.refresh_access_token(force=True) is False
    assert len(fake_lib.calls) == calls_before


def test_refresh_transient_failure_no_reauth(fake_lib):
    _make_connected_state()
    fake_lib.register('post', open115.URL_REFRESH_TOKEN, {
        'state': 0, 'code': 500, 'message': 'server busy',
    })
    assert open115.refresh_access_token() is False
    assert open115.load_state().get('need_reauth') is not True  # 非终态不标记


def test_refresh_cooldown_single_flight(fake_lib):
    _make_connected_state()
    fake_lib.register('post', open115.URL_REFRESH_TOKEN, {
        'state': 1, 'code': 0,
        'data': {'access_token': 'at2', 'refresh_token': 'rt2', 'expires_in': 7200},
    })
    assert open115.refresh_access_token() is True
    # 60s 冷却内的重复调用不再打接口（单飞合并）
    assert open115.refresh_access_token() is True
    assert len(fake_lib.calls) == 1


def test_ensure_token_refreshes_near_expiry(fake_lib):
    open115.save_state({
        'client_id': 'app1',
        'access_token': 'old_at',
        'refresh_token': 'rt',
        'expires_at': int(time.time()) + 100,  # 剩余 < 300s
        'authed_at': int(time.time()),
    })
    fake_lib.register('post', open115.URL_REFRESH_TOKEN, {
        'state': 1, 'code': 0,
        'data': {'access_token': 'fresh_at', 'refresh_token': 'rt2', 'expires_in': 7200},
    })
    open115.ensure_token()
    assert open115.load_state()['access_token'] == 'fresh_at'


def test_ensure_token_raises_when_not_authorized():
    with pytest.raises(open115.Open115Error) as ei:
        open115.ensure_token()
    assert ei.value.kind == 'not_authorized'


def test_ensure_token_raises_reauth():
    open115.save_state({'access_token': 'at', 'need_reauth': True})
    with pytest.raises(open115.Open115Error) as ei:
        open115.ensure_token()
    assert ei.value.kind == 'need_reauth'


# ============ API 请求封装 ============

def test_115_request_expired_token_refresh_and_retry(fake_lib):
    '''官方指引：40140125 → 刷新后重试一次'''
    _make_connected_state()
    fake_lib.register('get', open115.URL_GET_QUOTA_INFO, {
        'state': False, 'code': 40140125, 'message': 'token expired',
    })  # 第一次调用返回过期
    fake_lib.register('post', open115.URL_REFRESH_TOKEN, {
        'state': 1, 'code': 0,
        'data': {'access_token': 'new_at', 'refresh_token': 'rt2', 'expires_in': 7200},
    })
    # 重试路径用同一个 URL，注册成功响应会覆盖第一次的注册
    # 因此用第二种方式：检查调用次数来判断重试发生
    quota_ok = {'state': True, 'data': {'surplus': 5, 'used': 1, 'count': 6}}

    calls = []
    orig_do = fake_lib._do

    def smart_do(method, url, **kwargs):
        calls.append((method, url))
        if method == 'post' and url == open115.URL_REFRESH_TOKEN:
            return FakeResponse({
                'state': 1, 'code': 0,
                'data': {'access_token': 'new_at', 'refresh_token': 'rt2', 'expires_in': 7200},
            })
        if url == open115.URL_GET_QUOTA_INFO:
            # 第一次带旧 token → 过期；之后带新 token → 成功
            headers = kwargs.get('headers') or {}
            if headers.get('Authorization') == 'Bearer old_at':
                return FakeResponse({'state': False, 'code': 40140125})
            return FakeResponse(quota_ok)
        return orig_do(method, url, **kwargs)

    fake_lib._do = smart_do
    result = open115.get_quota()
    assert result['surplus'] == 5
    # 调用序列: quota(过期) → refresh → quota(成功)
    assert len(calls) == 3


def test_115_request_no_infinite_retry(fake_lib):
    '''刷新后重试仍失败 → 抛错，不再无限重试'''
    _make_connected_state()
    open115._last_refresh.update(ts=0.0, success=False)

    calls = []

    def smart_do(method, url, **kwargs):
        calls.append((method, url))
        if method == 'post' and url == open115.URL_REFRESH_TOKEN:
            return FakeResponse({
                'state': 1, 'code': 0,
                'data': {'access_token': 'new_at', 'refresh_token': 'rt2', 'expires_in': 7200},
            })
        return FakeResponse({'state': False, 'code': 40140125, 'message': 'still expired'})

    fake_lib._do = smart_do
    with pytest.raises(open115.Open115Error):
        open115.get_quota()
    assert len(calls) == 3  # quota → refresh → quota(重试一次) 后抛错


# ============ 扫码授权 ============

def test_start_qr_auth_requires_client_id():
    with pytest.raises(open115.Open115Error) as ei:
        open115.start_qr_auth()
    assert ei.value.kind == 'not_configured'


def test_start_qr_auth_and_poll_flow(fake_lib):
    open115.save_config('app1')

    captured = {}

    def smart_do(method, url, **kwargs):
        if url == open115.URL_AUTH_DEVICE_CODE:
            captured['challenge'] = kwargs['data']['code_challenge']
            captured['verifier_needed'] = kwargs['data']['code_challenge_method']
            return FakeResponse({
                'state': 1, 'code': 0,
                'data': {'uid': 'UID1', 'time': 123, 'qrcode': 'https://qr.example/x', 'sign': 'SG'},
            })
        if url == open115.QR_STATUS_URL:
            return FakeResponse({'state': 1, 'code': 0, 'data': {'status': 2}})
        if url == open115.URL_DEVICE_CODE_TO_TOKEN:
            captured['uid'] = kwargs['data']['uid']
            captured['verifier'] = kwargs['data']['code_verifier']
            return FakeResponse({
                'state': 1, 'code': 0,
                'data': {'access_token': 'at1', 'refresh_token': 'rt1', 'expires_in': 7200},
            })
        return FakeResponse({})

    fake_lib._do = smart_do
    result = open115.start_qr_auth()
    assert result['uid'] == 'UID1'
    assert captured['verifier_needed'] == 'sha256'
    # challenge 可由保存的 verifier 反推验证（poll 换 token 后对比）
    assert open115.get_pending_qrcode('UID1') == 'https://qr.example/x'

    status = open115.poll_qr_auth('UID1')
    assert status == 'authorized'
    assert captured['uid'] == 'UID1'
    # challenge 与 verifier 匹配
    assert open115.gen_code_challenge(captured['verifier']) == captured['challenge']
    # verifier 单次使用：pending 已删
    assert open115.get_pending_qrcode('UID1') is None
    state = open115.load_state()
    assert state['access_token'] == 'at1'
    assert state['authed_at'] is not None


def test_poll_expired_when_no_pending():
    assert open115.poll_qr_auth('nonexistent') == 'expired'


# ============ 云下载业务 ============

def test_add_magnet_task_success(fake_lib):
    _make_connected_state()
    open115.save_config('app1', '42')

    def smart_do(method, url, **kwargs):
        assert url == open115.URL_ADD_TASK_URLS
        form = {k: v[1] for k, v in (kwargs.get('files') or {}).items()}
        assert form['urls'].startswith('magnet:')
        assert form['wp_path_id'] == '42'
        headers = kwargs.get('headers') or {}
        assert headers.get('Authorization') == 'Bearer old_at'
        return FakeResponse({
            'state': True, 'code': 0,
            'data': [{'state': True, 'code': 0, 'info_hash': 'abc', 'url': 'magnet:...'}],
        })

    fake_lib._do = smart_do
    task = open115.add_magnet_task('magnet:?xt=urn:btih:xxx')
    assert task['info_hash'] == 'abc'


def test_add_magnet_task_quota_error(fake_lib):
    _make_connected_state()
    fake_lib.register('post', open115.URL_ADD_TASK_URLS, {
        'state': True, 'code': 0,
        'data': [{'state': False, 'code': 1000012, 'message': 'quota used up'}],
    })
    with pytest.raises(open115.Open115Error) as ei:
        open115.add_magnet_task('magnet:?xt=urn:btih:xxx')
    assert '配额' in str(ei.value)


# ============ 保活 ============

def test_keepalive_noop_when_not_authorized(fake_lib):
    open115.keepalive()  # 无凭证 → 不抛错不打接口
    assert len(fake_lib.calls) == 0


def test_keepalive_noop_when_fresh(fake_lib):
    open115.save_state({
        'client_id': 'app1', 'access_token': 'at', 'refresh_token': 'rt',
        'expires_at': int(time.time()) + 3600,  # 新鲜
    })
    open115.keepalive()
    assert len(fake_lib.calls) == 0


def test_keepalive_refreshes_when_near_expiry(fake_lib):
    open115.save_state({
        'client_id': 'app1', 'access_token': 'at', 'refresh_token': 'rt',
        'expires_at': int(time.time()) + 100, 'authed_at': int(time.time()),
    })
    fake_lib.register('post', open115.URL_REFRESH_TOKEN, {
        'state': 1, 'code': 0,
        'data': {'access_token': 'at2', 'refresh_token': 'rt2', 'expires_in': 7200},
    })
    open115.keepalive()
    assert open115.load_state()['access_token'] == 'at2'


def test_keepalive_never_raises(fake_lib):
    open115.save_state({
        'client_id': 'app1', 'access_token': 'at', 'refresh_token': 'rt',
        'expires_at': int(time.time()) + 100,
    })
    # 接口持续失败也不抛出（保活只记日志）
    fake_lib.register('post', open115.URL_REFRESH_TOKEN, {'state': 0, 'code': 500})
    open115.keepalive()
