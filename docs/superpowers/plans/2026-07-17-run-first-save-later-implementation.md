# Run First, Save Later Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a Policy Maker ("user" role) review a simulation's results before deciding to keep it, save it with a custom name via a new endpoint, and see only their named/saved runs in "Simulasi Saya" (My Runs) — without breaking the existing Audit Log's complete activity trail.

**Architecture:** `simulation_run_log` gains two columns (`run_name`, `is_saved`). The existing auto-insert on every `/api/simulate` / `/api/agent/run` call is untouched (`is_saved` defaults to FALSE), preserving Audit Log completeness. A new `POST /api/runs/save` endpoint, restricted to role `user`, updates a caller-owned row in place with a name and `is_saved = TRUE`. `GET /api/my-runs` is filtered to `is_saved = TRUE` rows only. The frontend adds a "Save Simulation" button + naming modal to the results view (role `user` only) and displays `run_name` in the My Runs table.

**Tech Stack:** FastAPI + Pydantic (backend), psycopg2 (PostgreSQL), DuckDB (historical backup file only), vanilla HTML/CSS/JavaScript (frontend), script-style smoke tests (no pytest runner in this repo).

## Global Constraints

- Projection year, 2026 supply baseline, port number, and core policy formulas are not touched by this feature (per CLAUDE.md "Things Not to Touch").
- No changes to Superadmin/Admin behavior — they keep seeing every simulation via Audit Log regardless of `is_saved`.
- No schema change to any column other than the two additive ones on `simulation_run_log` (`run_name`, `is_saved`).
- Never commit `.env`, never print secrets, never touch `models/random_forest_teacher_demand.pk1` or `data/*.duckdb` row data (schema-only ALTER is in scope per explicit user approval — no deletes, no data migration).
- Run `python smoke_test.py` and `python api_smoke_test.py` before considering any task complete, per CLAUDE.md's Testing Checklist.

---

### Task 1: Database schema — `run_name` and `is_saved` columns

**Files:**
- Create: `migrate_run_name_schema.py` (PostgreSQL — operational database)
- Create: `migrate_run_name_schema_duckdb.py` (DuckDB backup file — schema-only, historical record)
- Modify: `migrate_duckdb_to_postgres.py:39-48` (the `simulation_run_log` `CREATE TABLE` statement, so a from-scratch replay produces the current schema)

**Interfaces:**
- Consumes: `db.get_connection(read_only: bool = True)` (existing, from `db.py`), `config.get_database_path() -> Path` (existing, from `config.py`).
- Produces: `simulation_run_log.run_name VARCHAR` (nullable) and `simulation_run_log.is_saved BOOLEAN DEFAULT FALSE`, present in both PostgreSQL and the `.duckdb` backup file. Task 2 and Task 3 depend on these columns existing in PostgreSQL.

- [ ] **Step 1: Write the PostgreSQL migration script**

Create `migrate_run_name_schema.py`:

```python
"""One-off migration: adds run_name and is_saved columns to simulation_run_log.
Additive only — does not modify any existing column."""

import db

con = db.get_connection(read_only=False)
cursor = con.cursor()

cursor.execute("ALTER TABLE simulation_run_log ADD COLUMN IF NOT EXISTS run_name VARCHAR")
cursor.execute("ALTER TABLE simulation_run_log ADD COLUMN IF NOT EXISTS is_saved BOOLEAN DEFAULT FALSE")
con.commit()

cursor.execute(
    "SELECT column_name, data_type FROM information_schema.columns "
    "WHERE table_schema = 'public' AND table_name = 'simulation_run_log' ORDER BY ordinal_position"
)
print(cursor.fetchall())
cursor.close()
con.close()
```

- [ ] **Step 2: Run it against PostgreSQL and verify the columns exist**

