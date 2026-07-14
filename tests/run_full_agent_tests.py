from pathlib import Path
import sys
import time
import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from main import app

OUTPUT_DIR = Path(__file__).resolve().parents[0] / 'agent_test_outputs'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

API_BASE_URL = 'http://127.0.0.1:8002'
TEST_TIMEOUT_SECONDS = 30

client = TestClient(app)

user_test_cases = [
    {
        'id': 'api_health',
        'type': 'api',
        'method': 'get',
        'path': '/api/health',
        'expected_status': 200,
    },
    {
        'id': 'api_filters',
        'type': 'api',
        'method': 'get',
        'path': '/api/filters/kodtingkatantahun',
        'params': {'negeri': 'JOHOR'},
        'expected_status': 200,
        'expected_field': 'values',
    },
    {
        'id': 'api_forecast',
        'type': 'api',
        'method': 'post',
        'path': '/api/forecast/2027',
        'json': {'subject': 'SAINS', 'negeri': 'JOHOR'},
        'expected_status': 200,
        # allow either forecast or summary/fallback
        'expected_field': 'forecast_or_summary',
    },
    {
        'id': 'sim_single_policy',
        'type': 'api',
        'method': 'post',
        'path': '/api/simulate',
        'json': {
            'target_year': 2027,
            'subject': 'SAINS',
            'negeri': 'JOHOR',
            'policy_type': 'option_ratio',
            'option_ratio': 0.70,
        },
        'expected_status': 200,
        'expected_field': 'summary',
    },
    {
        'id': 'sim_combined_policy',
        'type': 'api',
        'method': 'post',
        'path': '/api/simulate',
        'json': {
            'target_year': 2027,
            'subject': 'SAINS',
            'negeri': 'JOHOR',
            'policy_mode': 'combined',
            'policy_type': 'teaching_hours',
            'active_policies': ['teaching_hours', 'teacher_capacity'],
            'teaching_hours_change_pct': 10,
            'teacher_capacity_change_pct': 5,
        },
        'expected_status': 200,
        'expected_field': 'policy_impacts',
    },
    {
        'id': 'agent_explanation',
        'type': 'api',
        'method': 'post',
        'path': '/api/simulate',
        'json': {
            'target_year': 2027,
            'subject': 'SAINS',
            'negeri': 'JOHOR',
            'policy_type': 'option_ratio',
            'option_ratio': 0.70,
        },
        'expected_status': 200,
        'expected_field': 'explanation',
    },
    {
        'id': 'error_invalid_input',
        'type': 'api',
        'method': 'post',
        'path': '/api/simulate',
        'json': {'target_year': 2027, 'subject': 'SAINS', 'negeri': 'JOHOR', 'policy_type': 'unknown_policy'},
        'expected_status': 422,
    },
    {
        'id': 'error_missing_fields',
        'type': 'api',
        'method': 'post',
        'path': '/api/simulate',
        'json': {'subject': 'SAINS'},
        'expected_status': 200,
        'expected_field': 'summary',
    },
]


@dataclass
class TestCaseResult:
    id: str
    status: str
    duration_seconds: float
    error: Optional[str]
    details: Dict[str, Any]


def run_case(case: Dict[str, Any]) -> TestCaseResult:
    start = time.time()
    try:
        method = case['method'].lower()
        kwargs = {}
        if case.get('params'):
            kwargs['params'] = case['params']
        if case.get('json'):
            kwargs['json'] = case['json']
        resp = client.request(method, case['path'], timeout=TEST_TIMEOUT_SECONDS, **kwargs)
        duration = time.time() - start
        try:
            content = resp.json()
        except Exception:
            content = resp.text
        details = {'status_code': resp.status_code, 'response': content}
        expected_status = case.get('expected_status', 200)
        if resp.status_code != expected_status:
            return TestCaseResult(case['id'], 'failed', duration, f'Unexpected status {resp.status_code}', details)
        ef = case.get('expected_field')
        if ef:
            if ef == 'forecast_or_summary':
                if not (isinstance(content, dict) and ('forecast' in content or 'summary' in content or content.get('forecast_only'))):
                    return TestCaseResult(case['id'], 'failed', duration, 'Missing forecast/summary', details)
            else:
                if not (isinstance(content, dict) and ef in content):
                    return TestCaseResult(case['id'], 'failed', duration, f"Missing field {ef}", details)
        return TestCaseResult(case['id'], 'passed', duration, None, details)
    except Exception as exc:
        duration = time.time() - start
        return TestCaseResult(case['id'], 'error', duration, str(exc), {})


if __name__ == '__main__':
    results: List[TestCaseResult] = []
    for c in user_test_cases:
        results.append(run_case(c))
    df = [asdict(r) for r in results]
    out_path = OUTPUT_DIR / 'latest_agent_test_results.json'
    out_path.write_text(json.dumps(df, indent=2), encoding='utf-8')
    # print summary
    passed = sum(1 for r in results if r.status == 'passed')
    failed = sum(1 for r in results if r.status != 'passed')
    print(f'Passed: {passed}, Failed/Other: {failed}')
    for r in results:
        print(r.id, r.status, r.error)
