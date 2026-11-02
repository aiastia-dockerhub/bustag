from concurrent.futures import ThreadPoolExecutor
import io
import os
import time
from PIL import Image
import bottle
from test_auth import call_app
from bustag.app import images


def make_image(size=(1600, 1000)):
    output = io.BytesIO()
    Image.new('RGB', size, color='navy').save(output, 'JPEG')
    return output.getvalue()


def test_same_image_download_is_coalesced(monkeypatch):
    calls = []
    def download(url, referer=None):
        calls.append(url)
        time.sleep(0.03)
        return make_image()
    monkeypatch.setattr(images, '_download', download)
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _: images.get_image('https://example.com/cover.jpg', 480), range(4)))
    assert len(calls) == 1
    assert len({result[0] for result in results}) == 1
    with Image.open(results[0][0]) as image:
        assert image.width == 480 and image.format == 'WEBP'
    assert os.path.getsize(results[0][0]) < len(make_image())


def test_cache_pruning(monkeypatch):
    monkeypatch.setitem(images.APP_CONFIG, 'download.img_cache_max_mb', '1')
    folder = images.cache_dir()
    for index in range(3):
        path = os.path.join(folder, f'{index}.image')
        with open(path, 'wb') as stream:
            stream.write(b'0' * 600_000)
        os.utime(path, (index + 1, index + 1))
    images.prune_cache(force=True)
    assert sum(entry.stat().st_size for entry in os.scandir(folder)) <= 1024 * 1024
    assert os.path.exists(os.path.join(folder, '2.image'))


def test_image_route_streams_and_supports_etag(monkeypatch):
    monkeypatch.setattr(images, '_download', lambda url, referer=None: make_image())
    query = {'QUERY_STRING': 'url=https%3A%2F%2Fexample.com%2Fcover.jpg&w=480'}
    status, headers, body = call_app(bottle.default_app(), 'GET', '/img_proxy', headers=query)
    assert status == 200 and headers['Content-Type'] == 'image/webp'
    assert body[:4] == b'RIFF'
    status, _, body = call_app(bottle.default_app(), 'GET', '/img_proxy', headers={
        **query, 'HTTP_IF_NONE_MATCH': headers['Etag']})
    assert status == 304 and not body


def test_download_carries_source_referer(monkeypatch):
    from unittest.mock import MagicMock
    client = MagicMock()
    response = client.get.return_value.__enter__.return_value
    response.iter_content.return_value = [make_image()]
    monkeypatch.setattr(images, 'session', lambda: client)
    source = 'https://bus.example/movie/TEST-001'
    assert images._download('https://cdn.example/cover.jpg', source)
    headers = client.get.call_args.kwargs['headers']
    assert headers['Referer'] == source
    assert 'AppleWebKit' in headers['User-Agent']


def test_configured_referer_fallback(monkeypatch):
    monkeypatch.setitem(images.APP_CONFIG, 'download.javbus_url', 'https://bus.example/')
    monkeypatch.delitem(images.APP_CONFIG, 'download.img_referer', raising=False)
    assert images._source_referer() == 'https://bus.example/'
    monkeypatch.setitem(images.APP_CONFIG, 'download.img_referer', 'https://source.example/')
    assert images._source_referer() == 'https://source.example/'
    assert images._source_referer('https://movie.example/ABC-123') == 'https://source.example/'
    monkeypatch.delitem(images.APP_CONFIG, 'download.img_referer')
    assert images._source_referer('https://movie.example/ABC-123') == 'https://movie.example/ABC-123'


def test_cached_images_are_readable_by_nginx(tmp_path, monkeypatch):
    import stat
    monkeypatch.setattr(images, '_download', lambda url, referer=None: make_image())
    path, _, _ = images.get_image('https://example.com/cover.jpg', 480)
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o644
    original = images.cache_path('https://example.com/cover.jpg')
    assert stat.S_IMODE(os.stat(original).st_mode) == 0o644
    monkeypatch.setenv('BUSTAG_ACCEL_IMAGES', '1')
    os.chmod(path, 0o600)
    # Even when the private pytest directory prevents acceleration, old files are repaired.
    images.can_accelerate(path)
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o644
    assert images.can_accelerate(path) is False


def test_proxy_falls_back_when_nginx_cannot_read(monkeypatch):
    monkeypatch.setenv('BUSTAG_ACCEL_IMAGES', '1')
    monkeypatch.setattr(images, '_download', lambda url, referer=None: make_image())
    status, headers, body = call_app(bottle.default_app(), 'GET', '/img_proxy', headers={
        'QUERY_STRING': 'url=https%3A%2F%2Fexample.com%2Fcover.jpg&w=480'})
    assert status == 200 and body[:4] == b'RIFF'
    assert 'X-Accel-Redirect' not in headers