Run: `python migrate_run_name_schema.py`
Expected output includes both new columns, e.g.:
```
[('run_id', 'character varying'), ('scenario_id', 'character varying'), ('run_timestamp', 'timestamp without time zone'), ('run_by', 'character varying'), ('run_type', 'character varying'), ('target_scope', 'character varying'), ('notes', 'character varying'), ('run_name', 'character varying'), ('is_saved', 'boolean')]
```

- [ ] **Step 3: Write the DuckDB backup-file migration script**

Create `migrate_run_name_schema_duckdb.py`:

```python
"""One-off migration: adds run_name and is_saved columns to the historical
DuckDB backup file's simulation_run_log table, keeping its schema in sync
with PostgreSQL even though the running application no longer queries this
file at runtime (PostgreSQL is the sole operational database)."""

import duckdb

from config import get_database_path

con = duckdb.connect(str(get_database_path()), read_only=False)
con.execute("ALTER TABLE simulation_run_log ADD COLUMN IF NOT EXISTS run_name VARCHAR")
con.execute("ALTER TABLE simulation_run_log ADD COLUMN IF NOT EXISTS is_saved BOOLEAN DEFAULT FALSE")

print(con.execute("DESCRIBE simulation_run_log").fetchall())
con.close()
```

- [ ] **Step 4: Run it against the DuckDB backup file and verify**

Run: `python migrate_run_name_schema_duckdb.py`
Expected: output includes rows for `run_name` (VARCHAR) and `is_saved` (BOOLEAN) alongside the existing columns.

- [ ] **Step 5: Update the from-scratch migration script's schema statement**

In `migrate_duckdb_to_postgres.py`, change lines 39-48 from:

```python
    """
    CREATE TABLE IF NOT EXISTS simulation_run_log (
        run_id VARCHAR PRIMARY KEY,
        scenario_id VARCHAR,
        run_timestamp TIMESTAMP,
        run_by VARCHAR,
        run_type VARCHAR,
        target_scope VARCHAR,
        notes VARCHAR
    )
    """,
```

to:

```python
    """
    CREATE TABLE IF NOT EXISTS simulation_run_log (
        run_id VARCHAR PRIMARY KEY,
        scenario_id VARCHAR,
        run_timestamp TIMESTAMP,
        run_by VARCHAR,
        run_type VARCHAR,
        target_scope VARCHAR,
        notes VARCHAR,
        run_name VARCHAR,
        is_saved BOOLEAN NOT NULL DEFAULT FALSE
    )
    """,
```

- [ ] **Step 6: Commit**

```bash
git add migrate_run_name_schema.py migrate_run_name_schema_duckdb.py migrate_duckdb_to_postgres.py
git commit -m "feat: add run_name and is_saved columns to simulation_run_log"
```

---

### Task 2: Backend — `POST /api/runs/save` endpoint

**Files:**
- Modify: `api_models.py` (add `SaveRunInput`)
- Modify: `main.py:22-29` (import `SaveRunInput`), and add the new endpoint after `_read_run_scenario` (currently `main.py:696-709`, right before the existing `GET /api/my-runs` at `main.py:712`)
- Test: `run_save_smoke_test.py` (new file, created in this task; extended further in Task 7)

**Interfaces:**
- Consumes: `db.get_connection(read_only: bool)` (existing), `require_role(*roles: str)` (existing, `main.py:83`), `SESSIONS` session dict shape `{"username": str, "role_name": str, ...}` (existing).
- Produces: `POST /api/runs/save` accepting `{run_id: str, run_name: str}`, returning `{"run_id": str, "run_name": str}` on success. Task 5 (frontend) calls this endpoint with this exact request/response shape.

- [ ] **Step 1: Add the `SaveRunInput` request model**

In `api_models.py`, after `ForecastInput` (end of file), add:

```python
class SaveRunInput(BaseModel):
    run_id: str = Field(min_length=1, max_length=80)
    run_name: str = Field(default="", max_length=200)
```

- [ ] **Step 2: Write the failing smoke test**

Create `run_save_smoke_test.py`:

```python
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

admin_login = client.post("/api/auth/login", json={"username": "superadmin", "password": "SuperAdmin123!"})
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

# It should NOT show up in My Runs yet — not saved.
my_runs_before = client.get("/api/my-runs", headers={"X-Auth-Token": user_token})
assert my_runs_before.status_code == 200, my_runs_before.text
assert run_id not in [r["run_id"] for r in my_runs_before.json()["runs"]]

print("run_save_smoke_test: initial checks passed")
```

- [ ] **Step 3: Run it to verify it fails (endpoint doesn't exist yet, no crash expected at this point)**

Run: `python run_save_smoke_test.py`
Expected: `run_save_smoke_test: initial checks passed` prints successfully — this step only exercises existing endpoints, confirming test setup (user creation, login, first simulation) works before the new endpoint is added. This is the "pre-feature" baseline.

- [ ] **Step 4: Add the `POST /api/runs/save` endpoint**

In `main.py`, add `SaveRunInput` to the import block at lines 22-29 (alongside the other `api_models` imports):

```python
from api_models import (
    AgentQuestionInput,
    ChangePasswordInput,
    CreateUserInput,
    ForecastInput,
    SaveRunInput,
    ScenarioInput,
)
```

Then, in `main.py`, insert the new endpoint immediately before the existing `GET /api/my-runs` (currently at `main.py:712`):

```python
@app.post("/api/runs/save")
def save_run(
    payload: SaveRunInput,
    session: dict[str, Any] = Depends(require_role("user")),
) -> dict[str, Any]:
    if not payload.run_id.startswith("RUN_") or not payload.run_id.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid run_id")

    connection = db.get_connection(read_only=False)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT run_timestamp FROM simulation_run_log WHERE run_id = %s AND run_by = %s",
                [payload.run_id, session["username"]],
            )
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Run not found")
            run_timestamp = row[0]

            run_name = payload.run_name.strip()
            if not run_name:
                run_name = f"Simulation - {run_timestamp:%Y-%m-%d %H:%M}"

            cursor.execute(
                "UPDATE simulation_run_log SET run_name = %s, is_saved = TRUE "
                "WHERE run_id = %s AND run_by = %s",
                [run_name, payload.run_id, session["username"]],
            )
        connection.commit()
    finally:
        connection.close()

    return {"run_id": payload.run_id, "run_name": run_name}
```

- [ ] **Step 5: Extend the smoke test to cover the save endpoint**

Append to `run_save_smoke_test.py`:

```python
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
```

- [ ] **Step 6: Run the smoke test to verify it passes**

Run: `python run_save_smoke_test.py`
Expected: `run_save_smoke_test: initial checks passed` then `run_save_smoke_test: save endpoint checks passed`, no assertion errors.

- [ ] **Step 7: Commit**

```bash
git add api_models.py main.py run_save_smoke_test.py
git commit -m "feat: add POST /api/runs/save endpoint for naming and saving simulations"
```

---

### Task 3: Backend — filter `GET /api/my-runs` to saved runs only

**Files:**
- Modify: `main.py:712-739` (the `get_my_runs` handler)
- Test: `run_save_smoke_test.py` (extend from Task 2)

**Interfaces:**
- Consumes: `SaveRunInput`/`POST /api/runs/save` from Task 2 (must exist and work for this task's test to pass).
- Produces: `GET /api/my-runs` response shape `{"runs": [{"run_id": str, "run_timestamp": str, "run_name": str | None, "scenario": dict}, ...]}` — the `run_name` key is new; everything else is unchanged. Task 6 (frontend My Runs table) depends on this exact key.

- [ ] **Step 1: Extend the smoke test first (failing)**

Append to `run_save_smoke_test.py`:

```python
# --- My Runs now shows only the saved run, with its custom name ---
my_runs_after = client.get("/api/my-runs", headers={"X-Auth-Token": user_token})
assert my_runs_after.status_code == 200, my_runs_after.text
saved_run_ids = [r["run_id"] for r in my_runs_after.json()["runs"]]
assert run_id in saved_run_ids
assert run_id_2 in saved_run_ids
saved_entry = next(r for r in my_runs_after.json()["runs"] if r["run_id"] == run_id)
assert saved_entry["run_name"] == "My Johor Science Scenario"

print("run_save_smoke_test: my-runs filtering checks passed")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python run_save_smoke_test.py`
Expected: `AssertionError` on `assert saved_entry["run_name"] == "My Johor Science Scenario"` (or a `KeyError`/`StopIteration` if the endpoint hasn't been modified yet) — `run_name` isn't selected/returned yet.

- [ ] **Step 3: Update the `GET /api/my-runs` handler**

In `main.py`, replace the body of `get_my_runs` (currently `main.py:712-739`):

```python
@app.get("/api/my-runs")
def get_my_runs(
    session: dict[str, Any] = Depends(require_role("user")),
) -> dict[str, Any]:
    connection = db.get_connection(read_only=True)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT run_id, run_timestamp, run_name FROM simulation_run_log "
                "WHERE run_by = %s AND run_type IN ('simulate', 'agent') AND is_saved = TRUE "
                "ORDER BY run_timestamp DESC LIMIT 20",
                [session["username"]],
            )
            rows = cursor.fetchall()
    finally:
        connection.close()

    runs: list[dict[str, Any]] = []
    for run_id, run_timestamp, run_name in rows:
        scenario = _read_run_scenario(run_id)
        if scenario is None:
            continue
        runs.append({
            "run_id": run_id,
            "run_timestamp": str(run_timestamp),
            "run_name": run_name,
            "scenario": scenario,
        })
    return {"runs": runs}
```

- [ ] **Step 4: Run the smoke test to verify it passes**

Run: `python run_save_smoke_test.py`
Expected: all three print lines appear, no assertion errors.

- [ ] **Step 5: Commit**

```bash
git add main.py run_save_smoke_test.py
git commit -m "feat: filter GET /api/my-runs to saved runs and include run_name"
```

---

### Task 4: Frontend — Save Simulation button, naming modal, and lang.js keys

**Files:**
- Modify: `frontend/index.html` (add button in the results `table-footer` block, add modal markup)
- Modify: `frontend/styles.css` (add modal overlay/box styles)
- Modify: `frontend/lang.js` (add new i18n keys in both the `bm` block, around `lang.js:166-168`, and the `en` block, around `lang.js:503-505`)

**Interfaces:**
- Consumes: existing `.btn`, `.btn-outline`, `.form-control`, `.form-error` CSS classes; existing `data-i18n` / `t()` i18n convention (see `lang.js`).
- Produces: DOM elements `#btnSaveSimulation` (button), `#saveSimModal` (modal overlay), `#saveSimNameInput` (text input), `#saveSimConfirmBtn`, `#saveSimCancelBtn` — Task 5's JavaScript wires these ids up.

- [ ] **Step 1: Add the "Save Simulation" button to the results table footer**

In `frontend/index.html`, in the `table-footer` div (currently `index.html:510-524`), add a new button after `btnDownloadSummaryCsv`:

```html
                <button class="btn btn-outline btn-sm" id="btnSaveSimulation" onclick="openSaveSimulationModal()"
                  style="display:none;" data-i18n="btn.save.simulation">
                  💾 Save Simulation
                </button>
```

- [ ] **Step 2: Add the naming modal markup**

In `frontend/index.html`, immediately before the closing `</body>` tag (find it with a search for `</body>`), add:

```html
    <!-- ===================== SAVE SIMULATION MODAL ===================== -->
    <div class="modal-overlay" id="saveSimModal" style="display:none;">
      <div class="modal-box">
        <h3 data-i18n="modal.save.title">Save Simulation</h3>
        <p class="hint" data-i18n="modal.save.hint">Give this simulation a name so you can find it later in My Runs.</p>
        <label for="saveSimNameInput" data-i18n="modal.save.label">Simulation Name</label>
        <input id="saveSimNameInput" class="form-control" type="text" maxlength="200"
          data-i18n-placeholder="modal.save.placeholder" placeholder="e.g. Johor Science 70% option ratio" />
        <div class="modal-actions">
          <button class="btn btn-outline btn-sm" id="saveSimCancelBtn" onclick="closeSaveSimulationModal()"
            data-i18n="modal.save.cancel">Cancel</button>
          <button class="btn btn-primary btn-sm" id="saveSimConfirmBtn" onclick="submitSaveSimulation()"
            data-i18n="modal.save.confirm">Save</button>
        </div>
      </div>
    </div>
```

- [ ] **Step 3: Add modal CSS**

In `frontend/styles.css`, after the `.loading-overlay` rules (currently ending around `styles.css:963`), add:

```css
/* ===== SAVE SIMULATION MODAL ===== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(6,10,20,0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}
.modal-box {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
  width: 100%;
  max-width: 380px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.modal-box h3 { margin: 0; font-size: 15px; color: var(--text); }
.modal-box .hint { font-size: 12px; color: var(--text-muted); margin: 0 0 4px; }
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}
```

- [ ] **Step 4: Add the i18n keys**

In `frontend/lang.js`, in the `bm` block, after `'btn.download.summary.csv': '⬇ Muat Turun Ringkasan (CSV)',` (currently `lang.js:168`), add:

```js
    'btn.save.simulation': '💾 Simpan Simulasi',
    'btn.save.saved': '✅ Disimpan',
    'modal.save.title': 'Simpan Simulasi',
    'modal.save.hint': 'Namakan simulasi ini supaya anda boleh menjumpainya kembali di Simulasi Saya.',
    'modal.save.label': 'Nama Simulasi',
    'modal.save.placeholder': 'cth. Johor Sains nisbah opsyen 70%',
    'modal.save.cancel': 'Batal',
    'modal.save.confirm': 'Simpan',
    'toast.save.ok': 'Simulasi berjaya disimpan.',
    'myruns.col.name': 'Nama Simulasi',
```

In the `en` block, after `'btn.download.summary.csv': '⬇ Download Summary (CSV)',` (currently `lang.js:505`), add:

```js
    'btn.save.simulation': '💾 Save Simulation',
    'btn.save.saved': '✅ Saved',
    'modal.save.title': 'Save Simulation',
    'modal.save.hint': 'Give this simulation a name so you can find it later in My Runs.',
    'modal.save.label': 'Simulation Name',
    'modal.save.placeholder': 'e.g. Johor Science 70% option ratio',
    'modal.save.cancel': 'Cancel',
    'modal.save.confirm': 'Save',
    'toast.save.ok': 'Simulation saved successfully.',
    'myruns.col.name': 'Simulation Name',
```

- [ ] **Step 5: Manually verify the markup renders**

Start the app (`run_api.bat` or `python -m uvicorn main:app --reload --host 127.0.0.1 --port 8002`), log in as a `user`-role account, run a simulation, and confirm the "Save Simulation" button and modal markup exist in the DOM (button will still be hidden/inert until Task 5 wires the JS — this step only confirms no HTML/CSS errors break page load).

- [ ] **Step 6: Commit**

```bash
git add frontend/index.html frontend/styles.css frontend/lang.js
git commit -m "feat: add Save Simulation button and naming modal markup"
```

---

### Task 5: Frontend — wire up the save flow in `app.js`

**Files:**
- Modify: `frontend/app.js` (add modal open/close/submit functions; show/reset the Save button inside `renderResults`)

**Interfaces:**
- Consumes: `#btnSaveSimulation`, `#saveSimModal`, `#saveSimNameInput`, `#saveSimConfirmBtn`, `#saveSimCancelBtn` (from Task 4); `apiFetch(path, options)` (existing, `app.js:2192`); `showToast(message, type)` (existing, `app.js:2111`); `t(key)` (existing i18n lookup); `state.currentRunId`, `state.auth.role_name` (existing, `app.js:608` / auth state); `POST /api/runs/save` (from Task 2).
- Produces: `openSaveSimulationModal()`, `closeSaveSimulationModal()`, `submitSaveSimulation()` — no other task depends on these being called from elsewhere; they're wired directly via the `onclick` attributes added in Task 4.

- [ ] **Step 1: Add the Save button visibility/reset logic to `renderResults`**

In `frontend/app.js`, in `renderResults` (currently `app.js:1272-1285`), extend the existing download-buttons block:

```javascript
  // --- Show download buttons if we have a run_id ---
  const btnDl = document.getElementById('btnDownload');
  const btnDlSummary = document.getElementById('btnDownloadSummary');
  const btnDlSummaryCsv = document.getElementById('btnDownloadSummaryCsv');
  const btnSave = document.getElementById('btnSaveSimulation');
  if (artifacts?.run_id) {
    state.currentRunId = artifacts.run_id;
    btnDl.style.display = state.auth.role_name === 'user' ? 'none' : 'inline-flex';
    btnDlSummary.style.display = 'inline-flex';
    btnDlSummaryCsv.style.display = 'inline-flex';
    btnSave.style.display = state.auth.role_name === 'user' ? 'inline-flex' : 'none';
    btnSave.disabled = false;
    btnSave.textContent = t('btn.save.simulation');
  } else {
    btnDl.style.display = 'none';
    btnDlSummary.style.display = 'none';
    btnDlSummaryCsv.style.display = 'none';
    btnSave.style.display = 'none';
  }
```

- [ ] **Step 2: Add the modal open/close/submit functions**

In `frontend/app.js`, after `downloadSummaryPDF` (find its closing brace — currently ends before the "TOAST" section around `app.js:2104`), add:

```javascript
// ============================================================
// SAVE SIMULATION — POST /api/runs/save
// ============================================================

/** Opens the naming modal for the currently displayed simulation run. */
function openSaveSimulationModal() {
  if (!state.currentRunId) return;
  document.getElementById('saveSimNameInput').value = '';
  document.getElementById('saveSimModal').style.display = 'flex';
  document.getElementById('saveSimNameInput').focus();
}

/** Closes the naming modal without saving. */
function closeSaveSimulationModal() {
  document.getElementById('saveSimModal').style.display = 'none';
}

/** Submits the run_id + user-entered name to POST /api/runs/save. */
async function submitSaveSimulation() {
  const runId = state.currentRunId;
  const runName = document.getElementById('saveSimNameInput').value.trim();
  const confirmBtn = document.getElementById('saveSimConfirmBtn');

  confirmBtn.disabled = true;
  try {
    await apiFetch('/api/runs/save', { method: 'POST', body: { run_id: runId, run_name: runName } });
    closeSaveSimulationModal();
    showToast(t('toast.save.ok'), 'success');

    const btnSave = document.getElementById('btnSaveSimulation');
    btnSave.disabled = true;
    btnSave.textContent = t('btn.save.saved');
  } catch (err) {
    showToast(`Save failed: ${err.message}`, 'error');
  } finally {
    confirmBtn.disabled = false;
  }
}
```

- [ ] **Step 3: Manually verify the end-to-end save flow**

With the app running, log in as a Policy Maker (`user` role), run a simulation, click "Save Simulation", enter a name, submit, and confirm: a success toast appears, the button becomes disabled and shows "Saved", and — per Task 3 — the run now appears in the "My Runs" page. Also verify: leaving the name blank still saves (with a fallback name), and running a brand-new simulation resets the button back to its enabled "Save Simulation" state.

- [ ] **Step 4: Commit**

```bash
git add frontend/app.js
git commit -m "feat: wire up Save Simulation modal and API call"
```

---

### Task 6: Frontend — display `run_name` in the My Runs table

**Files:**
- Modify: `frontend/index.html:646-651` (add a table header column)
- Modify: `frontend/app.js` (the `loadMyRuns` row-building loop, currently starting at `app.js:289`)

**Interfaces:**
- Consumes: `run_name` field from `GET /api/my-runs` (Task 3).
- Produces: no new interface — this is a leaf/display-only task.

- [ ] **Step 1: Add the table header column**

In `frontend/index.html`, in the My Runs table header (currently `index.html:647-652`), add a new first column:

```html
                    <thead>
                      <tr>
                        <th data-i18n="myruns.col.name">Nama Simulasi</th>
                        <th data-i18n="myruns.col.time">Tarikh &amp; Masa</th>
                        <th data-i18n="myruns.col.scope">Skop</th>
                        <th data-i18n="myruns.col.policy">Dasar Disimulasikan</th>
                        <th data-i18n="myruns.col.action">Tindakan</th>
                      </tr>
                    </thead>
```

(`myruns.col.name` was already added to `lang.js` in Task 4, Step 4.)

- [ ] **Step 2: Render the `run_name` cell**

In `frontend/app.js`, in `loadMyRuns` (`app.js:299` onward), add a name cell as the first cell of each row, immediately before the existing `tdTime` cell:

```javascript
    runs.forEach(run => {
      const scenario = run.scenario || {};
      const tr = document.createElement('tr');

      const tdName = document.createElement('td');
      tdName.textContent = run.run_name || '';
      tr.appendChild(tdName);

      const tdTime = document.createElement('td');
      tdTime.textContent = run.run_timestamp || '';
      tr.appendChild(tdTime);
```

(The rest of the existing loop — `tdScope`, `tdPolicy`, and the action button cell — is unchanged.)

- [ ] **Step 3: Manually verify**

Reload the My Runs page as a Policy Maker with at least one saved run (from Task 5's manual test) and confirm the "Simulation Name" column shows the name entered earlier, as the first column.

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html frontend/app.js
git commit -m "feat: show run_name column in My Runs table"
```

---

### Task 7: Full verification run

**Files:** none (verification only)

**Interfaces:** none.

- [ ] **Step 1: Run the full existing smoke test suite**

Run: `python smoke_test.py`
Expected: passes with no assertion errors (unrelated to this feature — confirms nothing was broken).

Run: `python api_smoke_test.py`
Expected: passes with no assertion errors — in particular, confirms `/api/simulate` and `/api/agent/run` still work exactly as before for superadmin (auto-logging unchanged).

- [ ] **Step 2: Run the new feature-specific smoke test**

Run: `python run_save_smoke_test.py`
Expected: all three print lines (`initial checks passed`, `save endpoint checks passed`, `my-runs filtering checks passed`) appear, no assertion errors.

- [ ] **Step 3: Run the RBAC and user-management smoke tests to confirm no regressions**

Run: `python rbac_smoke_test.py`
Run: `python user_management_smoke_test.py`
Expected: both pass — confirms the `require_role("user")` gate on the new endpoint and the unrelated RBAC/user-management features still behave correctly.

- [ ] **Step 4: Manual checklist (per CLAUDE.md Testing Checklist)**

As a Policy Maker (`user` role): run a single-policy simulation, confirm no auto-save into My Runs; save it with a name; run a combined-policy simulation via Agent Chat, save it with a blank name and confirm the fallback name; confirm CSV/PDF downloads still work; confirm My Runs shows both saved runs with correct names, and does not show any unsaved run. As Superadmin/Admin: run a simulation, confirm the Audit Log still shows it (auto-logged, regardless of `is_saved`), and confirm neither role sees a "Save Simulation" button.

- [ ] **Step 5: Commit (only if Step 4 surfaced fixes — otherwise this task produces no diff)**

```bash
git add -A
git commit -m "test: verify run-first-save-later workflow end-to-end"
```
