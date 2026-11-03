"""Check the public login limit using a random nonexistent username."""
import argparse
import http.cookiejar
import json
import secrets
import urllib.error
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('--base-url', default='http://127.0.0.1')
args = parser.parse_args()
base = args.base_url.rstrip('/')
opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
)
with opener.open(base + '/api/auth/csrf/', timeout=30) as response:
    token = json.load(response)['csrfToken']
username = 'a3-check-' + secrets.token_hex(12)
body = json.dumps({'username': username, 'password': secrets.token_urlsafe(24)}).encode()
print('Synthetic nonexistent username:', username)
statuses = []
for attempt in range(1, 7):
    request = urllib.request.Request(base + '/api/auth/login/', data=body, headers={
        'Content-Type': 'application/json',
        'X-CSRFToken': token,
        'Origin': base,
    })
    try:
        response = opener.open(request, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        statuses.append(response.status)
        print(f'Attempt {attempt}: HTTP {response.status}')
        if attempt == 6:
            retry_after = response.headers.get('Retry-After', '')
            print('Retry-After:', retry_after)
            assert retry_after.isdigit() and int(retry_after) > 0, 'Missing retry interval'
assert statuses == [401, 401, 401, 401, 401, 429], statuses
print('PASS: shared login limit; no real account was used.')
