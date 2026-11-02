"""Serialize model mutations across API, CLI and worker processes."""
import fcntl
import os
import threading
from contextlib import contextmanager
from bustag.util import get_data_path

_lock = threading.Lock()


class ModelBusyError(RuntimeError):
    pass


@contextmanager
def model_operation():
    if not _lock.acquire(blocking=False):
        raise ModelBusyError('模型任务正在执行，请稍后再试')
    stream = None
    try:
        path = get_data_path('model/operation.lock')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        stream = open(path, 'a')
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ModelBusyError('模型任务正在执行，请稍后再试') from None
        yield
    finally:
        if stream:
            stream.close()
        _lock.release()
