# "Simulasi Saya" (My Runs) for Policy Maker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the Policy Maker (`user`) role browse their own last 20 simulation runs on a dedicated page and re-download the summary PDF for any of them, without re-configuring the sidebar.

**Architecture:** A new read-only backend endpoint lists the caller's own runs by combining the existing `simulation_run_log` table (who ran what, when) with the existing per-run `{run_id}_summary.json` file (the exact scenario parameters used). The frontend adds a new header button + page (following the existing Admin/Audit Log page pattern) that lists these runs and, on download, re-runs `/api/simulate` with the archived scenario and reuses the existing client-side PDF pipeline.

**Tech Stack:** FastAPI + DuckDB (backend), vanilla HTML/CSS/JS (frontend), no new dependencies.

## Global Constraints

- No database schema changes — `simulation_run_log` and per-run `summary.json` files already contain everything needed (see `docs/superpowers/specs/2026-07-12-policy-maker-my-runs-design.md`).
- The new endpoint is restricted to the `user` role only (`Depends(require_role("user"))`) — Superadmin/Admin get a 403, per the approved design.
- The list shows the last **20** runs, newest first, for `run_type IN ('simulate', 'agent')`, filtered to the calling user's own `run_by`.
- No CSV download button on this list — PDF only.
- No side-by-side comparison feature — out of scope for this iteration.
- Reuse the existing client-side PDF pipeline (`downloadSummaryPDF()`) as-is — do not build a server-side PDF generator.
- Every edit to `frontend/app.js`, `frontend/lang.js`, or `frontend/styles.css` must bump its cache-busting `?v=N` query string in `frontend/index.html`.
- Follow the existing XSS-safe table-building pattern (`document.createElement` + `.textContent`, never `.innerHTML` string interpolation of data) used in `loadAuditLog()`/`buildUserRow()`.

---

### Task 1: Backend — `GET /api/my-runs` endpoint

**Files:**
- Modify: `main.py`

**Interfaces:**
- Produces: `GET /api/my-runs` → `{"runs": [{"run_id": str, "run_timestamp": str, "scenario": dict}, ...]}`, where `scenario` has the same shape as `ScenarioRequest.to_dict()` (subject, negeri, ppd, kod_sekolah, kodtingkatantahun, policy_mode, policy_type, active_policies, option_ratio, teaching_hours_change_pct, teacher_capacity_change_pct, coteaching_share_pct, etc.)

- [ ] **Step 1: Add the `json` import**

