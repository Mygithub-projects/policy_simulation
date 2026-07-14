"""Simple smoke tests for the FastAPI app and agent workflow.

This file can be run as a normal Python script or imported from a notebook.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from main import app


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200, response.text
    assert str(response.json()["access_mode"]).lower() == "read_only"


def test_forecast_endpoint() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/forecast/2027",
        json={"subject": "SAINS", "negeri": "JOHOR"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    # API returns a serialized output; accept forecast-only indicator or summary
    assert "forecast_only" in payload or "summary" in payload, payload.keys()


def test_simulation_endpoint() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/simulate",
        json={
            "target_year": 2027,
            "subject": "SAINS",
            "negeri": "JOHOR",
            "policy_type": "option_ratio",
            "option_ratio": 0.70,
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert "summary" in payload
    assert "agent_trace" in payload


def run_all_smoke_tests() -> None:
    test_health_endpoint()
    test_forecast_endpoint()
    test_simulation_endpoint()
    print("All smoke tests passed.")


if __name__ == "__main__":
    run_all_smoke_tests()
