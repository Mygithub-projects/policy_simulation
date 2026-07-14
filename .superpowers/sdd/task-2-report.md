# Task 2 Report — Frontend "Simulasi Saya" page and list

## Changes made (verbatim from plan)

### `frontend/index.html`
- Added `myRunsBtn` header button immediately after `auditLogBtn` (around line 38-39).
- Added new `<main id="myRunsPage">` page block immediately after the closing `</main>` of `auditLogPage`, before the `.app-body` closing `</div>` (around line 508-538).
- Bumped `lang.js?v=9` -> `?v=10` and `app.js?v=26` -> `?v=27` (final line block, near end of file). `styles.css?v=15` left untouched, as required.

### `frontend/lang.js`
- Added 7 new i18n keys (`nav.myruns`, `myruns.title`, `myruns.col.time`, `myruns.col.scope`, `myruns.col.policy`, `myruns.col.action`, `myruns.empty`) to the `bm` block right after `'nav.audit': 'Log Audit',` (around line 151-158).
- Added the same 7 keys (English values) to the `en` block right after `'nav.audit': 'Audit Log',` (around line 480-487).

### `frontend/app.js`
- Replaced `showAdminPanel()` (around line 211) to add the `myRunsBtn` element lookup and toggle for `role_name === 'user'`.
- Replaced `goToAdminPage()`, `goToDashboard()`, `goToAuditLogPage()` to each additionally hide `myRunsPage`.
- Added new `goToMyRunsPage()` function directly after `goToAuditLogPage()`.
- Added new `loadMyRuns()` function directly after the existing `loadAuditLog()` function (previously ending around line 267). It builds table rows via `document.createElement`/`.textContent` (XSS-safe, matching existing pattern) and wires each row's download button to `downloadPdfForRun(scenario)`, which is intentionally not yet defined — Task 3 will add it.

No changes were made to `main.py`, `.env`, `data/*.duckdb`, `models/*.pk1`, or `frontend/styles.css`.

## Verification performed
1. `python -c "import main"` — succeeded (backend untouched, sanity confirmed).
2. `node --check frontend/app.js` and `node --check frontend/lang.js` — both passed (syntactically valid JS).
3. Read the full `frontend/app.js` region around the five edited/added functions (lines ~205-372 post-edit) to confirm only the plan's intended functions were touched, and that surrounding functions (`runLogout`, `onNewRoleChange`, `handleCreateUser`, etc.) are unchanged.
4. Grepped all three files for the new identifiers (`myRunsBtn`, `myRunsPage`, `nav.myruns`, `myruns.*`, `goToMyRunsPage`, `loadMyRuns`, `downloadPdfForRun`) — counts matched expectations (14 lang.js occurrences = 7 keys x 2 language blocks; button/page markup and all 5 app.js functions present).
5. Did not start a live browser/server session or run Playwright — not required for this task per instructions; full manual UI verification is deferred to after Task 3 per the plan.
6. Did not touch or delete anything under `outputs/`.

## Concerns
- As expected/documented in the plan, `loadMyRuns()`'s per-row download button calls `downloadPdfForRun(scenario)`, which does not exist yet (added in Task 3). This will produce a browser console error only if a user actually clicks the button before Task 3 lands — not an issue for this task's scope.
- No automated frontend test suite exists in this project, so verification relied on static syntax checks (`node --check`) and careful visual diff review rather than a live DOM/browser test, consistent with the instructions for this task.

Status: DONE
