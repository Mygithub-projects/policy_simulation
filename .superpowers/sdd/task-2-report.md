# Task 2 Report — POST /api/runs/save

## Status: DONE

## Resolution of prior blockers

The requester confirmed two resolutions:

1. **Superadmin password**: use `P@ssword.123` (matching `api_smoke_test.py`'s convention)
   instead of the brief's `SuperAdmin123!`. `run_save_smoke_test.py` already used this
   corrected password.
2. **"Not yet in My Runs" assertion**: this depended on Task 3's `is_saved` filter on
   `GET /api/my-runs`, which is not in this worktree. Per instruction, that assertion
   block was removed entirely from the baseline test step. `GET /api/my-runs` was left
   untouched, as required (still out of scope for this task).

## What was implemented

- `api_models.py`: added `SaveRunInput` model (after `ForecastInput`), exactly as
  specified in the brief.
- `main.py`: added `SaveRunInput` to the `api_models` import block (lines 22-29), and
  added the `POST /api/runs/save` endpoint immediately before `GET /api/my-runs`. The
  endpoint:
  - Validates `run_id` shape (`RUN_` prefix, alphanumeric-plus-underscore) → 400 if invalid.
  - Looks up the run by `(run_id, run_by=session["username"])` → 404 if not found or not
    owned by the caller.
  - Falls back to a generated name (`Simulation - {run_timestamp:%Y-%m-%d %H:%M}`) if
    `run_name` is blank/whitespace after stripping.
  - Sets `run_name` and `is_saved = TRUE` on `simulation_run_log`, commits, and returns
    `{"run_id": ..., "run_name": ...}`.
  - Gated by `Depends(require_role("user"))`, consistent with the rest of the
    Policy-Maker-facing endpoints in this feature.
- `run_save_smoke_test.py`: created per brief Step 2 (with the `my_runs_before` block
  removed per resolution above), then extended per brief Step 5 with:
  - Save with a custom name.
  - Save with a blank name falls back to a generated name.
  - Cannot save another user's run_id (404).
  - Malformed run_id is rejected (400).

## Tests run

- `python run_save_smoke_test.py` — PASS
  (`run_save_smoke_test: initial checks passed`, then
  `run_save_smoke_test: save endpoint checks passed`).
- `python smoke_test.py` — PASS, no regressions.
- `python api_smoke_test.py` — PASS, no regressions.

## Self-review checklist

- [x] `SaveRunInput` matches brief exactly (`run_id` min_length=1/max_length=80,
      `run_name` default="" max_length=200).
- [x] Endpoint placed immediately before `GET /api/my-runs`, as specified.
- [x] `GET /api/my-runs` left untouched (Task 3's scope).
- [x] Ownership check via `run_by = %s` prevents cross-user save (verified: 404 for
      another user's run_id).
- [x] Malformed run_id rejected before hitting the DB (verified: 400).
- [x] Blank/whitespace run_name falls back to generated name (verified).
- [x] No regressions in `smoke_test.py` / `api_smoke_test.py`.
- [x] Committed: `api_models.py`, `main.py`, `run_save_smoke_test.py` only (this report
      file updated separately, not bundled into the feature commit).

## Files changed

- `api_models.py` — added `SaveRunInput`.
- `main.py` — added `SaveRunInput` import and the `POST /api/runs/save` endpoint.
- `run_save_smoke_test.py` — created and extended with save-endpoint assertions.

## Commit

`8b24a26` — "feat: add POST /api/runs/save endpoint for naming and saving simulations"
