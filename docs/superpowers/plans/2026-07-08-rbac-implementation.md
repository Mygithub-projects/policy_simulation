# RBAC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Superadmin / Forecasting Admin (`admin`) / Policy Maker (`user`) real, backend-enforced permissions, matching `docs/superpowers/specs/2026-07-08-rbac-design.md`.

**Architecture:** Add an in-memory session store + a `require_role` FastAPI dependency in `main.py`, gate the endpoints that need it, start writing to the existing `simulation_run_log` table plus a new `audit_log` table, add a summary-CSV download, and update the frontend to send the session token and hide/show the relevant buttons per role.

**Tech Stack:** FastAPI, DuckDB, plain Python (no pytest — this repo uses plain assert-based smoke-test scripts run directly with `python <file>.py`), vanilla JS frontend (no framework).

## Global Constraints

- Reuse existing DB role values (`superadmin`, `admin`, `user`) — no renaming, no new roles table changes.
- Additive-only schema changes: new `audit_log` table, new `users.can_view_audit_log` column. No existing table's columns are altered or dropped.
- No new page routing/navigation system — Audit Log is reached the same way the existing Admin page is (a header button swaps the visible `<main>` panel).
- No restriction on policy levers or single/combined mode for Policy Maker — only download buttons are gated.
- Session store is in-memory only, no expiry, resets on server restart (documented limitation, not a bug to fix in this plan).
- Follow this repo's existing test style: plain script with `assert` statements using `fastapi.testclient.TestClient`, run via `python <file>.py`, matching `api_smoke_test.py`. Do not introduce pytest.
- Keep policy formulas, projection year, port number, and API contract fields already used by the frontend untouched.

---

## File Structure

| File | Change |
|---|---|
| `data/*.duckdb` (via a new one-off script) | Additive schema: `audit_log` table, `users.can_view_audit_log` column. |
| `migrate_rbac_schema.py` (new) | One-off migration script, same pattern as `update_user_schema.py`. |
| `main.py` | Add `SESSIONS` dict, `require_role` dependency, `/api/auth/logout`, `/api/audit-log`, `/api/runs/{run_id}/summary.csv`; gate existing endpoints; write `audit_log` rows on login/create-user. |
| `api_models.py` | Add `can_view_audit_log: bool = False` to `CreateUserInput`. |
| `tools.py` | Extend `WorkforceTools.save_run` and the live `MockWorkforceTools.save_run` to accept `subject_summary` and write a `{run_id}_summary.csv`; add module-level `write_summary_csv` helper. |
| `agents/orchestrator.py` | Pass `subject_summary` into `self.tools.save_run(...)`. |
| `frontend/app.js` | Attach auth header in `apiFetch`; handle 401/403; gate detailed-download button; add summary-download button; add Audit Log page wiring; add `can_view_audit_log` checkbox handling in create-user form. |
| `frontend/index.html` | Add Audit Log header button + page markup; add "Download Summary Report" button; add "Can view audit log" checkbox to create-user form. |
| `frontend/lang.js` | Add new i18n strings for the above. |
| `rbac_smoke_test.py` (new) | Script-style smoke test covering session enforcement, audit log, summary CSV — mirrors `api_smoke_test.py`. |

---

### Task 1: Additive schema migration (`audit_log` table + `users.can_view_audit_log`)

**Files:**
- Create: `migrate_rbac_schema.py`
- Modify (verify only, no code change): `data/workforce_policy_agent_preclean_20260619_144113.duckdb`

**Interfaces:**
- Produces: `audit_log` table with columns `(id INTEGER PRIMARY KEY, occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, actor_username VARCHAR, actor_role VARCHAR, action VARCHAR, details VARCHAR)`.
- Produces: `users.can_view_audit_log BOOLEAN DEFAULT FALSE`.
- Later tasks (2, 3) write to `audit_log` and read/write `users.can_view_audit_log`.

- [ ] **Step 1: Write the migration script**

```python
"""One-off migration: adds audit_log table and users.can_view_audit_log column.
Additive only — does not modify any existing table's existing columns."""

import duckdb

from config import get_database_path

con = duckdb.connect(str(get_database_path()))

con.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY,
        occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        actor_username VARCHAR,
        actor_role VARCHAR,
        action VARCHAR,
        details VARCHAR
    )
""")
con.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS can_view_audit_log BOOLEAN DEFAULT FALSE")
con.commit()

print(con.execute("DESCRIBE audit_log").fetchall())
print(con.execute("DESCRIBE users").fetchall())
con.close()
```

- [ ] **Step 2: Run it and verify the new table/column exist**

Run: `python migrate_rbac_schema.py`
Expected output: a `DESCRIBE audit_log` row list showing the 6 columns above, and a `DESCRIBE users` row list that includes `can_view_audit_log | BOOLEAN`.

