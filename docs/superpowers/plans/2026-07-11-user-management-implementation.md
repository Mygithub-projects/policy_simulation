# User Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the superadmin full user lifecycle management (create with auto-generated + emailed password, list, deactivate, reset password) and force every user to change a temporary password on first login.

**Architecture:** A new `email_utils.py` module generates temp passwords and sends the BM/EN notification email over SMTP. `main.py` gains four endpoints (list/reset-password/deactivate/change-password) reusing the existing `require_role`/`write_audit_log` helpers from the RBAC feature. The frontend restructures the Admin page into two collapsible sections and adds a mandatory post-login "Set New Password" screen.

**Tech Stack:** FastAPI, DuckDB, Python stdlib `smtplib`/`email.message` (no new dependency), vanilla JS frontend, this repo's plain assert-based smoke-test scripts (no pytest).

## Global Constraints

- No schema changes — `users.email`, `is_active`, `is_first_login`, `password_changed_at` already exist.
- Password field is removed entirely from the create-user form/request — passwords are always server-generated and emailed, never admin-typed, never returned in any API response.
- Deactivation is soft (`is_active = false`), never a hard delete of the row.
- Deactivation is blocked (400) for the caller's own account and for the last remaining active superadmin.
- The BM and EN email templates (subject + body) must match the text in `docs/superpowers/specs/2026-07-11-user-management-design.md` verbatim.
- Never print, log, or return the generated temporary password anywhere except the email itself.
- Follow this repo's existing test style: plain script with `assert` statements using `fastapi.testclient.TestClient`, run via `python <file>.py` — do not introduce pytest.
- SMTP credentials come from `.env` (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_ADDRESS`), already populated in this project's `.env`. Automated tests must NOT send real email — monkeypatch `send_temp_password_email` in test scripts instead.

---

## File Structure

| File | Change |
|---|---|
| `email_utils.py` (new) | `generate_temp_password()`, `send_temp_password_email()`, the BM/EN templates. |
| `config.py` | Add `get_smtp_host/port/username/password/from_address()` getters. |
| `api_models.py` | `CreateUserInput` drops `password`, adds `lang`; new `ChangePasswordInput`. |
| `main.py` | `login()` now updates `last_login_at`; `create_user()` generates+emails password instead of accepting one; new `GET /api/admin/users`, `POST /api/admin/users/{id}/reset-password`, `POST /api/admin/users/{id}/deactivate`, `POST /api/auth/change-password`. |
| `user_management_smoke_test.py` (new) | Script-style smoke test covering all of the above, mirrors `rbac_smoke_test.py`. |
| `frontend/index.html` | Admin page restructured into two `<details>` sections (Create User, Manage Users); new "Set New Password" screen markup. |
| `frontend/app.js` | `handleCreateUser` drops the password field; new `loadUserList`, `buildUserRow`, `confirmResetPassword`, `confirmDeactivateUser`, `showChangePasswordScreen`, `hideChangePasswordScreen`, `runChangePassword`; `runLogin`/`initAuth` gate on `is_first_login`. |
| `frontend/styles.css` | New `.admin-section` (details/summary), `.status-pill`, `.icon-btn`, `.user-actions` styles. |
| `frontend/lang.js` | New i18n keys for the manage-users table, action confirmations, and the change-password screen. |

---

### Task 1: SMTP config, email module, and `last_login_at` tracking

**Files:**
- Create: `email_utils.py`
- Modify: `config.py`
- Modify: `main.py:207-247` (the `login()` function)
- Create: `user_management_smoke_test.py`

**Interfaces:**
- Produces: `config.get_smtp_host() -> str`, `get_smtp_port() -> int`, `get_smtp_username() -> str`, `get_smtp_password() -> str`, `get_smtp_from_address() -> str`.
- Produces: `email_utils.generate_temp_password(length: int = 12) -> str`.
- Produces: `email_utils.send_temp_password_email(to_email: str, username: str, temp_password: str, lang: str = "bm") -> bool` — returns `True`/`False`, never raises.
- Later tasks import `email_utils` as a module (`import email_utils`) so test scripts can monkeypatch `email_utils.send_temp_password_email` — do not do `from email_utils import send_temp_password_email` anywhere.

- [ ] **Step 1: Write the failing test**

```python
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

print("email_utils smoke test passed")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python user_management_smoke_test.py`
Expected: `ModuleNotFoundError: No module named 'email_utils'`

- [ ] **Step 3: Add SMTP getters to `config.py`**

Add at the end of `config.py`:

```python
def get_smtp_host() -> str:
    return os.getenv("SMTP_HOST", "").strip()


def get_smtp_port() -> int:
    return int(os.getenv("SMTP_PORT", "587").strip() or "587")


def get_smtp_username() -> str:
    return os.getenv("SMTP_USERNAME", "").strip()


def get_smtp_password() -> str:
    return os.getenv("SMTP_PASSWORD", "").strip()


def get_smtp_from_address() -> str:
    return os.getenv("SMTP_FROM_ADDRESS", "").strip()
```

- [ ] **Step 4: Create `email_utils.py`**

```python
"""Temporary-password generation and email notification for user accounts."""

from __future__ import annotations

import secrets
import smtplib
import string
from email.message import EmailMessage

from config import (
    get_smtp_from_address,
    get_smtp_host,
    get_smtp_password,
    get_smtp_port,
    get_smtp_username,
)

_AMBIGUOUS = set("0O1lI")
_UPPER = [c for c in string.ascii_uppercase if c not in _AMBIGUOUS]
_LOWER = [c for c in string.ascii_lowercase if c not in _AMBIGUOUS]
_DIGITS = [c for c in string.digits if c not in _AMBIGUOUS]
_SYMBOLS = list("!@#$%^&*")
_ALL_CHARS = _UPPER + _LOWER + _DIGITS + _SYMBOLS


def generate_temp_password(length: int = 12) -> str:
    """Generates a random temporary password guaranteed to contain at least
    one uppercase letter, one lowercase letter, one digit, and one symbol,
    excluding visually ambiguous characters (0/O/1/l/I)."""
    if length < 4:
        raise ValueError("length must be at least 4 to include all character classes")

    required = [
        secrets.choice(_UPPER),
        secrets.choice(_LOWER),
        secrets.choice(_DIGITS),
        secrets.choice(_SYMBOLS),
    ]
    remaining = [secrets.choice(_ALL_CHARS) for _ in range(length - len(required))]
    password_chars = required + remaining
    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)