`main.py` does not currently import the `json` module (it's only used inside `tools.py` today). Add it near the top, next to the other standard-library imports:

```python
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal
import duckdb
import hashlib
import hmac
import json
import secrets
```

- [ ] **Step 2: Add the new endpoint**

Add this directly after the existing `download_run_summary` endpoint (the one ending `raise HTTPException(status_code=404, detail="Run summary not found")` for `/api/runs/{run_id}/summary.csv`), so it sits alongside the other run-related endpoints:

```python
@app.get("/api/my-runs")
def get_my_runs(
    session: dict[str, Any] = Depends(require_role("user")),
) -> dict[str, Any]:
    connection = duckdb.connect(str(get_database_path()), read_only=True)
    try:
        rows = connection.execute(
            "SELECT run_id, run_timestamp FROM simulation_run_log "
            "WHERE run_by = ? AND run_type IN ('simulate', 'agent') "
            "ORDER BY run_timestamp DESC LIMIT 20",
            [session["username"]],
        ).fetchall()
    finally:
        connection.close()

    runs: list[dict[str, Any]] = []
    for run_id, run_timestamp in rows:
        scenario = _read_run_scenario(run_id)
        if scenario is None:
            continue
        runs.append({
            "run_id": run_id,
            "run_timestamp": str(run_timestamp),
            "scenario": scenario,
        })
    return {"runs": runs}
```

- [ ] **Step 3: Add the `_read_run_scenario` helper**

Add this helper function directly above `get_my_runs` (or above `download_run`, whichever reads more naturally — it's used only by `get_my_runs`). It mirrors the exact file-lookup + path-safety pattern already used by `download_run`/`download_run_summary`, but reads and parses the JSON instead of streaming the file:

```python
def _read_run_scenario(run_id: str) -> dict[str, Any] | None:
    """Reads the archived `scenario` dict from a run's summary.json, or None
    if the run_id is malformed or the file can't be found/parsed."""
    if not run_id.startswith("RUN_") or not run_id.replace("_", "").isalnum():
        return None
    for output_root in get_output_directories():
        output_root = output_root.resolve()
        file_path = (output_root / f"{run_id}_summary.json").resolve()
        if output_root in file_path.parents and file_path.exists():
            try:
                return json.loads(file_path.read_text(encoding="utf-8")).get("scenario")
            except (OSError, ValueError):
                return None
    return None
```

- [ ] **Step 4: Manually verify the endpoint**

Run the API (`python -m uvicorn main:app --reload --host 127.0.0.1 --port 8002`), log in as a `user`-role account that has run at least one simulation before, and call:

```powershell
$token = "<X-Auth-Token from login response>"
Invoke-RestMethod -Uri "http://127.0.0.1:8002/api/my-runs" -Headers @{ "X-Auth-Token" = $token }
```

Expected: a JSON object with a `runs` array, newest run first, each entry containing a `scenario` object with the fields listed above. Also verify a `superadmin` or `admin` token against the same endpoint gets a 403.

- [ ] **Step 5: Run smoke tests**

```powershell
python smoke_test.py
python api_smoke_test.py
```

Expected: both pass unchanged (this task only adds a new endpoint; nothing existing is modified). Clean up any `outputs/RUN_*` files these tests generate afterward, same as existing project convention.

---

### Task 2: Frontend — "Simulasi Saya" page and list

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/lang.js`
- Modify: `frontend/app.js`

**Interfaces:**
- Consumes: `GET /api/my-runs` from Task 1 (via the existing `apiFetch()` helper in `app.js`, which auto-attaches `X-Auth-Token`).
- Consumes: `getPolicyLabels()`, `formatSubject()`, `toTitleCase()`, `t()`, `applyLang()`, `showToast()` — all existing helpers in `frontend/app.js`.
- Produces: `goToMyRunsPage()` (global function, called from the new header button's `onclick`), `loadMyRuns()` (global function), used again by Task 3.

- [ ] **Step 1: Add the header button**

In `frontend/index.html`, immediately after the existing `auditLogBtn` button (find `<button id="auditLogBtn" ...>`), add:

```html
    <button id="myRunsBtn" class="btn btn-secondary" style="display:none; margin-right: 12px;" onclick="goToMyRunsPage()" data-i18n="nav.myruns">Simulasi Saya</button>
```

- [ ] **Step 2: Add the new page markup**

In `frontend/index.html`, immediately after the closing `</main>` of the existing `<main class="main-panel" id="auditLogPage" ...>` block (right before the `</div>` that closes `.app-body`), add:

```html
    <!-- ===================== MY RUNS PAGE (Policy Maker) ===================== -->
    <main class="main-panel" id="myRunsPage" style="display:none;">
      <div style="padding: 32px; max-width: 1100px; margin: 0 auto;">
        <button class="btn btn-outline btn-sm" onclick="goToDashboard()" style="margin-bottom: 24px;">
          <span>← Kembali ke Papan Pemuka</span>
        </button>
        <div class="admin-panel">
          <div class="result-card">
            <div class="result-card-header" data-i18n="myruns.title">Simulasi Saya</div>
            <div class="result-card-body">
              <div class="table-container">
                <table class="rec-table">
                  <thead>
                    <tr>
                      <th data-i18n="myruns.col.time">Tarikh &amp; Masa</th>
                      <th data-i18n="myruns.col.scope">Skop</th>
                      <th data-i18n="myruns.col.policy">Dasar Disimulasikan</th>
                      <th data-i18n="myruns.col.action">Tindakan</th>
                    </tr>
                  </thead>
                  <tbody id="myRunsBody"></tbody>
                </table>
                <p id="myRunsEmpty" class="hint" style="display:none; margin-top:14px;" data-i18n="myruns.empty">Belum ada simulasi dijalankan.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
```

Note: the "← Kembali ke Papan Pemuka" back button intentionally has no `data-i18n` — this matches the existing (pre-existing, not introduced by this task) Admin/Audit Log pages, which use the same hardcoded BM text regardless of UI language. Keep it consistent with those two pages rather than fixing that separately here.

- [ ] **Step 3: Add i18n keys**

In `frontend/lang.js`, in the **`bm`** block, immediately after the existing `'nav.audit': 'Log Audit',` line, add:

```javascript
    'nav.myruns': 'Simulasi Saya',
    'myruns.title': 'Simulasi Saya',
    'myruns.col.time': 'Tarikh & Masa',
    'myruns.col.scope': 'Skop',
    'myruns.col.policy': 'Dasar Disimulasikan',
    'myruns.col.action': 'Tindakan',
    'myruns.empty': 'Belum ada simulasi dijalankan.',
```

In the **`en`** block, immediately after the existing `'nav.audit': 'Audit Log',` line, add:

```javascript
    'nav.myruns': 'My Runs',
    'myruns.title': 'My Runs',
    'myruns.col.time': 'Date & Time',
    'myruns.col.scope': 'Scope',
    'myruns.col.policy': 'Policy Simulated',
    'myruns.col.action': 'Action',
    'myruns.empty': 'No simulations have been run yet.',
```

(The download button itself reuses the existing `'btn.download.summary'` key — "⬇ Muat Turun Laporan PDF" / "⬇ Download PDF Report" — no new key needed for it.)

- [ ] **Step 4: Add navigation + list-loading functions**

In `frontend/app.js`, find the existing `showAdminPanel()` function:

```javascript
function showAdminPanel() {
  const adminBtn = document.getElementById('adminBtn');
  const auditBtn = document.getElementById('auditLogBtn');
  adminBtn.style.display = state.auth.role_name === 'superadmin' ? 'inline-block' : 'none';
  const canSeeAudit = state.auth.role_name === 'superadmin'
    || (state.auth.role_name === 'admin' && state.auth.can_view_audit_log);
  auditBtn.style.display = canSeeAudit ? 'inline-block' : 'none';
}
```

Replace it with (adds the `myRunsBtn` toggle for the `user` role):

```javascript
function showAdminPanel() {
  const adminBtn = document.getElementById('adminBtn');
  const auditBtn = document.getElementById('auditLogBtn');
  const myRunsBtn = document.getElementById('myRunsBtn');
  adminBtn.style.display = state.auth.role_name === 'superadmin' ? 'inline-block' : 'none';
  const canSeeAudit = state.auth.role_name === 'superadmin'
    || (state.auth.role_name === 'admin' && state.auth.can_view_audit_log);
  auditBtn.style.display = canSeeAudit ? 'inline-block' : 'none';
  myRunsBtn.style.display = state.auth.role_name === 'user' ? 'inline-block' : 'none';
}
```

Then find the three existing page-navigation functions:

```javascript
function goToAdminPage() {
  document.getElementById('mainPanel').style.display = 'none';
  document.getElementById('auditLogPage').style.display = 'none';
  document.getElementById('adminPage').style.display = 'block';
  applyLang(); // Ensure translations are applied
  loadUserList();
}

function goToDashboard() {
  document.getElementById('adminPage').style.display = 'none';
  document.getElementById('auditLogPage').style.display = 'none';
  document.getElementById('mainPanel').style.display = 'block';
  applyLang(); // Ensure translations are applied
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
```

Replace them with (each now also hides/shows `myRunsPage`):

```javascript
function goToAdminPage() {
  document.getElementById('mainPanel').style.display = 'none';
  document.getElementById('auditLogPage').style.display = 'none';
  document.getElementById('myRunsPage').style.display = 'none';
  document.getElementById('adminPage').style.display = 'block';
  applyLang(); // Ensure translations are applied
  loadUserList();
}

function goToDashboard() {
  document.getElementById('adminPage').style.display = 'none';
  document.getElementById('auditLogPage').style.display = 'none';
  document.getElementById('myRunsPage').style.display = 'none';
  document.getElementById('mainPanel').style.display = 'block';
  applyLang(); // Ensure translations are applied
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
  document.getElementById('myRunsPage').style.display = 'none';
  document.getElementById('auditLogPage').style.display = 'block';
  applyLang();
  loadAuditLog();
}

function goToMyRunsPage() {
  if (state.auth.role_name !== 'user') {
    showToast(t('toast.no.permission'), 'error');
    return;
  }
  document.getElementById('mainPanel').style.display = 'none';
  document.getElementById('adminPage').style.display = 'none';
  document.getElementById('auditLogPage').style.display = 'none';
  document.getElementById('myRunsPage').style.display = 'block';
  applyLang();
  loadMyRuns();
}
```

- [ ] **Step 5: Add `loadMyRuns()`**

In `frontend/app.js`, directly after the existing `loadAuditLog()` function, add:

```javascript
/** Loads the current Policy Maker's own last 20 simulation runs and renders
 *  them as a table with a per-row PDF re-download button. */
async function loadMyRuns() {
  const tbody = document.getElementById('myRunsBody');
  const emptyMsg = document.getElementById('myRunsEmpty');
  tbody.innerHTML = '';
  try {
    const data = await apiFetch('/api/my-runs');
    const runs = data.runs || [];
    emptyMsg.style.display = runs.length ? 'none' : 'block';
    const policyLabels = getPolicyLabels();

    runs.forEach(run => {
      const scenario = run.scenario || {};
      const tr = document.createElement('tr');

      const tdTime = document.createElement('td');
      tdTime.textContent = run.run_timestamp || '';
      tr.appendChild(tdTime);

      const tdScope = document.createElement('td');
      const subject = scenario.subject === 'SEMUA' ? t('all.subjects') : formatSubject(scenario.subject);
      const negeri = scenario.negeri === 'SEMUA' ? t('all.states') : toTitleCase(scenario.negeri || '');
      tdScope.textContent = `${subject} / ${negeri}`;
      tr.appendChild(tdScope);

      const tdPolicy = document.createElement('td');
      const activePolicies = scenario.active_policies?.length
        ? scenario.active_policies
        : [scenario.policy_type].filter(Boolean);
      tdPolicy.textContent = activePolicies.map(value => policyLabels[value] || value).join(' + ') || '—';
      tr.appendChild(tdPolicy);

      const tdAction = document.createElement('td');
      const btn = document.createElement('button');
      btn.className = 'btn btn-teal btn-sm';
      btn.textContent = t('btn.download.summary');
      btn.addEventListener('click', () => downloadPdfForRun(scenario));
      tdAction.appendChild(btn);
      tr.appendChild(tdAction);

      tbody.appendChild(tr);
    });
  } catch (err) {
    showToast('Failed to load my runs: ' + err.message, 'error');
  }
}
```

This calls `downloadPdfForRun(scenario)`, which is implemented in Task 3 — this task will show an "undefined function" error in the browser console if tested in isolation with a real click; that's expected and resolved once Task 3 lands. The list rendering itself (table populates correctly) is independently verifiable now.

- [ ] **Step 6: Bump cache-busting versions**

In `frontend/index.html`, bump the versions for the two files touched in this task:

```html
  <link rel="stylesheet" href="styles.css?v=15" />
```
(unchanged — this task does not modify `styles.css`)

```html
<script src="lang.js?v=10"></script>
<script src="app.js?v=27"></script>
```

- [ ] **Step 7: Manually verify the list UI**

Start the API and open the frontend in a browser, logged in as a `user`-role test account that has at least one prior simulation run (use a disposable test account — never the real `superadmin`). Click "Simulasi Saya" in the header. Verify:
- The button only appears for the `user` role (log in as `admin`/`superadmin` and confirm it's hidden).
- The table lists prior runs, newest first, with correct scope and policy-label text (in both BM and EN — use the language toggle).
- With a fresh account that has never run a simulation, the empty-state message shows instead of an empty table.

---

### Task 3: Frontend — regenerate-and-download PDF flow

**Files:**
- Modify: `frontend/app.js`
- Modify: `frontend/index.html` (cache-bust bump only)

**Interfaces:**
- Consumes: `apiFetch()`, `renderResults()`, `downloadSummaryPDF()`, `showLoading()`, `showError()`, `goToDashboard()`, `t()` — all existing in `frontend/app.js`.
- Produces: `downloadPdfForRun(scenario)` (global function), called from the button built in Task 2's `loadMyRuns()`.

- [ ] **Step 1: Add `downloadPdfForRun()`**

In `frontend/app.js`, directly after the existing `runSimulation()` function, add:

```javascript
/** Re-runs an archived scenario (from the "Simulasi Saya" list) through the
 *  normal simulate → render → PDF pipeline, so a Policy Maker can get back a
 *  report for a scenario they ran earlier without re-configuring the sidebar.
 *  Switches to the dashboard first — Chart.js needs a real, visible-sized
 *  canvas to draw into, so this cannot happen invisibly in the background
 *  (see the comments on downloadSummaryPDF for the related, already-fixed
 *  cold-render failure mode this would otherwise risk repeating). */
async function downloadPdfForRun(scenario) {
  goToDashboard();
  showLoading(t('loading.sim'));

  const payload = { ...scenario, lang: (typeof getLang === 'function' ? getLang() : 'en') };

  try {
    const data = await apiFetch('/api/simulate', { method: 'POST', body: payload });
    state.currentRunId = data.artifacts?.run_id ?? null;
    renderResults(data, payload);

    // Chart.js animates new charts in (~1s by default) — wait for that to
    // finish before html2canvas captures them, otherwise the PDF can contain
    // a mid-animation frame with partially-drawn bars.
    await new Promise(resolve => setTimeout(resolve, 1200));
    await downloadSummaryPDF();
  } catch (err) {
    showLoading(null);
    showError(`Failed to regenerate report: ${err.message}`);
  }
}
```

- [ ] **Step 2: Bump the cache-busting version**

In `frontend/index.html`:

```html
<script src="app.js?v=28"></script>
```

- [ ] **Step 3: Manually verify the end-to-end download**

Using the same disposable `user`-role test account from Task 2:
1. Go to "Simulasi Saya", click "⬇ Muat Turun Laporan PDF" on any row.
2. Verify: the view switches to the dashboard, briefly shows a loading state, then the results populate (KPIs, charts, table) matching that row's scope/policy.
3. Verify: shortly after, the PDF downloads automatically (check the browser's downloads), and its Parameter/Summary/KPI/Chart pages match what's on screen.
4. Go back to "Simulasi Saya" and confirm the just-downloaded run now appears at the top of the list (expected side effect, per the design doc — re-running writes a new log entry).
5. Confirm the account's simulation count in `simulation_run_log` grew by exactly one (e.g. via a quick DuckDB query), not more — guards against the download accidentally triggering `runSimulation()` or a duplicate `/api/simulate` call.

- [ ] **Step 4: Run smoke tests**

```powershell
python smoke_test.py
python api_smoke_test.py
```

Expected: both pass unchanged. Clean up any `outputs/RUN_*` files generated by this task's manual testing and by the smoke tests, per existing project convention (do not commit generated outputs).

---

## Post-Implementation Checklist

- [ ] Re-run the full CLAUDE.md testing checklist relevant to this change: Policy Maker login, Agent Chat, single policy mode, combined policy mode, all four policy levers — since `downloadPdfForRun()` exercises the same `/api/simulate` → `renderResults()` → `downloadSummaryPDF()` path as the manual flow, confirm none of those manual flows regressed.
- [ ] Confirm Superadmin/Admin accounts still cannot see the "Simulasi Saya" button or call `/api/my-runs` directly (expect 403).
- [ ] Confirm no `.duckdb` schema changed (`git diff` / file timestamps on `data/*.duckdb` should be untouched by this feature — only new rows via the existing `simulation_run_log` insert path).