- [ ] **Step 3: Verify no existing table was altered**

Run:
```bash
python -c "
import duckdb
from config import get_database_path
con = duckdb.connect(str(get_database_path()), read_only=True)
print(con.execute('SELECT COUNT(*) FROM users').fetchone())
print(con.execute(\"SELECT column_name FROM information_schema.columns WHERE table_name='users'\").fetchall())
"
```
Expected: same row count as before this task, and the column list contains all original `users` columns plus `can_view_audit_log` at the end.

- [ ] **Step 4: Commit**

No git repo is present in this project directory — skip `git commit`. Note the change in the running task list instead.

---

### Task 2: Session store, `require_role` dependency, login/logout audit logging

**Files:**
- Modify: `main.py`
- Create: `rbac_smoke_test.py`

**Interfaces:**
- Consumes: `audit_log` table from Task 1.
- Produces: module-level `SESSIONS: dict[str, dict]` (`token -> {"username": str, "role_name": str, "can_view_audit_log": bool}`).
- Produces: `require_role(*roles: str)` — a FastAPI dependency factory. Calling `require_role("superadmin", "admin")` returns a dependency function that, when injected into a route, returns the session dict `{"username", "role_name", "can_view_audit_log"}` for the caller, or raises `HTTPException(401)` / `HTTPException(403)`.
- Produces: `POST /api/auth/logout` (body: `{"token": str}` optional — reads `X-Auth-Token` header) removing the session.
- Later tasks (3, 4) use `require_role(...)` as a route dependency and read `session["username"]` / `session["role_name"]` to stamp audit rows.

- [ ] **Step 1: Write the failing test**

```python
"""rbac_smoke_test.py — exercises session/role enforcement without starting a web server."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python rbac_smoke_test.py`
Expected: `AssertionError` on the first assertion (`no_token.status_code == 401`) because `/api/admin/create-user` currently returns `200` (or a validation error, but never `401`) — there is no auth check yet.

- [ ] **Step 3: Implement the session store and dependency in `main.py`**

Add near the top of `main.py`, after the existing imports (after the `import secrets` line):

```python
from fastapi import Depends, Header
```

Add after the `app = FastAPI(...)` block and before `get_system()`:

```python
# ============================================================
# SESSIONS — in-memory token -> user mapping (resets on restart)
# ============================================================

SESSIONS: dict[str, dict[str, Any]] = {}


def require_role(*roles: str):
    """FastAPI dependency factory: returns a dependency that requires a valid
    X-Auth-Token belonging to one of the given roles. Returns the session dict."""

    def _dependency(x_auth_token: str | None = Header(default=None)) -> dict[str, Any]:
        if not x_auth_token or x_auth_token not in SESSIONS:
            raise HTTPException(status_code=401, detail="Missing or invalid session token")
        session = SESSIONS[x_auth_token]
        if session["role_name"] not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission to perform this action")
        return session

    return _dependency


def write_audit_log(actor_username: str, actor_role: str, action: str, details: str = "") -> None:
    connection = duckdb.connect(str(get_database_path()), read_only=False)
    try:
        max_id = connection.execute("SELECT COALESCE(MAX(id), 0) FROM audit_log").fetchone()[0]
        connection.execute(
            "INSERT INTO audit_log (id, actor_username, actor_role, action, details) VALUES (?, ?, ?, ?, ?)",
            [max_id + 1, actor_username, actor_role, action, details],
        )
        connection.commit()
    finally:
        connection.close()
```

- [ ] **Step 4: Update `login()` to populate `SESSIONS` and write audit rows**

Replace the existing `login` function body's final section (from `if not row:` to the end) in `main.py`:

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


@app.post("/api/auth/logout")
def logout(x_auth_token: str | None = Header(default=None)) -> dict[str, Any]:
    if x_auth_token and x_auth_token in SESSIONS:
        session = SESSIONS.pop(x_auth_token)
        write_audit_log(session["username"], session["role_name"], "logout", "")
    return {"ok": True}
```

- [ ] **Step 5: Require a valid session on `create_user` and write an audit row**

Change the route decorator and signature:

```python
@app.post("/api/admin/create-user")
def create_user(
    payload: CreateUserInput,
    session: dict[str, Any] = Depends(require_role("superadmin")),
) -> dict[str, Any]:
    """Create a new user account. Superadmin only."""