_BM_SUBJECT = "Notifikasi Penetapan Semula Kata Laluan"
_BM_BODY = """Assalamualaikum dan Salam Sejahtera,

Tuan/Puan,

Dimaklumkan bahawa pihak pentadbir telah menetapkan semula kata laluan akaun tuan/puan susulan permohonan berkaitan kata laluan yang terlupa.

Kata laluan sementara/default adalah seperti berikut:

Kata laluan sementara: {temp_password}

Tuan/puan dimohon untuk log masuk menggunakan kata laluan tersebut dan menukarnya kepada kata laluan baharu dengan segera bagi menjaga keselamatan akaun.

Sekiranya tuan/puan masih menghadapi masalah untuk log masuk, sila hubungi pihak pentadbir sistem untuk bantuan selanjutnya.

Sekian, terima kasih.

Yang menjalankan amanah,
Pentadbir Sistem
Sistem Simulasi Dasar Tenaga Kerja Pendidikan
"""

_EN_SUBJECT = "Password Reset Notification"
_EN_BODY = """Dear User,

Please be informed that the administrator has reset your account password following your request regarding a forgotten password.

Your temporary/default password is as follows:

Temporary Password: {temp_password}

Please log in using the temporary password and change it immediately to ensure the security of your account.

Should you continue to experience any issues accessing your account, please contact the system administrator for further assistance.

Thank you.

Best regards,
System Administrator
Education Workforce Policy Simulation System
"""


def send_temp_password_email(to_email: str, username: str, temp_password: str, lang: str = "bm") -> bool:
    """Sends the temporary-password notification email. Returns True on success,
    False on any failure (never raises — a mail-server outage must not break
    user creation or password reset)."""
    subject = _BM_SUBJECT if lang == "bm" else _EN_SUBJECT
    body = (_BM_BODY if lang == "bm" else _EN_BODY).format(temp_password=temp_password)

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = get_smtp_from_address()
    message["To"] = to_email
    message.set_content(body)

    try:
        with smtplib.SMTP(get_smtp_host(), get_smtp_port(), timeout=10) as server:
            server.starttls()
            server.login(get_smtp_username(), get_smtp_password())
            server.send_message(message)
        return True
    except Exception:
        return False
```

- [ ] **Step 5: Run test to verify the password/email parts pass**

Run: `python user_management_smoke_test.py`
Expected: passes through the email section (the file has no `last_login_at`/endpoint assertions yet — those are added in later steps of this task and Tasks 2-4). No output yet since `print("email_utils smoke test passed")` is the last line so far.

- [ ] **Step 6: Make `login()` record `last_login_at`**

In `main.py`, modify the `login()` function (currently lines 207-247) — add a write-connection update right after the successful-login checks, before creating the session token:

```python
@app.post("/api/auth/login")
def login(payload: LoginInput) -> dict[str, Any]:
    connection = duckdb.connect(str(get_database_path()), read_only=True)
    try:
        row = connection.execute(
            "SELECT username, password_hash, role_name, is_active, is_first_login, "
            "COALESCE(can_view_audit_log, FALSE) "
            "FROM users WHERE username = ? LIMIT 1",
            [payload.username],
        ).fetchone()
    finally:
        connection.close()

    if not row:
        write_audit_log(payload.username, "unknown", "login_failed", "no such user")
        raise HTTPException(status_code=401, detail="Invalid username or password")

    username, password_hash, role_name, is_active, is_first_login, can_view_audit_log = row
    if not is_active:
        write_audit_log(username, role_name, "login_failed", "inactive account")
        raise HTTPException(status_code=403, detail="User account is inactive")
    if not verify_password(payload.password, password_hash):
        write_audit_log(username, role_name, "login_failed", "bad password")
        raise HTTPException(status_code=401, detail="Invalid username or password")

    write_connection = duckdb.connect(str(get_database_path()), read_only=False)
    try:
        write_connection.execute(
            "UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE username = ?",
            [username],
        )
        write_connection.commit()
    finally:
        write_connection.close()

    token = secrets.token_hex(16)
    SESSIONS[token] = {
        "username": username,
        "role_name": role_name,
        "can_view_audit_log": bool(can_view_audit_log),
    }
    write_audit_log(username, role_name, "login_success", "")

    return {
        "username": username,
        "role_name": role_name,
        "is_first_login": bool(is_first_login),
        "can_view_audit_log": bool(can_view_audit_log),
        "token": token,
    }
