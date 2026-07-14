import urllib.request
import json

url = 'http://127.0.0.1:8002/api/auth/login'
data = json.dumps({'username': 'superadmin', 'password': 'SuperAdmin123!'}).encode()
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')

try:
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    print('✓ LOGIN SUCCESS:')
    print(json.dumps(result, indent=2))
except urllib.error.HTTPError as e:
    raw = e.read().decode()
    print('✗ LOGIN FAILED:')
    print(f'Status: {e.code}')
    print(f'Raw response: {raw}')
    try:
        error = json.loads(raw)
        print(json.dumps(error, indent=2))
    except:
        print(f'(Not JSON)')
except Exception as e:
    print('✗ ERROR:')
    print(str(e))