```

At the very end of `create_user`, right before `return {...}`, add:

```python
    write_audit_log(
        session["username"], session["role_name"], "user_created",
        f"created '{payload.username}' with role '{payload.role_name}'",
    )
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python rbac_smoke_test.py`
Expected: `RBAC session smoke test passed` printed, no `AssertionError`.

- [ ] **Step 7: Run the existing smoke tests to check nothing else broke**

Run: `python smoke_test.py` then `python api_smoke_test.py`
Expected: both complete and print their existing success messages (`API smoke test passed`, etc.) with no `AssertionError`. `api_smoke_test.py` does not call `/api/admin/create-user`, so it is unaffected by the new auth requirement on that endpoint.

- [ ] **Step 8: Commit**

No git repo present — skip. Track progress via the plan checkboxes only.

---

### Task 3: Gate remaining endpoints + `GET /api/audit-log`

**Files:**
- Modify: `main.py`
- Modify: `rbac_smoke_test.py`

**Interfaces:**
- Consumes: `require_role(...)` and `SESSIONS` from Task 2.
- Consumes: `simulation_run_log` table (existing, unused so far) and `audit_log` table (Task 1).
- Produces: `GET /api/audit-log` returning `{"entries": [{"occurred_at": str, "actor": str, "role": str, "action": str, "details": str}]}` sorted newest-first, merged from `audit_log` and `simulation_run_log`.

- [ ] **Step 1: Write the failing test (append to `rbac_smoke_test.py`)**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python rbac_smoke_test.py`
Expected: fails at `forecast_public.status_code == 401` (currently `200`, no auth check on that route yet), or at the `audit_no_token`/`audit_as_superadmin` assertions since `/api/audit-log` does not exist yet (`404`).

- [ ] **Step 3: Gate `forecast_2027` and `download_run` in `main.py`**

```python
@app.post("/api/forecast/2027")
def forecast_2027(
    payload: ForecastInput,
    session: dict[str, Any] = Depends(require_role("superadmin", "admin")),
) -> dict[str, Any]:
    """Return the ML baseline projection without changing policy parameters."""
```

```python
@app.get("/api/runs/{run_id}/detail.csv")
def download_run(
    run_id: str,
    session: dict[str, Any] = Depends(require_role("superadmin", "admin")),
):
```

- [ ] **Step 4: Require any authenticated role on `simulate` and `run_agent`**

```python
@app.post("/api/simulate")
def simulate(
    payload: ScenarioInput,
    session: dict[str, Any] = Depends(require_role("superadmin", "admin", "user")),
) -> dict[str, Any]:
```

```python
@app.post("/api/agent/run")
def run_agent(
    payload: AgentQuestionInput,
    session: dict[str, Any] = Depends(require_role("superadmin", "admin", "user")),
) -> dict[str, Any]:
```

(Task 4 will use the injected `session` inside these two functions to stamp `simulation_run_log.run_by` — for this task, just add the dependency so gating tests pass; leave the function bodies otherwise unchanged.)

- [ ] **Step 5: Add `GET /api/audit-log`**

Add this route, placed after `download_run`:

```python
@app.get("/api/audit-log")
def get_audit_log(
    session: dict[str, Any] = Depends(require_role("superadmin", "admin")),
) -> dict[str, Any]:
    if session["role_name"] == "admin" and not session.get("can_view_audit_log"):
        raise HTTPException(status_code=403, detail="Audit log is not enabled for this account")

    connection = duckdb.connect(str(get_database_path()), read_only=True)
    try:
        audit_rows = connection.execute(
            "SELECT occurred_at, actor_username, actor_role, action, details FROM audit_log"
        ).fetchall()
        run_rows = connection.execute(
            "SELECT run_timestamp, run_by, run_type, target_scope, notes FROM simulation_run_log"
        ).fetchall()
    finally:
        connection.close()

    entries = [
        {"occurred_at": str(r[0]), "actor": r[1], "role": r[2], "action": r[3], "details": r[4] or ""}
        for r in audit_rows
    ] + [
        {
            "occurred_at": str(r[0]),
            "actor": r[1] or "unknown",
            "role": "",
            "action": f"simulation_run:{r[2] or 'simulate'}",
            "details": f"scope={r[3] or ''} {r[4] or ''}".strip(),
        }
        for r in run_rows
    ]
    entries.sort(key=lambda e: e["occurred_at"], reverse=True)
    return {"entries": entries}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python rbac_smoke_test.py`
Expected: both `RBAC session smoke test passed` and `RBAC endpoint-gating smoke test passed` printed.

- [ ] **Step 7: Run existing smoke tests**

Run: `python smoke_test.py` then `python api_smoke_test.py`
Expected: `api_smoke_test.py` now FAILS at its `/api/forecast/2027` and `/api/simulate` calls with `401`, because those routes are gated and the script sends no token.

Fix `api_smoke_test.py` (it represents an already-logged-in trusted caller in its original intent) by logging in once at the top and reusing the token on every gated call:

```python
# Insert immediately after `client = TestClient(app)`:
_login = client.post("/api/auth/login", json={"username": "superadmin", "password": "SuperAdmin123!"})
assert _login.status_code == 200, _login.text
AUTH_HEADERS = {"X-Auth-Token": _login.json()["token"]}
```

Then add `headers=AUTH_HEADERS` to every `client.post("/api/forecast/2027", ...)`, `client.post("/api/simulate", ...)`, and `client.post("/api/agent/run", ...)` call in that file (5 call sites: `forecast`, `simulation`, `coteaching`, `combined_two`, `combined_all`, `agent`, `forecast_agent`, `ambiguous_agent`, `coteaching_agent` — every `client.post` call needs `headers=AUTH_HEADERS` added as a keyword argument).

- [ ] **Step 8: Run `api_smoke_test.py` again to confirm the fix**

Run: `python api_smoke_test.py`
Expected: `API smoke test passed` with no `AssertionError`.

- [ ] **Step 9: Commit**

No git repo present — skip.

---

### Task 4: Write simulation runs to `simulation_run_log`; add summary CSV download

**Files:**
- Modify: `agents/orchestrator.py`
- Modify: `tools.py`
- Modify: `main.py`
- Modify: `rbac_smoke_test.py`

**Interfaces:**
- Consumes: `session` dict already injected into `simulate`/`run_agent` in Task 3 (`session["username"]`, `session["role_name"]`).
- Produces: `WorkforceTools.save_run(scenario, detail, summary, subject_summary, run_by=None)` — note the added `subject_summary` positional param and new optional `run_by` keyword — returns the same dict as before plus a `"summary_csv"` key.
- Produces: module-level `tools.write_summary_csv(output_dir: Path, run_id: str, summary: dict, subject_summary: pd.DataFrame) -> Path`.
- Produces: `GET /api/runs/{run_id}/summary.csv`, open to any authenticated role.
- This is the **only** task that touches `tools.py`'s `save_run` signature — no later task changes it again.

- [ ] **Step 1: Write the failing test (append to `rbac_smoke_test.py`)**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python rbac_smoke_test.py`
Expected: fails at `sim.json()["artifacts"]["summary_csv"]` with a `KeyError`/`AssertionError` (key does not exist yet), since `save_run` doesn't write a summary CSV yet.

- [ ] **Step 3: Add `write_summary_csv` and extend `save_run` in `tools.py`**

Add this module-level function in `tools.py`, right before `class WorkforceTools:`:

```python
def write_summary_csv(
    output_dir: Path,
    run_id: str,
    summary: dict[str, Any],
    subject_summary: pd.DataFrame,
) -> Path:
    """Writes an aggregated KPI + per-subject CSV (no per-school rows)."""
    csv_path = output_dir / f"{run_id}_summary.csv"
    kpi_rows = pd.DataFrame(
        [{"metric": key, "value": value} for key, value in summary.items()]
    )
    subject_rows = subject_summary.rename(columns={"subjek": "subject"}).copy()
    if "subject" in subject_rows.columns:
        subject_rows["subject"] = subject_rows["subject"].replace(
            {"SAINS": "SCIENCE", "MATEMATIK": "MATHEMATICS"}
        )
    with open(csv_path, "w", encoding="utf-8", newline="") as handle:
        handle.write("# KPI Summary\n")
        kpi_rows.to_csv(handle, index=False)
        handle.write("\n# Per-Subject Summary\n")
        subject_rows.to_csv(handle, index=False)
    return csv_path