```

- [ ] **Step 7: Append a test for `last_login_at` to `user_management_smoke_test.py`**

Add before the final `print(...)` line:

```python
# --- last_login_at gets recorded on successful login ---
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
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
```

Move the final `print("email_utils smoke test passed")` line to the very end of the
file (after this new block), and rename it to
`print("user_management smoke test passed (Task 1)")`.

- [ ] **Step 8: Run test to verify it passes**

Run: `python user_management_smoke_test.py`
Expected: `user_management smoke test passed (Task 1)` printed, no `AssertionError`.

- [ ] **Step 9: Run the existing smoke tests to check nothing else broke**

Run: `python smoke_test.py` then `python api_smoke_test.py` then `python rbac_smoke_test.py`
Expected: all three still pass unmodified.

- [ ] **Step 10: Commit**

No git repo present in this project directory — skip.

---

### Task 2: Password-less user creation (auto-generate + email)

**Files:**
- Modify: `api_models.py`
- Modify: `main.py:257-317` (the `create_user()` function)
- Modify: `user_management_smoke_test.py`

**Interfaces:**
- Consumes: `email_utils.generate_temp_password()`, `email_utils.send_temp_password_email()` (Task 1) — imported as `import email_utils` in `main.py`, called as `email_utils.generate_temp_password(...)` / `email_utils.send_temp_password_email(...)` so tests can monkeypatch `email_utils.send_temp_password_email` directly.
- Produces: `POST /api/admin/create-user` response shape `{id, username, email, role_name, is_first_login: true, email_sent: bool, message}` — no `password` field ever, in the request or the response.
- Later tasks (3) reuse this same "generate → hash → email → email_sent in response" pattern for reset-password.

- [ ] **Step 1: Write the failing test (append to `user_management_smoke_test.py`, before the final print)**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python user_management_smoke_test.py`
Expected: `AssertionError` on `"password" not in created_body` (the current endpoint still requires and doesn't return based on a request-supplied password — actually it will fail earlier, at the `created.status_code == 200` assertion, because the request body no longer includes a `password` field that `CreateUserInput` still requires).

- [ ] **Step 3: Update `CreateUserInput` in `api_models.py`**

```python
class CreateUserInput(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=120)
    role_name: Literal["superadmin", "admin", "user"] = "user"
    can_view_audit_log: bool = False
    lang: Literal["bm", "en"] = "bm"
```

- [ ] **Step 4: Add `import email_utils` and rewrite `create_user()` in `main.py`**

Add near the top of `main.py`, alongside the existing imports:

```python
import email_utils
```

Replace the body of `create_user()` (currently lines 257-317):

```python
@app.post("/api/admin/create-user")
def create_user(
    payload: CreateUserInput,
    session: dict[str, Any] = Depends(require_role("superadmin")),
) -> dict[str, Any]:
    """Create a new user account. Superadmin only. Password is always
    auto-generated and emailed — never admin-typed, never returned here."""
    connection = duckdb.connect(str(get_database_path()), read_only=True)
    try:
        existing = connection.execute(
            "SELECT id FROM users WHERE username = ? LIMIT 1",
            [payload.username],
        ).fetchone()
    finally:
        connection.close()

    if existing:
        raise HTTPException(status_code=400, detail=f"Username '{payload.username}' already exists")

    temp_password = email_utils.generate_temp_password()
    iterations = 260000
    salt = secrets.token_hex(16)
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        temp_password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    password_hash = f"pbkdf2_sha256${iterations}${salt}${hash_bytes.hex()}"

    connection = duckdb.connect(str(get_database_path()), read_only=False)
    try:
        max_id = connection.execute("SELECT COALESCE(MAX(id), 0) FROM users").fetchone()[0]
        new_id = max_id + 1

        connection.execute(
            "INSERT INTO users (id, username, email, password_hash, role_name, is_active, is_first_login, can_view_audit_log) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [new_id, payload.username, payload.email, password_hash, payload.role_name, True, True, payload.can_view_audit_log],
        )
        connection.commit()
    except Exception as error:
        connection.close()
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(error)}")
    finally:
        connection.close()

    email_sent = email_utils.send_temp_password_email(
        payload.email, payload.username, temp_password, payload.lang
    )

    write_audit_log(
        session["username"], session["role_name"], "user_created",
        f"created '{payload.username}' with role '{payload.role_name}'",
    )

    return {
        "id": new_id,
        "username": payload.username,
        "email": payload.email,
        "role_name": payload.role_name,
        "is_first_login": True,
        "email_sent": email_sent,
        "message": f"User '{payload.username}' created. Temporary password emailed to {payload.email}.",
    }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python user_management_smoke_test.py`
Expected: prints `user_management smoke test passed (Task 1)` (from the earlier block) with no `AssertionError` anywhere above it. (The print statement gets renamed again in Task 4 — leave it as-is for now.)

- [ ] **Step 6: Run existing smoke tests**

Run: `python smoke_test.py` then `python api_smoke_test.py` then `python rbac_smoke_test.py`

`rbac_smoke_test.py` calls `/api/admin/create-user` with a `password` field in its
request body (from the RBAC feature) — since `CreateUserInput` no longer has that
field, Pydantic ignores unknown extra fields by default, so this should still pass
unmodified. Confirm it does; if `rbac_smoke_test.py`'s create-user call instead
fails, open it, remove the `"password": "password123"` line from its request body,
and re-run.

- [ ] **Step 7: Commit**

No git repo present — skip.

---

### Task 3: List users, reset password, deactivate — with safety guards

**Files:**
- Modify: `main.py`
- Modify: `user_management_smoke_test.py`

**Interfaces:**
- Consumes: `email_utils.generate_temp_password()` / `send_temp_password_email()` (Task 1), `require_role` / `write_audit_log` (existing, from RBAC).
- Produces: `GET /api/admin/users` → `{"users": [{id, username, email, role_name, is_active, created_at, last_login_at}]}`.
- Produces: `POST /api/admin/users/{user_id}/reset-password` → `{id, email_sent: bool, message}`.
- Produces: `POST /api/admin/users/{user_id}/deactivate` → `{id, is_active: false, message}`, or `400` if self or last active superadmin.
- Later task (5, frontend) calls exactly these three endpoints and expects exactly these response shapes.

- [ ] **Step 1: Write the failing test (append to `user_management_smoke_test.py`, before the final print)**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python user_management_smoke_test.py`
Expected: `404` (Not Found) or connection-style error on the `client.get("/api/admin/users", ...)` call — the endpoint doesn't exist yet.

- [ ] **Step 3: Add the three endpoints to `main.py`**

Add these after `create_user()` and before `@app.get("/api/health")`:

```python
@app.get("/api/admin/users")
def list_users(
    session: dict[str, Any] = Depends(require_role("superadmin")),
) -> dict[str, Any]:
    connection = duckdb.connect(str(get_database_path()), read_only=True)
    try:
        rows = connection.execute(
            "SELECT id, username, email, role_name, is_active, created_at, last_login_at "
            "FROM users ORDER BY id"
        ).fetchall()
    finally:
        connection.close()

    return {
        "users": [
            {
                "id": row[0],
                "username": row[1],
                "email": row[2],
                "role_name": row[3],
                "is_active": bool(row[4]),
                "created_at": str(row[5]) if row[5] is not None else None,
                "last_login_at": str(row[6]) if row[6] is not None else None,
            }
            for row in rows
        ]
    }


@app.post("/api/admin/users/{user_id}/reset-password")
def reset_password(
    user_id: int,
    session: dict[str, Any] = Depends(require_role("superadmin")),
) -> dict[str, Any]:
    connection = duckdb.connect(str(get_database_path()), read_only=True)
    try:
        row = connection.execute(
            "SELECT username, email FROM users WHERE id = ? LIMIT 1", [user_id]
        ).fetchone()
    finally:
        connection.close()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    username, email = row

    temp_password = email_utils.generate_temp_password()
    iterations = 260000
    salt = secrets.token_hex(16)
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256", temp_password.encode("utf-8"), salt.encode("utf-8"), iterations
    )
    password_hash = f"pbkdf2_sha256${iterations}${salt}${hash_bytes.hex()}"

    write_connection = duckdb.connect(str(get_database_path()), read_only=False)
    try:
        write_connection.execute(
            "UPDATE users SET password_hash = ?, is_first_login = TRUE WHERE id = ?",
            [password_hash, user_id],
        )
        write_connection.commit()
    finally:
        write_connection.close()

    email_sent = email_utils.send_temp_password_email(email, username, temp_password, lang="bm")
    write_audit_log(
        session["username"], session["role_name"], "password_reset",
        f"reset password for '{username}'",
    )

    return {
        "id": user_id,
        "email_sent": email_sent,
        "message": f"Password reset for '{username}'. New temporary password emailed to {email}.",
    }


