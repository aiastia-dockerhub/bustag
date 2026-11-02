"""Exercise built Nuxt + Bottle + a separate worker using disposable data.

Run after npm run build --prefix frontend:
  .venv/bin/python scripts/smoke_test.py
  .venv/bin/python scripts/smoke_test.py --browser

For the browser option, first install Playwright Chromium:
  cd frontend && npx playwright install chromium
Or set PLAYWRIGHT_CHANNEL=chrome to use an installed Chrome.
"""
import json
import os
from pathlib import Path
import subprocess
import signal
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

repo = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo))
folder = tempfile.TemporaryDirectory(prefix='bustag-smoke-')
data = Path(folder.name)
(data / 'config.ini').write_text('[database]\ntype=sqlite\n[app]\nhost=127.0.0.1\nport=3901\n[download]\ncount=0\ninterval=86400\nmovie_type=normal\napi_interval=0\n')
os.environ['BUSTAG_DATA_DIR'] = str(data)
os.environ['BUSTAG_PASSWORD'] = 'smoke-test-password'
os.environ.pop('TESTING', None)
os.environ.pop('BUSTAG_EXTERNAL_WORKER', None)
from bustag.spider.db import Item, ItemRate, Tag, ItemTag, db
from datetime import date
with db.atomic():
    genre = Tag.create(type_='genre', value='Smoke genre', url='/genre/smoke')
    for index in range(260):
        item = Item.create(fanhao=f'SMOKE-{index:04d}', title=f'Smoke movie {index}',
                           url=f'https://example.com/{index}', release_date=date.today(),
                           meta_info=json.dumps({'cover_img_url': 'http://127.0.0.1:3902/cover.jpg'}))
        ItemTag.create(item=item.fanhao, tag=genre)
        if index < 250:
            ItemRate.create(item=item.fanhao, rate_type=1 if index < 240 else 2, rate_value=index % 2)
db.close()
from PIL import Image
import io
image = io.BytesIO()
Image.new('RGB', (1200, 800), 'navy').save(image, 'JPEG')
class Images(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'image/jpeg')
        self.end_headers()
        self.wfile.write(image.getvalue())
    def log_message(self, *_):
        pass
images = ThreadingHTTPServer(('127.0.0.1', 3902), Images)
threading.Thread(target=images.serve_forever, daemon=True).start()
logs = [open('/tmp/bustag-smoke-api.log', 'w'), open('/tmp/bustag-smoke-nuxt.log', 'w')]
children = []
try:
    children.append(subprocess.Popen([sys.executable, '-c', 'from bustag.app.api import start_app; start_app()'],
                                    cwd=repo, stdout=logs[0], stderr=logs[0], start_new_session=True))
    env = dict(os.environ, HOST='127.0.0.1', PORT='3900', NUXT_API_BASE='http://127.0.0.1:3901')
    children.append(subprocess.Popen(['node', 'frontend/.output/server/index.mjs'], cwd=repo, env=env,
                                    stdout=logs[1], stderr=logs[1], start_new_session=True))
    import requests
    client = requests.Session()
    for _ in range(100):
        try:
            if client.get('http://127.0.0.1:3900/api/version', timeout=1).ok:
                break
        except requests.RequestException:
            pass
        time.sleep(0.1)
    root = 'http://127.0.0.1:3900'
    result = client.get(root + '/', allow_redirects=False, timeout=10)
    assert result.status_code in (302, 307), (result.status_code, result.text[:500])
    assert '/login' in result.headers['Location']
    assert client.post(root+'/api/auth/login', json={'password': 'smoke-test-password'}).ok
    html = client.get(root + '/', timeout=15)
    Path('/tmp/bustag-smoke-page.html').write_text(html.text)
    assert html.ok and 'Smoke movie' in html.text, html.text[-1500:]
    assert 'fetchpriority="high"' in html.text
    assert '&amp;w=480' in html.text
    assert client.get(root+'/tagit').ok
    assert 'Smoke genre' in client.get(root+'/search').text
    assert client.get(root+'/model').ok
    img = client.get(root+'/img_proxy', params={'url':'http://127.0.0.1:3902/cover.jpg','w':480})
    assert img.ok and img.headers['Content-Type'].startswith('image/webp'), img.text[:200]
    started=time.perf_counter()
    job = client.post(root+'/api/do-training', json={})
    accepted_ms=(time.perf_counter()-started)*1000
    assert job.status_code == 202, job.text
    jobid=job.json()['job']['id']
    latency=[]
    deadline=time.monotonic()+25
    while time.monotonic()<deadline:
        start=time.perf_counter()
        assert client.get(root+'/api/tagit').ok
        latency.append((time.perf_counter()-start)*1000)
        status=client.get(root+'/api/jobs/'+jobid).json()['job']
        if status['state'] in ('succeeded','failed'):
            break
        time.sleep(0.1)
    assert status['state']=='succeeded', status
    rec=client.post(root+'/api/re-recommend',json={}).json()['job']
    while time.monotonic()<deadline:
        status=client.get(root+'/api/jobs/'+rec['id']).json()['job']
        if status['state'] in ('succeeded','failed'):
            break
        time.sleep(0.1)
    assert status['state']=='succeeded', status
    assert status['result']['total']==20, status
    # A separate browser request must not inherit the first user's SSR auth/data.
    outsider=requests.get(root+'/', allow_redirects=False)
    assert outsider.status_code in (302,307)
    assert client.get(root+'/api/115/status').ok
    print(json.dumps({'SSR':'authenticated content present, unauthenticated requests redirected',
                      'thumbnail':'480px WebP served through Nuxt', 'train_submission_ms':round(accepted_ms,2),
                      'interactive_api_max_ms_during_training':round(max(latency),2),
                      'recommendation':status['result']},ensure_ascii=False))
    # Optional browser check is invoked by a separate process while this fixture is alive.
    if '--browser' in sys.argv:
        from bustag.spider.db import touch_data
        ItemRate.update(rate_value=1).where(ItemRate.rate_type == 2).execute()
        touch_data()
        db.close()
        subprocess.run(['npm', 'run', 'test:e2e', '--prefix', str(repo / 'frontend')],
                       check=True, timeout=120)
finally:
    for child in children:
        os.killpg(child.pid, signal.SIGTERM)
    for child in children:
        try: child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill(); child.wait()
    for stream in logs: stream.close()
    images.shutdown()
    folder.cleanup()