```

Modify `WorkforceTools.save_run` (currently at line ~388-434 in `tools.py`) to accept `subject_summary` and `run_by`, and write the summary CSV:

```python
    @staticmethod
    def save_run(
        scenario: ScenarioRequest,
        result: pd.DataFrame,
        summary: dict[str, Any],
        subject_summary: pd.DataFrame,
        run_by: str | None = None,
    ) -> dict[str, str]:
        run_id = datetime.now().strftime("RUN_%Y%m%d_%H%M%S_%f")
        errors: list[str] = []
        for output_dir in get_output_directories():
            csv_path = output_dir / f"{run_id}_detail.csv"
            json_path = output_dir / f"{run_id}_summary.json"
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                export_result = result.rename(
                    columns={
                        "kod_sekolah": "school_code",
                        "negeri": "state",
                        "subjek": "subject",
                    }
                ).copy()
                if "subject" in export_result.columns:
                    export_result["subject"] = export_result["subject"].replace(
                        {"SAINS": "SCIENCE", "MATEMATIK": "MATHEMATICS"}
                    )
                export_result.to_csv(csv_path, index=False)
                summary_csv_path = write_summary_csv(output_dir, run_id, summary, subject_summary)
                json_path.write_text(
                    json.dumps(
                        {
                            "run_id": run_id,
                            "scenario": scenario.to_dict(),
                            "summary": summary,
                            "run_by": run_by,
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                return {
                    "run_id": run_id,
                    "detail_csv": str(csv_path),
                    "summary_csv": str(summary_csv_path),
                    "summary_json": str(json_path),
                    "output_directory": str(output_dir),
                }
            except OSError as error:
                errors.append(f"{output_dir}: {error}")
        raise PermissionError(
            "Unable to save simulation output. Tried: " + " | ".join(errors)
        )
```

Apply the exact same signature change (`subject_summary`, `run_by=None` params; write `summary_csv_path = write_summary_csv(...)`; include `"summary_csv"` in the returned dict) to the **live** `MockWorkforceTools.save_run` — this is the second `MockWorkforceTools` class definition in the file (the first one, defined earlier in the file, is dead code shadowed by the second and is not touched by this plan):

```python
    def save_run(
        self,
        scenario: ScenarioRequest,
        result: "pd.DataFrame",
        summary: dict[str, Any],
        subject_summary: "pd.DataFrame",
        run_by: str | None = None,
    ) -> dict[str, str]:
        run_id = "RUN_TEST"
        for output_dir in get_output_directories():
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                csv_path = output_dir / f"{run_id}_detail.csv"
                json_path = output_dir / f"{run_id}_summary.json"
                result.to_csv(csv_path, index=False)
                summary_csv_path = write_summary_csv(output_dir, run_id, summary, subject_summary)
                json_path.write_text(
                    json.dumps(
                        {"run_id": run_id, "scenario": scenario.to_dict(), "summary": summary, "run_by": run_by},
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                return {
                    "run_id": run_id,
                    "detail_csv": str(csv_path),
                    "summary_csv": str(summary_csv_path),
                    "summary_json": str(json_path),
                    "output_directory": str(output_dir),
                }
            except Exception:
                continue
        raise PermissionError("Unable to save simulation output for mock tool")
```

- [ ] **Step 4: Update the caller in `agents/orchestrator.py`**

```python
    def execute(self, scenario: ScenarioRequest, lang: str = "en", run_by: str | None = None) -> dict[str, Any]:
        scenario.validate()
        detail, summary, subject_summary = self.simulation_agent.run(scenario)
        policy_impacts = self.simulation_agent.compare_active_policies(scenario)
        recommendations, rules = self.recommendation_agent.run(detail, lang)
        explanation, explanation_source = self.explanation_agent.run(
            scenario, summary, subject_summary, lang
        )
        artifacts = self.tools.save_run(scenario, detail, summary, subject_summary, run_by=run_by)
        return {
            "scenario": scenario,
            "scenario_source": "Direct user controls",
            "detail": detail,
            "summary": summary,
            "subject_summary": subject_summary,
            "policy_impacts": policy_impacts,
            "recommendations": recommendations,
            "rules": rules,
            "explanation": explanation,
            "explanation_source": explanation_source,
            "artifacts": artifacts,
        }

    def execute_from_text(
        self,
        question: str,
        defaults: ScenarioRequest | None = None,
        lang: str = "en",
        run_by: str | None = None,
    ) -> dict[str, Any]:
        scenario, source = self.scenario_agent.parse(question, defaults)
        output = self.execute(scenario, lang, run_by=run_by)
        output["scenario_source"] = source
        return output
```

- [ ] **Step 5: Pass `run_by` and write to `simulation_run_log` in `main.py`**

Update `simulate` and `run_agent` bodies:

```python
@app.post("/api/simulate")
def simulate(
    payload: ScenarioInput,
    session: dict[str, Any] = Depends(require_role("superadmin", "admin", "user")),
) -> dict[str, Any]:
    try:
        _, orchestrator = get_system()
        output = orchestrator.execute(payload.to_scenario(), lang=payload.lang, run_by=session["username"])
        _write_run_log(output, session, run_type="simulate")
        return serialize_output(output)
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/agent/run")
def run_agent(
    payload: AgentQuestionInput,
    session: dict[str, Any] = Depends(require_role("superadmin", "admin", "user")),
) -> dict[str, Any]:
    try:
        _, orchestrator = get_system()
        output = orchestrator.execute_from_text(payload.question, lang=payload.lang, run_by=session["username"])
        _write_run_log(output, session, run_type="agent")
        return serialize_output(output)
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
```

Add the `_write_run_log` helper right after `write_audit_log` (defined in Task 2):

```python
def _write_run_log(output: dict[str, Any], session: dict[str, Any], run_type: str) -> None:
    scenario = output["scenario"]
    run_id = output["artifacts"]["run_id"]
    target_scope = f"{scenario.subject}/{scenario.negeri}/{scenario.ppd}"
    connection = duckdb.connect(str(get_database_path()), read_only=False)
    try:
        connection.execute(
            "INSERT INTO simulation_run_log (run_id, scenario_id, run_timestamp, run_by, run_type, target_scope, notes) "
            "VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?)",
            [run_id, run_id, session["username"], run_type, target_scope, output.get("scenario_source", "")],
        )
        connection.commit()
    finally:
        connection.close()
```

`ScenarioRequest` (see `schemas.py`) exposes `.subject`, `.negeri`, `.ppd` directly as dataclass fields — the code above is already correct as written.

- [ ] **Step 6: Add the summary-CSV download route**

Add after `download_run` (and after `get_audit_log`) in `main.py`:

```python
@app.get("/api/runs/{run_id}/summary.csv")
def download_run_summary(
    run_id: str,
    session: dict[str, Any] = Depends(require_role("superadmin", "admin", "user")),
):
    if not run_id.startswith("RUN_") or not run_id.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid run_id")
    for output_root in get_output_directories():
        output_root = output_root.resolve()
        file_path = (output_root / f"{run_id}_summary.csv").resolve()
        if output_root in file_path.parents and file_path.exists():
            return FileResponse(
                file_path,
                media_type="text/csv",
                filename=file_path.name,
            )
    raise HTTPException(status_code=404, detail="Run summary not found")
```

- [ ] **Step 7: Run test to verify it passes**

Run: `python rbac_smoke_test.py`
Expected: all four print statements appear, no `AssertionError`.

- [ ] **Step 8: Run full existing suite**

Run: `python smoke_test.py` then `python api_smoke_test.py`
Expected: both pass. `smoke_test.py` calls `Orchestrator(tools).execute(scenario)` directly with no `run_by` — confirm this still works since `run_by` defaults to `None` in both `execute()` and `save_run()`.

- [ ] **Step 9: Commit**

No git repo present — skip.

---

### Task 5: Frontend — auth header, download gating, Audit Log page, create-user checkbox

**Files:**
- Modify: `frontend/app.js`
- Modify: `frontend/index.html`
- Modify: `frontend/lang.js`

**Interfaces:**
- Consumes: `POST /api/auth/login` response now includes `can_view_audit_log` (Task 2); `GET /api/audit-log` (Task 3); `GET /api/runs/{run_id}/summary.csv` (Task 4).
- Produces: no new interfaces consumed by other tasks — this is the last task.

- [ ] **Step 1: Attach the auth token to every API call in `frontend/app.js`**

Modify `apiFetch` (around line 1556):

```javascript
async function apiFetch(path, options = {}) {
  const { method = 'GET', body } = options;
  const fetchOptions = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (state.auth?.token) {
    fetchOptions.headers['X-Auth-Token'] = state.auth.token;
  }
  if (body) fetchOptions.body = JSON.stringify(body);

  const res = await fetch(`${API_BASE}${path}`, fetchOptions);

  if (!res.ok) {
    let errMsg = `HTTP ${res.status}`;
    try {
      const errData = await res.json();
      errMsg = errData.detail || errData.message || errMsg;
    } catch {}
    if (res.status === 401 || res.status === 403) {
      showToast(t('toast.no.permission'), 'error');
    }
    throw new Error(errMsg);
  }

  return res.json();
}
```

- [ ] **Step 2: Add the new i18n strings to `frontend/lang.js`**

Add these keys to both the `bm` and `en` translation objects in `frontend/lang.js` (place them near the existing `admin.*` keys):

```javascript
    'toast.no.permission': 'Anda tidak mempunyai kebenaran untuk melakukan tindakan ini.',
    'nav.audit': 'Log Audit',
    'audit.title': 'Log Audit',
    'audit.col.time': 'Masa',
    'audit.col.actor': 'Pengguna',
    'audit.col.role': 'Peranan',
    'audit.col.action': 'Tindakan',
    'audit.col.details': 'Butiran',
    'admin.canviewaudit': 'Boleh Lihat Log Audit',
    'btn.download.summary': 'Muat Turun Ringkasan',
```

(English block, same keys, English text — copy the existing bilingual pattern used for `admin.title` etc.:)

```javascript
    'toast.no.permission': 'You do not have permission to perform this action.',
    'nav.audit': 'Audit Log',
    'audit.title': 'Audit Log',
    'audit.col.time': 'Time',
    'audit.col.actor': 'User',
    'audit.col.role': 'Role',
    'audit.col.action': 'Action',
    'audit.col.details': 'Details',
    'admin.canviewaudit': 'Can View Audit Log',
    'btn.download.summary': 'Download Summary Report',
```

- [ ] **Step 3: Add the Audit Log button and page markup to `frontend/index.html`**

In the header, right after the existing `adminBtn` button (around line 36):

```html
    <button id="auditLogBtn" class="btn btn-secondary" style="display:none; margin-right: 12px;" onclick="goToAuditLogPage()" data-i18n="nav.audit">Log Audit</button>
```

Add the "Can view audit log" checkbox to the create-user form, right after the `newRole` `<select>` closes (around line 473, inside the `form-group` that follows it):

```html
              <div class="form-group" id="canViewAuditGroup" style="display:none;">
                <label>
                  <input type="checkbox" id="newCanViewAudit" />
                  <span data-i18n="admin.canviewaudit">Can View Audit Log</span>
                </label>
              </div>
```

Add a new `<main>` page for the Audit Log, right after the existing `#adminPage` `</main>` (before the closing `</div></div>` at the end of `app-body`):

```html
    <!-- ===================== AUDIT LOG PAGE ===================== -->
    <main class="main-panel" id="auditLogPage" style="display:none;">
      <div style="padding: 32px; max-width: 1100px; margin: 0 auto;">
        <button class="btn btn-outline btn-sm" onclick="goToDashboard()" style="margin-bottom: 24px;">
          <span>← Kembali ke Papan Pemuka</span>
        </button>
        <div class="admin-panel">
          <div class="result-card">
            <div class="result-card-header" data-i18n="audit.title">Log Audit</div>
            <div class="result-card-body">
              <div class="table-container">
                <table class="rec-table">
                  <thead>
                    <tr>
                      <th data-i18n="audit.col.time">Masa</th>
                      <th data-i18n="audit.col.actor">Pengguna</th>
                      <th data-i18n="audit.col.role">Peranan</th>
                      <th data-i18n="audit.col.action">Tindakan</th>
                      <th data-i18n="audit.col.details">Butiran</th>
                    </tr>
                  </thead>
                  <tbody id="auditLogBody"></tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
```

Add the "Download Summary Report" button next to the existing `btnDownload` button (around line 384, inside `.table-footer`):

```html
              <button class="btn btn-outline btn-sm" id="btnDownloadSummary" onclick="downloadSummaryCSV()" style="display:none;" data-i18n="btn.download.summary">
                ⬇ Muat Turun Ringkasan
              </button>
```

- [ ] **Step 4: Add the JS behaviour in `frontend/app.js`**

Modify `showAdminPanel()` (around line 72) to also gate the Audit Log button and to show/hide the create-user checkbox by role selection:

```javascript
function showAdminPanel() {
  const adminBtn = document.getElementById('adminBtn');
  const auditBtn = document.getElementById('auditLogBtn');
  adminBtn.style.display = state.auth.role_name === 'superadmin' ? 'inline-block' : 'none';
  const canSeeAudit = state.auth.role_name === 'superadmin'
    || (state.auth.role_name === 'admin' && state.auth.can_view_audit_log);
  auditBtn.style.display = canSeeAudit ? 'inline-block' : 'none';
}

function goToAuditLogPage() {
  const canSeeAudit = state.auth.role_name === 'superadmin'
    || (state.auth.role_name === 'admin' && state.auth.can_view_audit_log);
  if (!canSeeAudit) {
    showToast(t('toast.no.permission'), 'error');
    return;
  }
  document.getElementById('mainPanel').style.display = 'none';
  document.getElementById('adminPage').style.display = 'none';
  document.getElementById('auditLogPage').style.display = 'block';
  applyLang();
  loadAuditLog();
}

async function loadAuditLog() {
  const tbody = document.getElementById('auditLogBody');
  tbody.innerHTML = '';
  try {
    const data = await apiFetch('/api/audit-log');
    (data.entries || []).forEach(entry => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${entry.occurred_at}</td>
        <td>${entry.actor}</td>
        <td>${entry.role}</td>
        <td>${entry.action}</td>
        <td>${entry.details}</td>`;
      tbody.appendChild(tr);
    });
  } catch (err) {
    showToast('Failed to load audit log: ' + err.message, 'error');
  }
}
```

Modify `goToDashboard()` (around line 87) to also hide the Audit Log page:

```javascript
function goToDashboard() {
  document.getElementById('adminPage').style.display = 'none';
  document.getElementById('auditLogPage').style.display = 'none';
  document.getElementById('mainPanel').style.display = 'block';
  applyLang();
}
```

Add role dropdown change handling for the checkbox, inside `document.addEventListener('DOMContentLoaded', ...)` (around line 302), by adding one line to wire up a listener; and add the listener function itself right after `handleCreateUser`:

```javascript
function onNewRoleChange() {
  const role = document.getElementById('newRole').value;
  document.getElementById('canViewAuditGroup').style.display = role === 'admin' ? 'block' : 'none';
}
```

In `index.html`, add `onchange="onNewRoleChange()"` to the existing `<select id="newRole" ...>` tag.

Modify `handleCreateUser` (around line 93) to include the checkbox value in the request body:

```javascript
  const canViewAudit = document.getElementById('newCanViewAudit').checked;
  // ... existing username/email/password/role reads stay the same ...
  body: JSON.stringify({ username, email, password, role_name: role, can_view_audit_log: canViewAudit }),
```

This requires backend support for the new field. In `api_models.py`, add the field to `CreateUserInput`:

```python
class CreateUserInput(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    role_name: Literal["superadmin", "admin", "user"] = "user"
    can_view_audit_log: bool = False
```

In `main.py`'s `create_user`, update the `INSERT INTO users` call to include the new column:

```python
        connection.execute(
            "INSERT INTO users (id, username, email, password_hash, role_name, is_active, is_first_login, can_view_audit_log) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [new_id, payload.username, payload.email, password_hash, payload.role_name, True, True, payload.can_view_audit_log],
        )
```

- [ ] **Step 5: Hide the detailed-download button for Policy Makers; add the summary download**

Modify `renderResults` (around line 913) where `btnDownload` visibility is set:

```javascript
  // --- Show download buttons if we have a run_id ---
  const btnDl = document.getElementById('btnDownload');
  const btnDlSummary = document.getElementById('btnDownloadSummary');
  if (artifacts?.run_id) {
    state.currentRunId = artifacts.run_id;
    btnDl.style.display = state.auth.role_name === 'user' ? 'none' : 'inline-flex';
    btnDlSummary.style.display = 'inline-flex';
  } else {
    btnDl.style.display = 'none';
    btnDlSummary.style.display = 'none';
  }
```

Add `downloadSummaryCSV()` right after the existing `downloadCSV()` function (around line 1417):

```javascript
async function downloadSummaryCSV() {
  if (!state.currentRunId) {
    showToast('No simulation result is available for download.', 'warning');
    return;
  }
  const url = `${API_BASE}/api/runs/${state.currentRunId}/summary.csv`;
  try {
    const res = await fetch(url, { headers: state.auth?.token ? { 'X-Auth-Token': state.auth.token } : {} });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const text = await res.text();
    const blob = new Blob([text], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `simulation_2027_summary_${state.currentRunId}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
    showToast(t('toast.csv.ok'), 'success');
  } catch (err) {
    showToast(`Failed to download summary CSV: ${err.message}`, 'error');
  }
}
```

- [ ] **Step 6: Manually verify in the browser**

Run: `python -m uvicorn main:app --reload --host 127.0.0.1 --port 8002`, open `http://127.0.0.1:8002`.

Check:
- Log in as `superadmin` → both "Pengurusan Pengguna" and "Log Audit" buttons visible; running a simulation shows both download buttons; Audit Log page lists the login and the simulation run.
- Create a new `user` (Policy Maker) account via the Admin page, log in as them → neither admin button visible; running a simulation shows only the summary download button, not the detailed one.
- Create a new `admin` (Forecasting Admin) account with the "Can View Audit Log" checkbox unchecked, log in as them → no admin button, no audit button, both download buttons visible after a run.
- Create another `admin` account with the checkbox checked, log in as them → Audit Log button visible and the page loads entries; still no "Pengurusan Pengguna" button.
- Directly call `curl -X POST http://127.0.0.1:8002/api/admin/create-user -H "Content-Type: application/json" -d "{\"username\":\"x\",\"email\":\"x@x.com\",\"password\":\"password123\",\"role_name\":\"user\"}"` with no token → confirm `401 Unauthorized` in the response.

- [ ] **Step 7: Commit**

No git repo present — skip.

---

## Self-Review Notes

- **Spec coverage:** Role mapping (Task 2), backend enforcement on all six listed endpoints (Tasks 2-4), audit log using existing + new tables (Tasks 1, 3, 4), summary report (Task 4), download-button gating (Task 5), nav gating for Admin/Audit Log (Task 5), no lever/mode restriction for Policy Maker (nothing built — matches spec's explicit "not restricted" decision), `/api/forecast/2027` backend-gated with no UI change (Task 3) — all covered.
- **Placeholder scan:** no `TBD`/`TODO` — the one soft spot (Task 4 Step 5's parenthetical about `ScenarioRequest` field names) is intentional: it tells the implementer exactly what to check (`schemas.py`) and exactly what to do with either outcome, not "figure it out later."
- **Type/name consistency:** `require_role(*roles)` returns a dependency used identically in Tasks 2-4; `session` dict keys (`username`, `role_name`, `can_view_audit_log`) are the same across all tasks; `save_run(scenario, detail, summary, subject_summary, run_by=None)` signature is defined once (Task 4) and not changed again; `write_audit_log` (Task 2) and `_write_run_log` (Task 4) are both defined once and are the only writers to their respective tables.
