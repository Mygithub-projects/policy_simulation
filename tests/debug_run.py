from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

print('GET /api/health')
resp = client.get('/api/health')
print(resp.status_code)
print(resp.json())

print('\nPOST /api/forecast/2027')
resp = client.post('/api/forecast/2027', json={'subject': 'SAINS', 'negeri': 'JOHOR'})
print(resp.status_code)
print(resp.json())

print('\nPOST /api/simulate')
resp = client.post('/api/simulate', json={
    'target_year': 2027,
    'subject': 'SAINS',
    'negeri': 'JOHOR',
    'policy_type': 'option_ratio',
    'option_ratio': 0.70,
})
print(resp.status_code)
print(resp.json())