@app.post("/api/admin/users/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    session: dict[str, Any] = Depends(require_role("superadmin")),
) -> dict[str, Any]:
    connection = duckdb.connect(str(get_database_path()), read_only=True)
    try:
        row = connection.execute(
            "SELECT username, role_name, is_active FROM users WHERE id = ? LIMIT 1", [user_id]
        ).fetchone()
        active_superadmins = connection.execute(
            "SELECT COUNT(*) FROM users WHERE role_name = 'superadmin' AND is_active = TRUE"
        ).fetchone()[0]
    finally:
        connection.close()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    username, role_name, is_active = row

    if username == session["username"]:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")
    if role_name == "superadmin" and is_active and active_superadmins <= 1:
        raise HTTPException(status_code=400, detail="Cannot deactivate the last remaining active superadmin")

    write_connection = duckdb.connect(str(get_database_path()), read_only=False)
    try:
        write_connection.execute("UPDATE users SET is_active = FALSE WHERE id = ?", [user_id])
        write_connection.commit()
    finally:
        write_connection.close()

    write_audit_log(
        session["username"], session["role_name"], "user_deactivated",
        f"deactivated '{username}'",
    )
    return {"id": user_id, "is_active": False, "message": f"User '{username}' deactivated."}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python user_management_smoke_test.py`
Expected: no `AssertionError`; the existing print statement from Task 1 still fires at the end.

- [ ] **Step 5: Run existing smoke tests**

Run: `python smoke_test.py` then `python api_smoke_test.py` then `python rbac_smoke_test.py`
Expected: all three still pass unmodified.

- [ ] **Step 6: Commit**

No git repo present — skip.

---

### Task 4: Forced password change endpoint

**Files:**
- Modify: `api_models.py`
- Modify: `main.py`
- Modify: `user_management_smoke_test.py`

**Interfaces:**
- Consumes: `verify_password()` (existing, in `main.py`), `require_role` / `write_audit_log` (existing).
- Produces: `POST /api/auth/change-password` (any authenticated role) → `{"ok": true}` on success, `401` if `current_password` doesn't match.
- Later task (6, frontend) posts to exactly this endpoint with `{current_password, new_password}`.

- [ ] **Step 1: Write the failing test (append to `user_management_smoke_test.py`, before the final print)**

```python
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

