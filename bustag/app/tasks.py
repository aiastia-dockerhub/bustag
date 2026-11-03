"""Persistent bounded job queue. Heavy work runs in a separate Python process."""
import atexit
import datetime
import hashlib
import json
import os
import subprocess
import sys
import threading
import uuid
from peewee import CharField, TextField, DateTimeField, IntegrityError
from bustag.spider.db import BaseModel, db


class Job(BaseModel):
    id = CharField(primary_key=True)
    kind = CharField()
    state = CharField(default='queued', index=True)
    active_key = CharField(null=True, unique=True)
    payload = TextField(default='{}')
    progress = TextField(default='{}')
    result = TextField(null=True)
    error = TextField(null=True)
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)


_initialized = None
_init_lock = threading.Lock()


def initialize():
    global _initialized
    identity = (id(db), db.database)
    with _init_lock:
        if _initialized != identity:
            db.create_tables([Job])
            _initialized = identity


def serialize(job):
    return {'id': job.id, 'kind': job.kind, 'state': job.state,
            'progress': json.loads(job.progress),
            'result': json.loads(job.result) if job.result else None,
            'error': job.error, 'created_at': job.created_at.isoformat(),
            'updated_at': job.updated_at.isoformat()}


def submit(kind, payload=None):
    if kind not in ('train', 'recommend', 'clear', 'download', 'preview'):
        raise ValueError('未知任务类型')
    initialize()
    encoded = json.dumps(payload or {}, sort_keys=True)
    # Only one active mutation of a given kind; downloads/previews deduplicate identical inputs.
    key = kind + (':' + hashlib.sha256(encoded.encode()).hexdigest() if kind in ('download', 'preview') else '')
    existing = Job.get_or_none(Job.active_key == key)
    if existing:
        return serialize(existing)
    if Job.select().where(Job.state.in_(['queued', 'running'])).count() >= 20:
        raise ValueError('后台任务队列已满，请稍后再试')
    try:
        job = Job.create(id=uuid.uuid4().hex, kind=kind, active_key=key, payload=encoded)
    except IntegrityError:
        job = Job.get(Job.active_key == key)
    return serialize(job)


_worker = None
_worker_lock = threading.Lock()


def ensure_worker():
    """Local source runs start a child; Docker supervises the worker independently."""
    global _worker
    if os.environ.get('BUSTAG_EXTERNAL_WORKER') == '1':
        return
    with _worker_lock:
        if _worker is None or _worker.poll() is not None:
            _worker = subprocess.Popen([sys.executable, '-m', 'bustag.app.worker'],
                                       env={**os.environ, 'BUSTAG_PARENT_PID': str(os.getpid())})


@atexit.register
def _stop_worker():
    if _worker is not None and _worker.poll() is None:
        _worker.terminate()
        try:
            _worker.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _worker.kill()
            _worker.wait()
