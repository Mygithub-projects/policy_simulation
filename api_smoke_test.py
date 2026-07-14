"""Exercise the key FastAPI endpoints without starting a web server."""

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)

_login = client.post("/api/auth/login", json={"username": "superadmin", "password": "P@ssword.123"})
assert _login.status_code == 200, _login.text
AUTH_HEADERS = {"X-Auth-Token": _login.json()["token"]}

health = client.get("/api/health")
assert health.status_code == 200, health.text
assert str(health.json()["access_mode"]).lower() == "read_only"

levels = client.get("/api/filters/kodtingkatantahun", params={"negeri": "JOHOR"})
assert levels.status_code == 200, levels.text
assert {"D1", "D2", "D3", "T1", "T2", "T3"}.issubset(
    set(levels.json()["values"])
)

forecast = client.post(
    "/api/forecast/2027",
    json={"subject": "SAINS", "negeri": "JOHOR"},
    headers=AUTH_HEADERS,
)
assert forecast.status_code == 200, forecast.text

simulation = client.post(
    "/api/simulate",
    json={
        "target_year": 2027,
        "subject": "SAINS",
        "negeri": "JOHOR",
        "policy_type": "option_ratio",
        "option_ratio": 0.70,
    },
    headers=AUTH_HEADERS,
)
assert simulation.status_code == 200, simulation.text
payload = simulation.json()
assert payload["summary"]["scenario_required_2027"] >= 0
assert (
    payload["summary"]["scenario_option_gap"]
    >= payload["summary"]["baseline_option_gap"]
)
assert len(payload["agent_trace"]) == 5

coteaching = client.post(
    "/api/simulate",
    json={
        "target_year": 2027,
        "subject": "SAINS",
        "negeri": "JOHOR",
        "kodtingkatantahun": ["D1", "D2", "D3"],
        "policy_type": "coteaching",
        "coteaching_share_pct": 50,
    },
    headers=AUTH_HEADERS,
)
assert coteaching.status_code == 200, coteaching.text
coteaching_payload = coteaching.json()
assert coteaching_payload["scenario"]["kodtingkatantahun"] == ["D1", "D2", "D3"]
assert coteaching_payload["summary"]["coteaching_eligible_fte_2027"] > 0
assert coteaching_payload["summary"]["coteaching_extra_fte_2027"] > 0
assert (
    coteaching_payload["summary"]["scenario_required_2027"]
    >= coteaching_payload["summary"]["baseline_required_2027"]
)

combined_two = client.post(
    "/api/simulate",
    json={
        "target_year": 2027,
        "subject": "SAINS",
        "negeri": "JOHOR",
        "policy_mode": "combined",
        "policy_type": "teaching_hours",
        "active_policies": ["teaching_hours", "teacher_capacity"],
        "teaching_hours_change_pct": 10,
        "teacher_capacity_change_pct": 5,
    },
    headers=AUTH_HEADERS,
)
assert combined_two.status_code == 200, combined_two.text
combined_two_payload = combined_two.json()
assert combined_two_payload["scenario"]["policy_mode"] == "combined"
assert len(combined_two_payload["policy_impacts"]) == 2
assert combined_two_payload["summary"]["combined_fte_multiplier"] > 1

combined_all = client.post(
    "/api/simulate",
    json={
        "target_year": 2027,
        "subject": "SAINS",
        "negeri": "JOHOR",
        "kodtingkatantahun": ["D1", "D2", "D3"],
        "policy_mode": "combined",
        "policy_type": "option_ratio",
        "active_policies": [
            "option_ratio",
            "teaching_hours",
            "teacher_capacity",
            "coteaching"
        ],
        "option_ratio": 0.80,
        "teaching_hours_change_pct": 10,
        "teacher_capacity_change_pct": 5,
        "coteaching_share_pct": 20,
    },
    headers=AUTH_HEADERS,
)
assert combined_all.status_code == 200, combined_all.text
combined_all_payload = combined_all.json()
assert len(combined_all_payload["scenario"]["active_policies"]) == 4
assert len(combined_all_payload["policy_impacts"]) == 4
assert combined_all_payload["summary"]["scenario_required_2027"] > 0

agent = client.post(
    "/api/agent/run",
    json={
        "question": "Forecast Science teacher demand in Johor for 2027 with a 70% subject-option ratio"
    },
    headers=AUTH_HEADERS,
)
assert agent.status_code == 200, agent.text
# A straightforward question with a configured AI provider should be
# interpreted by the AI, not silently fall back to the local parser.
assert agent.json()["ai_usage"]["scenario_interpreted_by_ai"] is True

forecast_agent = client.post(
    "/api/agent/run",
    json={"question": "Forecast Science teacher demand in Johor for 2027"},
    headers=AUTH_HEADERS,
)
assert forecast_agent.status_code == 200, forecast_agent.text
assert forecast_agent.json()["scenario"]["policy_type"] == "baseline"

ambiguous_agent = client.post(
    "/api/agent/run",
    json={"question": "Kalau kita ubah macam biasa apa akan jadi?"},
    headers=AUTH_HEADERS,
)
# With an AI provider active the question is interpreted rather than rejected;
# with local-only mode the parser returns 400. Both are acceptable.
assert ambiguous_agent.status_code in (200, 400), ambiguous_agent.text

coteaching_agent = client.post(
    "/api/agent/run",
    json={
        "question": "Apply co-teaching to 50% of Science classes from Year 1 to 3 in Johor"
    },
    headers=AUTH_HEADERS,
)
assert coteaching_agent.status_code == 200, coteaching_agent.text
assert coteaching_agent.json()["scenario"]["kodtingkatantahun"] == ["D1", "D2", "D3"]

print("API smoke test passed")
print("Health:", health.json())
print("Simulation summary:", payload["summary"])
print("Co-teaching D1-D3 summary:", coteaching_payload["summary"])
print("Combined all-policy summary:", combined_all_payload["summary"])
print("Agent scenario:", agent.json()["scenario"])
