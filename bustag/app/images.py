"""Bounded disk image cache, thumbnail generation and per-key request coalescing."""
import hashlib
import io
import os
import tempfile
import threading
import time
from PIL import Image, ImageOps
from bustag.http import session
from bustag.util import APP_CONFIG, get_data_path

# Fixed stripes bound lock memory, even with many unique image URLs.
_locks = [threading.Lock() for _ in range(64)]
_slots = threading.Semaphore(6)
_resize_slots = threading.Semaphore(2)
_cleanup_lock = threading.Lock()
_last_cleanup = 0.0
MAX_IMAGE_BYTES = 20 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 40_000_000


def cache_dir():
    directory = get_data_path('img_cache')
    os.makedirs(directory, exist_ok=True)
    return directory


def cache_path(url, width=0):
    key = f'{url}\n{width}' if width else url
    digest = hashlib.md5(key.encode()).hexdigest()
    return os.path.join(cache_dir(), digest + ('.webp' if width else '.image'))


def _atomic_write(path, data):
    fd, temporary = tempfile.mkstemp(prefix='.image-', dir=cache_dir())
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _download(url):
    with _slots, session().get(url, headers={
        'Referer': 'https://www.javbus.com/', 'User-Agent': 'Mozilla/5.0'},
        timeout=(5, 15), stream=True) as result:
        result.raise_for_status()
        data = bytearray()
        for chunk in result.iter_content(64 * 1024):
            data.extend(chunk)
            if len(data) > MAX_IMAGE_BYTES:
                raise ValueError('图片超过 20MB 限制')
    # Validate the upstream body before publishing or serving it as an image.
    with Image.open(io.BytesIO(data)) as image:
        image.verify()
    return bytes(data)


def _thumbnail(data, width):
    with _resize_slots, Image.open(io.BytesIO(data)) as image:
        image.draft("RGB", (width, width * 2))
        image = ImageOps.exif_transpose(image)
        image.thumbnail((width, width * 2))
        output = io.BytesIO()
        image.convert('RGB').save(output, format='WEBP', quality=80)
        return output.getvalue()


def content_type(path_or_stream):
    with Image.open(path_or_stream) as image:
        return Image.MIME.get(image.format, 'image/jpeg')


def get_image(url, width=0):
    if width not in (0, 480, 960):
        raise ValueError('不支持的图片尺寸')
    enabled = APP_CONFIG.get('download.img_cache_enabled', 'true').lower() != 'false'
    path = cache_path(url, width)
    lock = _locks[int(hashlib.md5(url.encode()).hexdigest(), 16) % len(_locks)]
    with lock:
        if enabled and os.path.isfile(path):
            return path, None, content_type(path)
        original = cache_path(url)
        if width and enabled and os.path.isfile(original):
            with open(original, 'rb') as stream:
                data = stream.read()
        else:
            data = _download(url)
            if enabled:
                _atomic_write(original, data)
        if width:
            data = _thumbnail(data, width)
        mime = content_type(io.BytesIO(data))
        if enabled:
            if width:
                _atomic_write(path, data)
            prune_cache(protect={path, original})
            return path, None, mime
        return None, data, mime


def prune_cache(protect=frozenset(), force=False):
    global _last_cleanup
    if not _cleanup_lock.acquire(blocking=False):
        return
    try:
        if not force and time.monotonic() - _last_cleanup < 60:
            return
        _last_cleanup = time.monotonic()
        limit = max(1, int(APP_CONFIG.get('download.img_cache_max_mb', 1024))) * 1024 * 1024
        files = []
        for entry in os.scandir(cache_dir()):
            if entry.is_file() and not entry.name.startswith('.'):
                try:
                    stat = entry.stat()
                    files.append((stat.st_mtime, stat.st_size, entry.path))
                except FileNotFoundError:
                    pass
        total = sum(size for _, size, _ in files)
        for _, size, path in sorted(files):
            if total <= limit:
                break
            if path not in protect:
                try:
                    os.unlink(path)
                    total -= size
                except FileNotFoundError:
                    pass
    finally:
        _cleanup_lock.release()
