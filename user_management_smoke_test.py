"""user_management_smoke_test.py — exercises password generation, email templates
(mocked, no real network), last_login_at tracking, and the user-management
endpoints without starting a real web server."""

import email_utils

# --- Password generation ---
pw = email_utils.generate_temp_password()
assert len(pw) == 12, pw
assert any(c.isupper() for c in pw), pw
assert any(c.islower() for c in pw), pw
assert any(c.isdigit() for c in pw), pw
assert any(c in "!@#$%^&*" for c in pw), pw
assert not any(c in "0O1lI" for c in pw), pw

pw2 = email_utils.generate_temp_password()
assert pw != pw2, "two generated passwords should not be identical"

# --- Email templates (monkeypatch smtplib so no real network call happens) ---
import smtplib

sent_messages = []

class FakeSMTP:
    def __init__(self, host, port, timeout=10):
        sent_messages.append({"host": host, "port": port})
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def starttls(self):
        pass
    def login(self, username, password):
        sent_messages[-1]["login_username"] = username
    def send_message(self, message):
        sent_messages[-1]["subject"] = message["Subject"]
        sent_messages[-1]["to"] = message["To"]
        sent_messages[-1]["from"] = message["From"]
        sent_messages[-1]["body"] = message.get_content()

_real_smtp = smtplib.SMTP
smtplib.SMTP = FakeSMTP

try:
    ok = email_utils.send_temp_password_email("someone@example.com", "someone", "Ab3$xyz9Qw2!", lang="bm")
    assert ok is True
    assert sent_messages[-1]["to"] == "someone@example.com"
    assert sent_messages[-1]["subject"] == "Notifikasi Penetapan Semula Kata Laluan"
    assert "Ab3$xyz9Qw2!" in sent_messages[-1]["body"]
    assert "Assalamualaikum" in sent_messages[-1]["body"]

    ok_en = email_utils.send_temp_password_email("someone@example.com", "someone", "Ab3$xyz9Qw2!", lang="en")
    assert ok_en is True
    assert sent_messages[-1]["subject"] == "Password Reset Notification"
    assert "Dear User" in sent_messages[-1]["body"]
    assert "Ab3$xyz9Qw2!" in sent_messages[-1]["body"]
finally:
    smtplib.SMTP = _real_smtp

# --- last_login_at gets recorded on successful login ---
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# Idempotency: this script creates 'um_test_user1'/'um_test_user2' unconditionally
# below. Remove any leftover rows from a prior run so re-running this script
# never fails on a stale "username already exists" from its own earlier output.
import duckdb as _duckdb_cleanup
from config import get_database_path as _get_db_path_cleanup

_cleanup_connection = _duckdb_cleanup.connect(str(_get_db_path_cleanup()), read_only=False)
_cleanup_connection.execute("DELETE FROM users WHERE username IN ('um_test_user1', 'um_test_user2')")
_cleanup_connection.commit()
_cleanup_connection.close()

before = client.post(
    "/api/auth/login", json={"username": "superadmin", "password": "SuperAdmin123!"}
)
assert before.status_code == 200, before.text

import duckdb
from config import get_database_path

con = duckdb.connect(str(get_database_path()), read_only=True)
last_login = con.execute(
    "SELECT last_login_at FROM users WHERE username = 'superadmin'"
).fetchone()[0]
con.close()
assert last_login is not None, "last_login_at should be set after a successful login"

# --- Create-user: no password in request, temp password generated + "emailed" ---
import main as main_module

_captured_emails = []

def _fake_send_temp_password_email(to_email, username, temp_password, lang="bm"):
    _captured_emails.append({"to": to_email, "username": username, "password": temp_password, "lang": lang})
    return True

main_module.email_utils.send_temp_password_email = _fake_send_temp_password_email

login2 = client.post("/api/auth/login", json={"username": "superadmin", "password": "SuperAdmin123!"})
admin_token = login2.json()["token"]

created = client.post(
    "/api/admin/create-user",
    json={"username": "um_test_user1", "email": "um_test_user1@example.com", "role_name": "user", "lang": "en"},
    headers={"X-Auth-Token": admin_token},
)
assert created.status_code == 200, created.text
created_body = created.json()
assert "password" not in created_body, created_body
assert created_body["email_sent"] is True
assert created_body["is_first_login"] is True
assert len(_captured_emails) == 1
assert _captured_emails[0]["to"] == "um_test_user1@example.com"
assert _captured_emails[0]["lang"] == "en"
temp_password_for_user1 = _captured_emails[0]["password"]
assert len(temp_password_for_user1) == 12

# The generated password actually works to log in as the new user
new_login = client.post(
    "/api/auth/login", json={"username": "um_test_user1", "password": temp_password_for_user1}
)
assert new_login.status_code == 200, new_login.text
assert new_login.json()["is_first_login"] is True

# --- List users ---
users_resp = client.get("/api/admin/users", headers={"X-Auth-Token": admin_token})
assert users_resp.status_code == 200, users_resp.text
users_list = users_resp.json()["users"]
usernames = [u["username"] for u in users_list]
assert "um_test_user1" in usernames
sample_user = next(u for u in users_list if u["username"] == "um_test_user1")
assert sample_user["is_active"] is True
assert sample_user["email"] == "um_test_user1@example.com"
assert sample_user["created_at"] is not None
user1_id = sample_user["id"]

# non-superadmin cannot list users
user_login = client.post("/api/auth/login", json={"username": "um_test_user1", "password": temp_password_for_user1})
user_token = user_login.json()["token"]
forbidden = client.get("/api/admin/users", headers={"X-Auth-Token": user_token})
assert forbidden.status_code == 403, forbidden.text

