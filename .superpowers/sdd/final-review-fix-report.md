# Final Review Fix Report — Run First, Save Later (Minor Findings)

## Finding 1: Save-failure toast not i18n'd

- Added `toast.save.fail` key to both `bm` and `en` blocks in `frontend/lang.js`, right next to the existing `toast.save.ok` key:
  - `bm`: `'toast.save.fail': 'Simpan simulasi gagal:',`
  - `en`: `'toast.save.fail': 'Save failed:',`
- Updated the catch block in `submitSaveSimulation` (`frontend/app.js`) from a hardcoded English string to `showToast(\`${t('toast.save.fail')} ${err.message}\`, 'error');`

## Finding 2: Test never asserted an unsaved run is excluded from My Runs

- Added a new section at the end of `run_save_smoke_test.py`: runs a third simulation for `rfsl_test_user` that is deliberately never saved, then asserts its `run_id` is absent from `GET /api/my-runs`. This closes the gap where deleting `AND is_saved = TRUE` from the `/api/my-runs` query in `main.py` would previously have gone undetected.

## Test Results

- `python run_save_smoke_test.py` — all checkpoints passed, including the new "unsaved-run-excluded" check.
- `python smoke_test.py` — passed (health check, summary, explanation, artifacts all generated as expected).
- `python api_smoke_test.py` — failed only on `assert agent.json()["ai_usage"]["scenario_interpreted_by_ai"] is True` near the end. This is the known pre-existing Groq-rate-limit flake called out in the task instructions as expected/unrelated to this change — not something to fix here.

## Files Changed

- `frontend/app.js`
- `frontend/lang.js`
- `run_save_smoke_test.py`

## Concerns

None. Both findings were narrow, isolated fixes; no other code paths touched.
