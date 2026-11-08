import json
import subprocess
import sys
import time
from bustag.app.tasks import Job, submit
from bustag.app import worker
from bustag.spider.db import ItemRate, RATE_TYPE, data_revision


def test_queue_deduplicates_and_persists():
    first = submit('train')
    assert submit('train')['id'] == first['id']
    assert submit('clear')['id'] != first['id']
    assert Job.select().count() == 2


def test_worker_failure_is_recorded():
    job = submit('train')
    assert worker.run_one()
    saved = Job.get_by_id(job['id'])
    assert saved.state == 'failed' and saved.error
    assert saved.active_key is None
    assert submit('train')['id'] != saved.id


def test_worker_batch_download_passes_sources_and_pages():
    from unittest.mock import patch
    job = submit('download', {'stars': ['qs6'], 'keywords': ['三上'], 'pages': 2})
    with patch('bustag.spider.bus_spider.batch_download', return_value=4) as mock_batch:
        assert worker.run_one()
    mock_batch.assert_called_once()
    sources = mock_batch.call_args.args[0]
    kwargs = mock_batch.call_args.kwargs
    assert sources == [{'type': 'star', 'value': 'qs6'}, {'type': 'keyword', 'value': '三上'}]
    assert kwargs['pages'] == 2
    saved = Job.get_by_id(job['id'])
    assert saved.state == 'succeeded'
    assert json.loads(saved.result)['saved'] == 4


def test_worker_preview_returns_candidates_without_saving():
    from unittest.mock import patch
    job = submit('preview', {'stars': ['qs6'], 'pages': 2, 'movie_type': 'uncensored'})
    preview_result = {'movies': [{'fanhao': 'SSIS-401', 'title': 'x'}], 'skipped': 3}
    with patch('bustag.spider.bus_spider.preview_sources', return_value=preview_result) as mock_preview:
        assert worker.run_one()
    mock_preview.assert_called_once()
    assert mock_preview.call_args.args == ([{'type': 'star', 'value': 'qs6'}],)
    kwargs = mock_preview.call_args.kwargs
    assert kwargs['pages'] == 2 and kwargs['movie_type'] == 'uncensored'
    assert callable(kwargs['progress'])
    saved = Job.get_by_id(job['id'])
    assert saved.state == 'succeeded'
    assert json.loads(saved.result) == preview_result


def test_worker_process_clears_only_system_rates(seeded_data):
    ItemRate.update(rate_type=RATE_TYPE.SYSTEM_RATE).where(ItemRate.rate_value == 0).execute()
    revision = data_revision()
    job = submit('clear')
    result = subprocess.run([sys.executable, '-c',
        'from bustag.app.worker import run_one; assert run_one()'], capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr.decode()
    saved = Job.get_by_id(job['id'])
    assert saved.state == 'succeeded'
    assert json.loads(saved.result)['deleted'] == 120
    assert ItemRate.select().count() == 120
    assert data_revision() > revision


def test_worker_restart_marks_interrupted_task_failed():
    job = submit('train')
    Job.update(state='running').where(Job.id == job['id']).execute()
    child = subprocess.Popen([sys.executable, '-m', 'bustag.app.worker'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            saved = Job.get_by_id(job['id'])
            if saved.state == 'failed':
                break
            time.sleep(0.1)
        assert saved.state == 'failed' and '重启' in saved.error
    finally:
        child.terminate()
        child.wait(timeout=10)
