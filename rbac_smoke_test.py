"""rbac_smoke_test.py — exercises session/role enforcement without starting a web server."""

from fastapi.testclient import TestClient

import db
from main import app

client = TestClient(app)

# Idempotency: this script creates 'rbac_test_admin' unconditionally below.
# Remove any leftover row from a prior run so re-running this script never
# fails on a stale "username already exists" from its own earlier output.
_cleanup_connection = db.get_connection(read_only=False)
_cleanup_cursor = _cleanup_connection.cursor()
_cleanup_cursor.execute("DELETE FROM users WHERE username = 'rbac_test_admin'")
_cleanup_connection.commit()
_cleanup_cursor.close()
_cleanup_connection.close()

# --- No token at all ---
no_token = client.post("/api/admin/create-user", json={
    "username": "shouldfail1", "email": "a@a.com", "password": "password123", "role_name": "user",
})
assert no_token.status_code == 401, no_token.text

# --- Login as superadmin, get a real token ---
login = client.post("/api/auth/login", json={"username": "superadmin", "password": "SuperAdmin123!"})
assert login.status_code == 200, login.text
token = login.json()["token"]
assert login.json()["role_name"] == "superadmin"

# --- Superadmin can create a user ---
created = client.post(
    "/api/admin/create-user",
    json={"username": "rbac_test_admin", "email": "rbac@test.com", "password": "password123", "role_name": "admin"},
    headers={"X-Auth-Token": token},
)
assert created.status_code == 200, created.text

# --- Logout invalidates the token ---
logout = client.post("/api/auth/logout", headers={"X-Auth-Token": token})
assert logout.status_code == 200, logout.text

after_logout = client.post(
    "/api/admin/create-user",
    json={"username": "shouldfail2", "email": "b@b.com", "password": "password123", "role_name": "user"},
    headers={"X-Auth-Token": token},
)
assert after_logout.status_code == 401, after_logout.text

print("RBAC session smoke test passed")

# --- Re-login as superadmin (previous token was logged out) ---
login2 = client.post("/api/auth/login", json={"username": "superadmin", "password": "SuperAdmin123!"})
admin_token = login2.json()["token"]

# --- forecast/2027 requires admin or superadmin, not a bare policy maker ---
forecast_public = client.post("/api/forecast/2027", json={"subject": "SAINS", "negeri": "JOHOR"})
assert forecast_public.status_code == 401, forecast_public.text

forecast_ok = client.post(
    "/api/forecast/2027",
    json={"subject": "SAINS", "negeri": "JOHOR"},
    headers={"X-Auth-Token": admin_token},
)
assert forecast_ok.status_code == 200, forecast_ok.text

# --- detail.csv requires admin/superadmin ---
detail_no_token = client.get("/api/runs/RUN_TEST/detail.csv")
assert detail_no_token.status_code == 401, detail_no_token.text

# --- audit log requires superadmin (or flagged admin) ---
audit_no_token = client.get("/api/audit-log")
assert audit_no_token.status_code == 401, audit_no_token.text

audit_as_superadmin = client.get("/api/audit-log", headers={"X-Auth-Token": admin_token})
assert audit_as_superadmin.status_code == 200, audit_as_superadmin.text
entries = audit_as_superadmin.json()["entries"]
assert any(e["action"] == "login_success" for e in entries)

print("RBAC endpoint-gating smoke test passed")

# --- Run a simulation as a logged-in user, then check the summary CSV exists ---
policy_maker_login = client.post("/api/auth/login", json={"username": "superadmin", "password": "SuperAdmin123!"})
pm_token = policy_maker_login.json()["token"]

sim = client.post(
    "/api/simulate",
    json={"target_year": 2027, "subject": "SAINS", "negeri": "JOHOR", "policy_type": "option_ratio", "option_ratio": 0.7},
    headers={"X-Auth-Token": pm_token},
)
assert sim.status_code == 200, sim.text
run_id = sim.json()["artifacts"]["run_id"]
assert sim.json()["artifacts"]["summary_csv"], sim.json()["artifacts"]

summary_dl = client.get(f"/api/runs/{run_id}/summary.csv", headers={"X-Auth-Token": pm_token})
assert summary_dl.status_code == 200, summary_dl.text
assert "baseline_required_2027" in summary_dl.text

# --- audit log now shows the simulation run ---
audit_after_run = client.get("/api/audit-log", headers={"X-Auth-Token": pm_token})
assert audit_after_run.status_code == 200
assert any("simulation_run" in e["action"] for e in audit_after_run.json()["entries"])

print("RBAC summary-report and run-log smoke test passed")
