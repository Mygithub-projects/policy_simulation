# Task 5 Report: Frontend — wire up the save flow in app.js

## What was implemented

1. Extended the button-visibility block in `renderResults` (frontend/app.js, was lines 1272-1285) to add a `btnSave` element lookup and show/reset logic:
   - On `artifacts?.run_id` present: shown (`inline-flex`) only for `state.auth.role_name === 'user'`, re-enabled, and text reset to `t('btn.save.simulation')` every render (so a fresh simulation always gets a fresh clickable button).
   - On no run_id: hidden.

2. Added three new functions after `downloadSummaryPDF` (before the "UI HELPERS" section):
   - `openSaveSimulationModal()` — guards on `state.currentRunId`, clears the name input, shows the modal (`display: flex`), focuses the input.
   - `closeSaveSimulationModal()` — hides the modal.
   - `submitSaveSimulation()` — disables the confirm button, POSTs `{run_id: state.currentRunId, run_name: <trimmed input>}` to `/api/runs/save` via `apiFetch`, on success closes the modal, shows a success toast (`toast.save.ok`), and sets the Save button to disabled/"Saved" (`btn.save.saved`); on failure shows an error toast with the error message; re-enables the confirm button in `finally`.

## Verification of DOM ids and backend contract

- DOM ids confirmed via grep in `frontend/index.html`: `btnSaveSimulation` (line 524, `onclick="openSaveSimulationModal()"`), `saveSimModal` (line 744), `saveSimNameInput` (line 748-749), `saveSimCancelBtn` (line 752, `onclick="closeSaveSimulationModal()"`), `saveSimConfirmBtn` (line 754, `onclick="submitSaveSimulation()"`). All match the function names exactly.
- Backend contract confirmed by reading `main.py` lines 713-746: `POST /api/runs/save` accepts `SaveRunInput` and returns `{"run_id": payload.run_id, "run_name": run_name}` (line 746). Request body fields (`SaveRunInput` in `api_models.py`) are `run_id` and `run_name`. This matches exactly what `submitSaveSimulation` sends and the shape it expects back (though the response body isn't consumed further — only success/failure matters for the UI).
- Confirmed `apiFetch` (app.js, "UTILITY HELPERS" section, ~line 2236) JSON-serializes `options.body` and attaches `X-Auth-Token`, and throws on non-2xx with `errData.detail` — consistent with the brief's description and with how `submitSaveSimulation`'s catch block uses `err.message`.
- Confirmed i18n keys `btn.save.simulation`, `btn.save.saved`, `toast.save.ok` already exist in `frontend/lang.js` (both `ms` and `en` locales, lines 169-177 and 516-524).

## Test results

- `python smoke_test.py` — passed (backend workflow smoke test completed, produced artifacts/run_id as expected).
- `python api_smoke_test.py` — passed ("API smoke test passed" printed; health check, simulation, co-teaching, combined-policy, and agent-scenario checks all completed without error).

Both were run with the specified venv Python interpreter. No frontend-affecting regressions expected since these tests don't touch `frontend/`.

## Files changed

- `frontend/app.js` — extended `renderResults` button-visibility block; added `openSaveSimulationModal`, `closeSaveSimulationModal`, `submitSaveSimulation`.

## Self-review findings

- Function names match `onclick` attributes exactly: `openSaveSimulationModal()`, `closeSaveSimulationModal()`, `submitSaveSimulation()` — confirmed by grep against index.html.
- Save button resets to enabled/"Save Simulation" at the top of every `renderResults` call with a run_id, and only flips to disabled/"Saved" after a real successful `apiFetch` call to `/api/runs/save` resolves without throwing.
- Save button is hidden entirely (`display: none`) for any role other than `'user'`, and hidden when there's no run_id at all — Superadmin/Admin behavior unaffected.
- `submitSaveSimulation` sends exactly `{run_id, run_name}` and the endpoint returns exactly `{run_id, run_name}`, matching Task 2's actual `main.py` implementation, not just the brief's paraphrase.
- No other files touched (index.html, styles.css, lang.js untouched, as instructed).

## Issues or concerns

None. No manual browser verification was possible in this environment (no browser tooling), so Step 3 of the brief (end-to-end manual click-through) was not performed — this matches the task's own acknowledgment that verification here is code review only, since there's no way to run a browser in this environment.