print("user_management smoke test passed")
```

Delete the old `print("user_management smoke test passed (Task 1)")` line from Task 1's block — this new `print("user_management smoke test passed")` at the very end of the file replaces it as the single final success marker.

- [ ] **Step 2: Run test to verify it fails**

Run: `python user_management_smoke_test.py`
Expected: `404`/error on the `/api/auth/change-password` call — the endpoint doesn't exist yet.

- [ ] **Step 3: Add `ChangePasswordInput` to `api_models.py`**

```python
class ChangePasswordInput(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
```

- [ ] **Step 4: Add the endpoint to `main.py`**

Add after `deactivate_user()`:

```python
@app.post("/api/auth/change-password")
def change_password(
    payload: ChangePasswordInput,
    session: dict[str, Any] = Depends(require_role("superadmin", "admin", "user")),
) -> dict[str, Any]:
    connection = duckdb.connect(str(get_database_path()), read_only=True)
    try:
        row = connection.execute(
            "SELECT password_hash FROM users WHERE username = ? LIMIT 1",
            [session["username"]],
        ).fetchone()
    finally:
        connection.close()

    if not row or not verify_password(payload.current_password, row[0]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    iterations = 260000
    salt = secrets.token_hex(16)
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256", payload.new_password.encode("utf-8"), salt.encode("utf-8"), iterations
    )
    password_hash = f"pbkdf2_sha256${iterations}${salt}${hash_bytes.hex()}"

    write_connection = duckdb.connect(str(get_database_path()), read_only=False)
    try:
        write_connection.execute(
            "UPDATE users SET password_hash = ?, is_first_login = FALSE, password_changed_at = CURRENT_TIMESTAMP "
            "WHERE username = ?",
            [password_hash, session["username"]],
        )
        write_connection.commit()
    finally:
        write_connection.close()

    write_audit_log(session["username"], session["role_name"], "password_changed", "")
    return {"ok": True}
```

Update the import line at the top of `main.py` to include `ChangePasswordInput`:

```python
from api_models import (
    AgentQuestionInput,
    ChangePasswordInput,
    CreateUserInput,
    ForecastInput,
    LoginInput,
    ScenarioInput,
)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python user_management_smoke_test.py`
Expected: `user_management smoke test passed` printed, no `AssertionError`.

- [ ] **Step 6: Run existing smoke tests**

Run: `python smoke_test.py` then `python api_smoke_test.py` then `python rbac_smoke_test.py`
Expected: all three still pass unmodified.

- [ ] **Step 7: Commit**

No git repo present — skip.

---

### Task 5: Frontend — Admin page restructure (Create User + Manage Users table)

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/app.js`
- Modify: `frontend/styles.css`
- Modify: `frontend/lang.js`

**Interfaces:**
- Consumes: `GET /api/admin/users`, `POST /api/admin/users/{id}/reset-password`, `POST /api/admin/users/{id}/deactivate` (Task 3); `POST /api/admin/create-user` now without a `password` field (Task 2); `apiFetch(path, opts)` (existing, attaches `X-Auth-Token` automatically).
- Produces: no new interfaces consumed by other tasks in this plan — Task 6 touches different parts of the same files (the login/change-password flow), not this table.

- [ ] **Step 1: Replace the Admin page markup in `frontend/index.html`**

Find the current Admin page block (starts at the `<!-- ===================== ADMIN PAGE ===================== -->` comment) and replace the entire `<div class="admin-panel">...</div>` inside it with:

```html
        <div class="admin-panel">
          <details class="admin-section" open>
            <summary data-i18n="admin.section.create">Buat Pengguna</summary>
            <div class="result-card">
              <div class="result-card-body">
                <form id="createUserForm" onsubmit="handleCreateUser(event)" class="create-user-form">
                  <div class="form-group">
                    <label for="newUsername" data-i18n="admin.username">Nama Pengguna</label>
                    <input id="newUsername" class="form-control" type="text" required />
                  </div>
                  <div class="form-group">
                    <label for="newEmail" data-i18n="admin.email">Email</label>
                    <input id="newEmail" class="form-control" type="email" required />
                  </div>
                  <div class="form-group">
                    <label for="newRole" data-i18n="admin.role">Peranan</label>
                    <select id="newRole" class="form-control" onchange="onNewRoleChange()">
                      <option value="user" data-i18n="admin.role.user">Pengguna Biasa (Policy Maker)</option>
                      <option value="admin" data-i18n="admin.role.admin">Admin (Pegawai Perancangan)</option>
                      <option value="superadmin" data-i18n="admin.role.superadmin">Superadmin (Akses Penuh)</option>
                    </select>
                  </div>
                  <div class="form-group" id="canViewAuditGroup" style="display:none;">
                    <label>
                      <input type="checkbox" id="newCanViewAudit" />
                      <span data-i18n="admin.canviewaudit">Can View Audit Log</span>
                    </label>
                  </div>
                  <p class="hint" data-i18n="admin.password.note">Kata laluan sementara akan dijana secara automatik dan dihantar ke e-mel pengguna.</p>
                  <div id="createUserError" class="form-error"></div>
                  <button type="submit" class="btn btn-primary" data-i18n="admin.create.btn">Buat Pengguna</button>
                </form>
              </div>
            </div>
          </details>

          <details class="admin-section" style="margin-top: 20px;">
            <summary data-i18n="admin.section.manage">Urus Pengguna</summary>
            <div class="result-card">
              <div class="result-card-body">
                <div class="table-container">
                  <table class="rec-table">
                    <thead>
                      <tr>
                        <th data-i18n="admin.table.username">Nama Pengguna</th>
                        <th data-i18n="admin.table.email">Email</th>
                        <th data-i18n="admin.table.role">Peranan</th>
                        <th data-i18n="admin.table.status">Status</th>
                        <th data-i18n="admin.table.created">Dicipta</th>
                        <th data-i18n="admin.table.lastlogin">Log Masuk Terakhir</th>
                        <th data-i18n="admin.table.actions">Tindakan</th>
                      </tr>
                    </thead>
                    <tbody id="userListBody"></tbody>
                  </table>
                </div>
              </div>
            </div>
          </details>
        </div>
```

- [ ] **Step 2: Add `.admin-section` / `.status-pill` / `.icon-btn` / `.user-actions` CSS to `frontend/styles.css`**

Add near the existing `.admin-panel` rules:

```css
/* ===== ADMIN: collapsible sections ===== */
.admin-section {
  margin-bottom: 0;
}
.admin-section summary {
  cursor: pointer;
  padding: 12px 16px;
  background: var(--bg-card2);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  font-weight: 700;
  font-size: 13px;
  color: var(--text);
  list-style: none;
  user-select: none;
}
.admin-section summary::-webkit-details-marker { display: none; }
.admin-section summary::before {
  content: '▸';
  display: inline-block;
  margin-right: 8px;
  color: var(--gold-lt);
  transition: transform 0.15s;
}
.admin-section[open] summary::before { transform: rotate(90deg); }
.admin-section[open] summary {
  border-bottom-left-radius: 0;
  border-bottom-right-radius: 0;
}
.admin-section .result-card {
  border-top-left-radius: 0;
  border-top-right-radius: 0;
}

/* ===== ADMIN: status pill ===== */
.status-pill {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.status-pill.active { background: rgba(45,212,160,0.15); color: var(--success); }
.status-pill.inactive { background: rgba(255,255,255,0.08); color: var(--text-muted); }

/* ===== ADMIN: row action icons ===== */
.user-actions { white-space: nowrap; }
.icon-btn {
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 4px 8px;
  margin-right: 6px;
  font-size: 14px;
  cursor: pointer;
  color: var(--text-muted);
  transition: background 0.15s, color 0.15s;
}
.icon-btn:hover:not(:disabled) {
  background: rgba(255,255,255,0.06);
  color: var(--text);
}
.icon-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
```

- [ ] **Step 3: Add the new i18n keys to `frontend/lang.js`**

Add to the `bm` object (near the existing `admin.*` keys):

```javascript
    'admin.section.create': 'Buat Pengguna',
    'admin.section.manage': 'Urus Pengguna',
    'admin.password.note': 'Kata laluan sementara akan dijana secara automatik dan dihantar ke e-mel pengguna.',
    'admin.table.username': 'Nama Pengguna',
    'admin.table.email': 'Email',
    'admin.table.role': 'Peranan',
    'admin.table.status': 'Status',
    'admin.table.created': 'Dicipta',
    'admin.table.lastlogin': 'Log Masuk Terakhir',
    'admin.table.actions': 'Tindakan',
    'admin.status.active': 'Aktif',
    'admin.status.inactive': 'Tidak Aktif',
    'admin.action.reset': 'Tetapkan Semula Kata Laluan',
    'admin.action.deactivate': 'Nyahaktifkan Pengguna',
    'admin.confirm.reset': 'Hantar kata laluan sementara baharu ke %s?',
    'admin.confirm.deactivate': 'Nyahaktifkan pengguna "%s"? Mereka tidak akan dapat log masuk lagi.',
    'admin.email.failed': 'Tindakan berjaya, tetapi e-mel gagal dihantar. Sila cuba tetapkan semula kata laluan.',
```

Add the matching English keys to the `en` object:

```javascript
    'admin.section.create': 'Create User',
    'admin.section.manage': 'Manage Users',
    'admin.password.note': 'A temporary password will be generated automatically and emailed to the user.',
    'admin.table.username': 'Username',
    'admin.table.email': 'Email',
    'admin.table.role': 'Role',
    'admin.table.status': 'Status',
    'admin.table.created': 'Created',
    'admin.table.lastlogin': 'Last Login',
    'admin.table.actions': 'Actions',
    'admin.status.active': 'Active',
    'admin.status.inactive': 'Inactive',
    'admin.action.reset': 'Reset Password',
    'admin.action.deactivate': 'Deactivate User',
    'admin.confirm.reset': 'Send a new temporary password to %s?',
    'admin.confirm.deactivate': 'Deactivate user "%s"? They will no longer be able to log in.',
    'admin.email.failed': 'Action succeeded, but the email failed to send. Try the reset-password action again.',
```

- [ ] **Step 4: Remove the password field and its handling from `handleCreateUser` in `frontend/app.js`**

Replace the whole function:

```javascript
async function handleCreateUser(event) {
  event.preventDefault();
  const btn = event.target.querySelector('button[type="submit"]');
  const errorEl = document.getElementById('createUserError');
  errorEl.textContent = '';

  const username = document.getElementById('newUsername').value.trim();
  const email = document.getElementById('newEmail').value.trim();
  const role = document.getElementById('newRole').value;
  const canViewAudit = document.getElementById('newCanViewAudit').checked;

  if (!username || !email) {
    errorEl.textContent = 'Please fill all fields';
    return;
  }

  btn.disabled = true;
  btn.classList.add('loading');

  try {
    const data = await apiFetch('/api/admin/create-user', {
      method: 'POST',
      body: {
        username, email, role_name: role,
        can_view_audit_log: canViewAudit,
        lang: (typeof getLang === 'function' ? getLang() : 'bm'),
      },
    });
    showToast(data.message || t('admin.create.success'), 'success');
    if (!data.email_sent) {
      showToast(t('admin.email.failed'), 'warning');
    }
    document.getElementById('createUserForm').reset();
    loadUserList();
  } catch (err) {
    errorEl.textContent = err.message;
  } finally {
    btn.disabled = false;
    btn.classList.remove('loading');
  }
}
```

This also switches the create-user call from a raw `fetch()` to `apiFetch()` (consistent
with the rest of the app, and it already attaches `X-Auth-Token` automatically).

- [ ] **Step 5: Remove the now-unused `newPassword` input**

In `frontend/index.html`, delete this block (it was removed from the "Files" step
above already if you replaced the whole Admin page markup — verify it's gone):

```html
              <div class="form-group">
                <label for="newPassword" data-i18n="admin.password">Katalaluan Awal</label>
                <input id="newPassword" class="form-control" type="password" required />
              </div>
```

- [ ] **Step 6: Add `loadUserList`, `buildUserRow`, `confirmResetPassword`, `confirmDeactivateUser` to `frontend/app.js`**

Add after `handleCreateUser`:

```javascript
async function loadUserList() {
  const tbody = document.getElementById('userListBody');
  if (!tbody) return;
  tbody.innerHTML = '';
  try {
    const data = await apiFetch('/api/admin/users');
    (data.users || []).forEach(user => tbody.appendChild(buildUserRow(user)));
  } catch (err) {
    showToast('Failed to load user list: ' + err.message, 'error');
  }
}

function formatUserTimestamp(value) {
  if (!value) return '—';
  return value.slice(0, 19).replace('T', ' ');
}

function buildUserRow(user) {
  const tr = document.createElement('tr');
  const statusClass = user.is_active ? 'active' : 'inactive';
  const statusLabel = user.is_active ? t('admin.status.active') : t('admin.status.inactive');
  const isSelf = user.username === state.auth.username;
  const resetDisabled = !user.is_active;
  const deactivateDisabled = !user.is_active || isSelf;

  tr.innerHTML = `
    <td>${user.username}</td>
    <td>${user.email}</td>
    <td>${user.role_name}</td>
    <td><span class="status-pill ${statusClass}">${statusLabel}</span></td>
    <td>${formatUserTimestamp(user.created_at)}</td>
    <td>${formatUserTimestamp(user.last_login_at)}</td>
    <td class="user-actions">
      <button class="icon-btn" title="${t('admin.action.reset')}" ${resetDisabled ? 'disabled' : ''}>📝</button>
      <button class="icon-btn" title="${t('admin.action.deactivate')}" ${deactivateDisabled ? 'disabled' : ''}>🗑️</button>
    </td>`;

  const [resetBtn, deactivateBtn] = tr.querySelectorAll('.icon-btn');
  resetBtn.addEventListener('click', () => confirmResetPassword(user.id, user.email));
  deactivateBtn.addEventListener('click', () => confirmDeactivateUser(user.id, user.username));
  return tr;
}

async function confirmResetPassword(id, email) {
  if (!confirm(t('admin.confirm.reset', email))) return;
  try {
    const data = await apiFetch(`/api/admin/users/${id}/reset-password`, { method: 'POST' });
    showToast(data.message, 'success');
    if (!data.email_sent) {
      showToast(t('admin.email.failed'), 'warning');
    }
  } catch (err) {
    showToast('Failed: ' + err.message, 'error');
  }
}

async function confirmDeactivateUser(id, username) {
  if (!confirm(t('admin.confirm.deactivate', username))) return;
  try {
    const data = await apiFetch(`/api/admin/users/${id}/deactivate`, { method: 'POST' });
    showToast(data.message, 'success');
    loadUserList();
  } catch (err) {
    showToast('Failed: ' + err.message, 'error');
  }
}
```

Note: row action buttons use `addEventListener` with the real `user.id`/`user.username`
values (not inline `onclick="..."` string interpolation), so usernames/emails containing
a quote character can't break the generated HTML.

- [ ] **Step 7: Load the user list when the Admin page opens**

Modify `goToAdminPage()` in `frontend/app.js`:

```javascript
function goToAdminPage() {
  document.getElementById('mainPanel').style.display = 'none';
  document.getElementById('auditLogPage').style.display = 'none';
  document.getElementById('adminPage').style.display = 'block';
  applyLang(); // Ensure translations are applied
  loadUserList();
}
```

- [ ] **Step 8: Manually verify in the browser**

Run: `python -m uvicorn main:app --reload --host 127.0.0.1 --port 8002`, open
`http://127.0.0.1:8002/app/`.

Check:
- Log in as `superadmin` → open "Pengurusan Pengguna" → see two collapsible
  sections; "Buat Pengguna" open by default, "Urus Pengguna" collapsed.
- Expand "Urus Pengguna" → table lists all existing users (including any
  `um_test_user1`/`um_test_user2` left over from the smoke tests — fine to leave,
  or manually deactivate them via the UI itself as part of this check).
- Create a new user with a real email address you control → confirm the email
  arrives with a working temporary password, and the new row appears in the table
  after the form resets.
- Click 📝 on a row → confirm dialog appears → confirm → new email arrives.
- Click 🗑️ on a row → confirm dialog appears → confirm → row shows "Tidak Aktif" /
  "Inactive", and both icons on that row are now disabled.
- Confirm both icons are disabled on your own logged-in row.

- [ ] **Step 9: Commit**

No git repo present — skip.

---

### Task 6: Frontend — mandatory "Set New Password" screen after first login

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/app.js`
- Modify: `frontend/lang.js`

**Interfaces:**
- Consumes: `POST /api/auth/change-password` (Task 4); `apiFetch`, `setStoredAuth`, `state.auth` (existing).
- Produces: no interfaces consumed elsewhere — this is the last task in the plan.

- [ ] **Step 1: Add the "Set New Password" screen markup to `frontend/index.html`**

Add immediately after the existing `<div class="login-screen visible" id="loginScreen">...</div>` block (reuses the same `.login-screen` / `.login-box` / `.login-form` CSS classes already defined for the login screen — no new CSS needed):

```html
  <div class="login-screen" id="changePasswordScreen">
    <div class="login-box">
      <div class="login-brand">
        <div class="login-brand-icon">
          <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 3L2 8v2h2v9H2v2h20v-2h-2V10h2V8L12 3zm-4 18V10h2v11H8zm4 0V10h2v11h-2zm4 0V10h2v11h-2zm-4-15.18L17.6 8H6.4L12 5.82z"/>
          </svg>
        </div>
        <div>
          <h2 data-i18n="cp.title">Tetapkan Kata Laluan Baharu</h2>
          <p data-i18n="cp.subtitle">Anda mesti menukar kata laluan sementara sebelum meneruskan.</p>
        </div>
      </div>
      <div class="login-form">
        <label for="cpCurrentPassword" data-i18n="cp.current">Kata Laluan Semasa</label>
        <input id="cpCurrentPassword" class="form-control" type="password" autocomplete="current-password" />

        <label for="cpNewPassword" data-i18n="cp.new">Kata Laluan Baharu</label>
        <input id="cpNewPassword" class="form-control" type="password" autocomplete="new-password" />

        <label for="cpConfirmPassword" data-i18n="cp.confirm">Sahkan Kata Laluan Baharu</label>
        <input id="cpConfirmPassword" class="form-control" type="password" autocomplete="new-password" />

        <div id="changePasswordError" class="form-error"></div>

        <button class="btn btn-primary btn-block" id="btnChangePassword" onclick="runChangePassword()">
          <span class="btn-text" data-i18n="cp.submit">Tetapkan Kata Laluan</span>
        </button>
      </div>
    </div>
  </div>
```

- [ ] **Step 2: Add the i18n keys to `frontend/lang.js`**

Add to the `bm` object:

```javascript
    'cp.title':    'Tetapkan Kata Laluan Baharu',
    'cp.subtitle': 'Anda mesti menukar kata laluan sementara sebelum meneruskan.',
    'cp.current':  'Kata Laluan Semasa',
    'cp.new':      'Kata Laluan Baharu',
    'cp.confirm':  'Sahkan Kata Laluan Baharu',
    'cp.submit':   'Tetapkan Kata Laluan',
    'cp.error.missing':  'Sila isi semua medan.',
    'cp.error.mismatch': 'Kata laluan baharu tidak sepadan.',
    'cp.error.short':    'Kata laluan baharu mestilah sekurang-kurangnya 8 aksara.',
    'cp.success':  'Kata laluan berjaya ditukar.',
```

Add to the `en` object:

```javascript
    'cp.title':    'Set New Password',
    'cp.subtitle': 'You must change your temporary password before continuing.',
    'cp.current':  'Current Password',
    'cp.new':      'New Password',
    'cp.confirm':  'Confirm New Password',
    'cp.submit':   'Set Password',
    'cp.error.missing':  'Please fill in all fields.',
    'cp.error.mismatch': 'New passwords do not match.',
    'cp.error.short':    'New password must be at least 8 characters.',
    'cp.success':  'Password changed successfully.',
```

- [ ] **Step 3: Add `showChangePasswordScreen` / `hideChangePasswordScreen` / `runChangePassword` to `frontend/app.js`**

Add near `showLoginScreen`/`hideLoginScreen`:

```javascript
function showChangePasswordScreen() {
  document.getElementById('changePasswordScreen').classList.add('visible');
}

function hideChangePasswordScreen() {
  document.getElementById('changePasswordScreen').classList.remove('visible');
}

async function runChangePassword() {
  const btn = document.getElementById('btnChangePassword');
  const currentPassword = document.getElementById('cpCurrentPassword').value;
  const newPassword = document.getElementById('cpNewPassword').value;
  const confirmPassword = document.getElementById('cpConfirmPassword').value;
  const errorEl = document.getElementById('changePasswordError');
  errorEl.textContent = '';

  if (!currentPassword || !newPassword || !confirmPassword) {
    errorEl.textContent = t('cp.error.missing');
    return;
  }
  if (newPassword !== confirmPassword) {
    errorEl.textContent = t('cp.error.mismatch');
    return;
  }
  if (newPassword.length < 8) {
    errorEl.textContent = t('cp.error.short');
    return;
  }

  btn.disabled = true;
  btn.classList.add('loading');
  try {
    await apiFetch('/api/auth/change-password', {
      method: 'POST',
      body: { current_password: currentPassword, new_password: newPassword },
    });
    state.auth.is_first_login = false;
    setStoredAuth(state.auth);
    hideChangePasswordScreen();
    document.getElementById('cpCurrentPassword').value = '';
    document.getElementById('cpNewPassword').value = '';
    document.getElementById('cpConfirmPassword').value = '';
    showToast(t('cp.success'), 'success');
  } catch (err) {
    errorEl.textContent = err.message;
  } finally {
    btn.disabled = false;
    btn.classList.remove('loading');
  }
}
```

- [ ] **Step 4: Gate `initAuth()` and `runLogin()` on `is_first_login`**

Modify `initAuth()`:

```javascript
function initAuth() {
  const stored = getStoredAuth();
  if (stored?.token && stored?.username && stored?.role_name) {
    state.auth = stored;
    hideLoginScreen();
    updateUserChip();
    showAdminPanel();
    if (stored.is_first_login) {
      showChangePasswordScreen();
    }
    return;
  }
  showLoginScreen('');
}
```

Modify the success branch of `runLogin()` (currently `setStoredAuth(data); updateUserChip(); showAdminPanel(); hideLoginScreen();`):

```javascript
    setStoredAuth(data);
    updateUserChip();
    showAdminPanel();
    hideLoginScreen();
    if (data.is_first_login) {
      showChangePasswordScreen();
    }
```

- [ ] **Step 5: Manually verify in the browser**

Run: `python -m uvicorn main:app --reload --host 127.0.0.1 --port 8002`, open
`http://127.0.0.1:8002/app/`.

Check:
- Create a brand-new user (Task 5's flow), then log in as that user with the
  temporary password from the email → confirm the "Set New Password" screen
  appears immediately and the dashboard is not visible/reachable behind it.
- Submit with a wrong "current password" → error shown, screen stays.
- Submit with mismatched new/confirm passwords → error shown, screen stays.
- Submit correctly → screen disappears, dashboard appears, toast confirms success.
- Reload the page (or log out and back in) with the new password → no
  change-password screen this time (is_first_login is now false), dashboard
  loads directly.
- Reset that same user's password from the Admin page (Task 5's 📝 icon) → log
  in as them again with the newly emailed temporary password → confirm the
  change-password screen reappears (is_first_login was set back to true by the
  reset).

- [ ] **Step 6: Commit**

No git repo present — skip.

---

## Self-Review Notes

- **Spec coverage:** Password-less create (Task 2), email module + both BM/EN
  templates verbatim (Task 1), one template for both creation and reset (Tasks 2
  & 3), email-failure-doesn't-block behavior (Tasks 2 & 3), deactivate not
  hard-delete + self/last-superadmin guards (Task 3), list/reset/deactivate
  endpoints (Task 3), forced change-password endpoint + screen (Tasks 4 & 6),
  two-collapsible-section admin UI + table columns (Task 5) — all covered.
- **Placeholder scan:** no `TBD`/`TODO`. The one deliberately-open note (Task 2
  Step 6, "if `rbac_smoke_test.py` instead fails...") tells the implementer
  exactly what to check and exactly what to do in either outcome — not a
  postponement.
- **Type/name consistency:** `email_utils.generate_temp_password()` /
  `send_temp_password_email()` signatures defined once (Task 1) and used
  identically in Tasks 2 and 3; `main.email_utils` (module import, not
  `from...import`) is consistent across Tasks 2-4 so the test monkeypatch in
  Task 2 Step 1 (`main_module.email_utils.send_temp_password_email = ...`)
  actually intercepts calls made in Task 3's endpoints too; `user_management_smoke_test.py`
  is built incrementally across all four backend tasks with one running `client`
  and `admin_token`, not recreated per task.
