"""Exercise five concurrent authenticated users through the public web server."""
import argparse
import base64
import concurrent.futures
from datetime import datetime, timezone
import http.cookiejar
import json
import math
from pathlib import Path
import re
import statistics
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from uuid import uuid4

parser = argparse.ArgumentParser()
parser.add_argument('--fixtures', required=True)
parser.add_argument('--base-url', default='http://127.0.0.1')
parser.add_argument('--output', required=True)
args = parser.parse_args()
manifest = json.loads(Path(args.fixtures).read_text())
assert len(manifest['users']) == 5
base = args.base_url.rstrip('/')
parsed = urllib.parse.urlsplit(base)
barrier = threading.Barrier(5)
lock = threading.Lock()
records = []
active = 0
peak = 0
# A 1x1 PNG is decoded and re-encoded by the real upload endpoint.
image = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGOQq3ADAAGUAN1srQ+kAAAAAElFTkSuQmCC')


def multipart(fields):
    boundary = 'ratemate-' + uuid4().hex
    chunks = []
    for name, value in fields.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for index in range(2):
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="item_image_{index}"; filename="item.png"\r\nContent-Type: image/png\r\n\r\n'.encode() + image + b'\r\n')
    chunks.append(f'--{boundary}--\r\n'.encode())
    return b''.join(chunks), 'multipart/form-data; boundary=' + boundary


def visitor(number, fixture):
    global active, peak
    jar = http.cookiejar.CookieJar()
    jar.set_cookie(http.cookiejar.Cookie(
        0, manifest['cookie_name'], fixture['session_key'], None, False,
        parsed.hostname, False, False, '/', True, parsed.scheme == 'https',
        None, True, None, None, {}, False,
    ))
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    csrf = ''

    def request(method, path, expected=200, data=None, content_type=None, json_result=True):
        global active, peak
        headers = {'Origin': base}
        if csrf:
            headers['X-CSRFToken'] = csrf
        if content_type:
            headers['Content-Type'] = content_type
        req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
        started = time.perf_counter()
        with lock:
            active += 1
            peak = max(peak, active)
        status = 0
        ok = False
        try:
            try:
                response = opener.open(req, timeout=60)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                status = response.status
                body = response.read()
            if status != expected:
                raise RuntimeError(f'{method} {path}: expected {expected}, received {status}')
            result = json.loads(body) if json_result else body
            ok = True
            return result
        finally:
            elapsed = time.perf_counter() - started
            with lock:
                active -= 1
                records.append({'user': number, 'method': method, 'path': path,
                                'status': status, 'success': ok, 'seconds': round(elapsed, 6)})

    try:
        barrier.wait(timeout=30)
        html = request('GET', '/', json_result=False).decode()
        for asset in sorted(set(re.findall(r'(?:src|href)="(/assets/[^" ]+)"', html))):
            request('GET', asset, json_result=False)
        csrf = request('GET', '/api/auth/csrf/')['csrfToken']
        profile = request('GET', '/api/auth/profile/')
        assert profile['userName'] == fixture['username'], 'Session identity mismatch'
        for round_number in range(1, 3):
            request('GET', '/api/templates/?page=1')
            payload, kind = multipart({
                'title': f'A3 concurrency {manifest["tag"]} user {number} round {round_number}',
                'description': 'Temporary concurrency test data',
                'criteria': json.dumps([{'name': 'Quality', 'weight': 1}]),
                'items': json.dumps([{'name': 'First'}, {'name': 'Second'}]),
            })
            created = request('POST', '/api/templates/', 201, payload, kind)
            template_id = created['id']
            detail = request('GET', f'/api/templates/{template_id}/')
            assert len(detail['items']) == 2 and len(detail['criteria']) == 1
            request('GET', urllib.parse.urlsplit(detail['items'][0]['imageUrl']).path, json_result=False)
            scores = [{'itemId': item['id'], 'criterionId': detail['criteria'][0]['id'], 'score': 4}
                      for item in detail['items']]
            rating = request('POST', '/api/ratings/', 201,
                             json.dumps({'templateId': template_id, 'isPublic': False, 'scores': scores}).encode(),
                             'application/json')
            assert len(rating['ranking']) == 2
            comment = request('POST', f'/api/templates/{template_id}/comments/', 201,
                              json.dumps({'content': 'Temporary concurrency test comment'}).encode(),
                              'application/json')
            history = request('GET', '/api/ratings/?page=1')
            assert any(result['id'] == rating['id'] for result in history['results'])
            request('DELETE', f'/api/templates/{template_id}/comments/{comment["id"]}/', 204, json_result=False)
        return {'user': number, 'completed': True}
    except Exception as error:
        return {'user': number, 'completed': False, 'error': str(error)}


started = time.perf_counter()
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(visitor, n, fixture) for n, fixture in enumerate(manifest['users'], 1)]
    users = [future.result() for future in futures]
elapsed = time.perf_counter() - started
latencies = sorted(row['seconds'] for row in records)
failures = sum(not row['success'] for row in records)
passed = all(user['completed'] for user in users) and failures == 0 and peak == 5
summary = {
    'timestamp_utc': datetime.now(timezone.utc).isoformat(),
    'base_url': base, 'users': 5, 'rounds_per_user': 2,
    'peak_concurrent_requests': peak, 'requests': len(records),
    'successful_requests': len(records) - failures, 'failed_requests': failures,
    'elapsed_seconds': round(elapsed, 4),
    'median_ms': round(statistics.median(latencies) * 1000, 2) if latencies else None,
    'p95_ms': round(latencies[math.ceil(len(latencies) * .95) - 1] * 1000, 2) if latencies else None,
    'max_ms': round(max(latencies) * 1000, 2) if latencies else None,
    'passed': passed,
    'workload': 'Frontend/assets, CSRF, authenticated profile, template list, image upload and creation, '
                'template detail, media download, private rating, comment creation/deletion and rating history.',
    'visitor_results': users,
}
output = Path(args.output)
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps({'summary': summary, 'requests': records}, indent=2) + '\n')
print(json.dumps(summary, indent=2))
print('PASS: five concurrent authenticated users completed all workflows.' if passed else 'FAIL: review visitor_results.')
raise SystemExit(0 if passed else 1)
