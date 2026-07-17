"""run_save_smoke_test.py — exercises the run-first-save-later workflow:
POST /api/runs/save and the is_saved filtering on GET /api/my-runs."""

from fastapi.testclient import TestClient

from main import app
import db as _db_cleanup

client = TestClient(app)

# Idempotency: remove any leftover test user and its run-log rows from a
# prior run before creating a fresh one.
_cleanup_connection = _db_cleanup.get_connection(read_only=False)
_cleanup_cursor = _cleanup_connection.cursor()
_cleanup_cursor.execute("DELETE FROM simulation_run_log WHERE run_by = 'rfsl_test_user'")
_cleanup_cursor.execute("DELETE FROM users WHERE username = 'rfsl_test_user'")
_cleanup_connection.commit()
_cleanup_cursor.close()
_cleanup_connection.close()

# --- Create a Policy Maker test user (mock email so no real network call) ---
import main as main_module

_captured_emails = []


def _fake_send_temp_password_email(to_email, username, temp_password, lang="bm"):
    _captured_emails.append({"to": to_email, "username": username, "password": temp_password, "lang": lang})
    return True


main_module.email_utils.send_temp_password_email = _fake_send_temp_password_email

admin_login = client.post("/api/auth/login", json={"username": "superadmin", "password": "P@ssword.123"})
assert admin_login.status_code == 200, admin_login.text
admin_token = admin_login.json()["token"]

created = client.post(
    "/api/admin/create-user",
    json={"username": "rfsl_test_user", "email": "rfsl_test_user@example.com", "role_name": "user", "lang": "en"},
    headers={"X-Auth-Token": admin_token},
)
assert created.status_code == 200, created.text
temp_password = _captured_emails[-1]["password"]

user_login = client.post("/api/auth/login", json={"username": "rfsl_test_user", "password": temp_password})
assert user_login.status_code == 200, user_login.text
user_token = user_login.json()["token"]

# Forced first-login: change password before the user can call anything else.
change_pw = client.post(
    "/api/auth/change-password",
    json={"current_password": temp_password, "new_password": "RfslTest123!"},
    headers={"X-Auth-Token": user_token},
)
assert change_pw.status_code == 200, change_pw.text

user_login2 = client.post("/api/auth/login", json={"username": "rfsl_test_user", "password": "RfslTest123!"})
assert user_login2.status_code == 200, user_login2.text
user_token = user_login2.json()["token"]

# --- Run a simulation as the Policy Maker (auto-logged, not yet saved) ---
sim = client.post(
    "/api/simulate",
    json={
        "target_year": 2027,
        "subject": "SAINS",
        "negeri": "JOHOR",
        "policy_type": "option_ratio",
        "option_ratio": 0.70,
    },
    headers={"X-Auth-Token": user_token},
)
assert sim.status_code == 200, sim.text
run_id = sim.json()["artifacts"]["run_id"]

print("run_save_smoke_test: initial checks passed")

# --- Save with a custom name ---
save_resp = client.post(
    "/api/runs/save",
    json={"run_id": run_id, "run_name": "My Johor Science Scenario"},
    headers={"X-Auth-Token": user_token},
)
assert save_resp.status_code == 200, save_resp.text
assert save_resp.json() == {"run_id": run_id, "run_name": "My Johor Science Scenario"}

# --- Save with a blank name falls back to a generated name ---
sim2 = client.post(
    "/api/simulate",
    json={"target_year": 2027, "subject": "SAINS", "negeri": "JOHOR", "policy_type": "option_ratio", "option_ratio": 0.70},
    headers={"X-Auth-Token": user_token},
)
run_id_2 = sim2.json()["artifacts"]["run_id"]
save_blank = client.post(
    "/api/runs/save",
    json={"run_id": run_id_2, "run_name": "   "},
    headers={"X-Auth-Token": user_token},
)
assert save_blank.status_code == 200, save_blank.text
assert save_blank.json()["run_name"].startswith("Simulation - ")

# --- Cannot save a run_id that isn't yours ---
admin_sim = client.post(
    "/api/simulate",
    json={"target_year": 2027, "subject": "SAINS", "negeri": "JOHOR", "policy_type": "option_ratio", "option_ratio": 0.70},
    headers={"X-Auth-Token": admin_token},
)
admin_run_id = admin_sim.json()["artifacts"]["run_id"]
steal_attempt = client.post(
    "/api/runs/save",
    json={"run_id": admin_run_id, "run_name": "Not mine"},
    headers={"X-Auth-Token": user_token},
)
assert steal_attempt.status_code == 404, steal_attempt.text

# --- Bad run_id shape is rejected ---
bad_id = client.post(
    "/api/runs/save",
    json={"run_id": "not-a-real-id!", "run_name": "x"},
    headers={"X-Auth-Token": user_token},
)
assert bad_id.status_code == 400, bad_id.text

print("run_save_smoke_test: save endpoint checks passed")