# --- Reset password ---
_captured_emails.clear()
reset_resp = client.post(f"/api/admin/users/{user1_id}/reset-password", headers={"X-Auth-Token": admin_token})
assert reset_resp.status_code == 200, reset_resp.text
reset_body = reset_resp.json()
assert "password" not in reset_body
assert reset_body["email_sent"] is True
assert len(_captured_emails) == 1
new_temp_password = _captured_emails[0]["password"]

# old password no longer works, new one does and forces first-login again
old_login_fails = client.post("/api/auth/login", json={"username": "um_test_user1", "password": temp_password_for_user1})
assert old_login_fails.status_code == 401, old_login_fails.text
new_login_works = client.post("/api/auth/login", json={"username": "um_test_user1", "password": new_temp_password})
assert new_login_works.status_code == 200, new_login_works.text
assert new_login_works.json()["is_first_login"] is True

# --- Deactivate ---
deactivate_resp = client.post(f"/api/admin/users/{user1_id}/deactivate", headers={"X-Auth-Token": admin_token})
assert deactivate_resp.status_code == 200, deactivate_resp.text
assert deactivate_resp.json()["is_active"] is False

deactivated_login = client.post("/api/auth/login", json={"username": "um_test_user1", "password": new_temp_password})
assert deactivated_login.status_code == 403, deactivated_login.text

# --- Safety guards ---
superadmin_id = next(u["id"] for u in users_list if u["username"] == "superadmin")
self_deactivate = client.post(f"/api/admin/users/{superadmin_id}/deactivate", headers={"X-Auth-Token": admin_token})
assert self_deactivate.status_code == 400, self_deactivate.text

# --- Change password ---
cp_user = client.post(
    "/api/admin/create-user",
    json={"username": "um_test_user2", "email": "um_test_user2@example.com", "role_name": "user", "lang": "en"},
    headers={"X-Auth-Token": admin_token},
)
assert cp_user.status_code == 200, cp_user.text
cp_temp_password = _captured_emails[-1]["password"]

cp_login = client.post("/api/auth/login", json={"username": "um_test_user2", "password": cp_temp_password})
assert cp_login.status_code == 200, cp_login.text
cp_token = cp_login.json()["token"]

wrong_current = client.post(
    "/api/auth/change-password",
    json={"current_password": "definitely-wrong", "new_password": "NewPassw0rd!"},
    headers={"X-Auth-Token": cp_token},
)
assert wrong_current.status_code == 401, wrong_current.text

correct_change = client.post(
    "/api/auth/change-password",
    json={"current_password": cp_temp_password, "new_password": "NewPassw0rd!"},
    headers={"X-Auth-Token": cp_token},
)
assert correct_change.status_code == 200, correct_change.text
assert correct_change.json() == {"ok": True}

old_pw_now_fails = client.post("/api/auth/login", json={"username": "um_test_user2", "password": cp_temp_password})
assert old_pw_now_fails.status_code == 401, old_pw_now_fails.text

new_pw_login = client.post("/api/auth/login", json={"username": "um_test_user2", "password": "NewPassw0rd!"})
assert new_pw_login.status_code == 200, new_pw_login.text
assert new_pw_login.json()["is_first_login"] is False

# --- is_first_login is enforced server-side (Finding 3) ---
_cleanup_connection = _duckdb_cleanup.connect(str(_get_db_path_cleanup()), read_only=False)
_cleanup_connection.execute("DELETE FROM users WHERE username = 'um_test_user3'")
_cleanup_connection.commit()
_cleanup_connection.close()

_captured_emails.clear()
fl_user = client.post(
    "/api/admin/create-user",
    json={"username": "um_test_user3", "email": "um_test_user3@example.com", "role_name": "user", "lang": "en"},
    headers={"X-Auth-Token": admin_token},
)
assert fl_user.status_code == 200, fl_user.text
fl_temp_password = _captured_emails[-1]["password"]

fl_login = client.post("/api/auth/login", json={"username": "um_test_user3", "password": fl_temp_password})
assert fl_login.status_code == 200, fl_login.text
assert fl_login.json()["is_first_login"] is True
fl_token = fl_login.json()["token"]

SIMULATE_PAYLOAD = {
    "target_year": 2027,
    "subject": "SAINS",
    "negeri": "JOHOR",
    "policy_type": "option_ratio",
    "option_ratio": 0.7,
}

blocked = client.post("/api/simulate", json=SIMULATE_PAYLOAD, headers={"X-Auth-Token": fl_token})
assert blocked.status_code == 403, blocked.text
assert blocked.json()["detail"] == "Password change required before continuing", blocked.text

fl_change = client.post(
    "/api/auth/change-password",
    json={"current_password": fl_temp_password, "new_password": "NewPassw0rd!"},
    headers={"X-Auth-Token": fl_token},
)
assert fl_change.status_code == 200, fl_change.text

allowed = client.post("/api/simulate", json=SIMULATE_PAYLOAD, headers={"X-Auth-Token": fl_token})
assert allowed.status_code == 200, allowed.text

# Cleanup test user created for this block.
_cleanup_connection = _duckdb_cleanup.connect(str(_get_db_path_cleanup()), read_only=False)
_cleanup_connection.execute("DELETE FROM users WHERE username = 'um_test_user3'")
_cleanup_connection.commit()
_cleanup_connection.close()

print("user_management smoke test passed")
