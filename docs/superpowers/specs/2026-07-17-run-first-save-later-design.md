# Run First, Save Later — Design Spec

Date: 2026-07-17

## Objective

Today, every `/api/simulate` and `/api/agent/run` call is automatically written to `simulation_run_log`, and the Policy Maker's ("user" role) "Simulasi Saya" (My Runs) page lists all of them. This makes it hard to distinguish scenarios worth keeping from ones a user was just exploring.

This feature lets a Policy Maker review results first, then explicitly choose to save a simulation with a custom name, so "My Runs" only shows the runs they intentionally kept — under names they chose.

## Non-Goals

- No change to Superadmin/Admin behavior or visibility. They keep seeing every simulation via the Audit Log, exactly as today.
- No rename/edit of a run's name after it has been saved.
- No side-by-side scenario comparison (tracked separately as a future idea).
- No change to how `/api/simulate` / `/api/agent/run` compute or return results — only what happens to the run afterward.

## Why Auto-Logging Isn't Removed

The RBAC/audit-trail feature (approved 2026-07-08) relies on every simulation call writing a `simulation_run_log` row so the Audit Log (superadmin/admin) shows a complete activity trail, including runs nobody chose to keep. Fully removing automatic logging (as the original request literally described) would silently break that completeness guarantee.

Resolution: keep the existing auto-insert on every call (unchanged), and add a separate opt-in "save" step that only affects what the Policy Maker's own "My Runs" list shows. Two concerns (audit completeness vs. user-curated history), one table, distinguished by a new `is_saved` flag.

## Database Changes

Add two nullable/defaulted columns to `simulation_run_log` (no changes to any other column, no data migration needed for existing rows):

```sql
ALTER TABLE simulation_run_log
    ADD COLUMN run_name VARCHAR,
    ADD COLUMN is_saved BOOLEAN DEFAULT FALSE;
```

Applies to:

- **PostgreSQL** (operational database) — run once via a small maintenance script, following the existing pattern of one-off maintenance scripts in this repo.
- **`data/*.duckdb`** (historical backup file) — run the same `ALTER TABLE` directly against the backup file via a short DuckDB-native script, so its schema stays in sync with Postgres even though the running app never queries it at runtime. This file is not touched otherwise (no row-level backfill needed since it has no post-migration rows).
- **`migrate_duckdb_to_postgres.py`** — update its `CREATE TABLE IF NOT EXISTS simulation_run_log (...)` statement to include `run_name` and `is_saved`, so a from-scratch replay of the migration produces the current schema.

Existing rows in Postgres default to `run_name = NULL`, `is_saved = FALSE` (i.e., "not saved" — matches today's implicit state, since no rows have ever been explicitly saved before this feature ships).

## Backend Changes (`main.py`)

### Unchanged: `_write_run_log`

Still called at the end of every `/api/simulate` and `/api/agent/run` request, exactly as today. `run_name` is left NULL and `is_saved` FALSE on insert — this is what makes the Audit Log's existing behavior (showing all simulation activity) continue to work unmodified.

### New: `POST /api/runs/save`

- Access: `Depends(require_role("user"))` — only the Policy Maker role can save runs, matching the existing role scope of "My Runs".
- Request body: `{run_id: str, run_name: str}`.
- Behavior:
  1. Validate `run_id` has the same `RUN_` prefix / alphanumeric shape already enforced on the other `run_id`-taking endpoints.
  2. If `run_name` is blank or whitespace-only after stripping, substitute a server-generated fallback: `f"Simulation - {timestamp}"` (using the run's own `run_timestamp` from the row being updated, not wall-clock time, so it's reproducible and doesn't require a new "current time" source).
  3. Run `UPDATE simulation_run_log SET run_name = %s, is_saved = TRUE WHERE run_id = %s AND run_by = %s`, scoping to the caller's own username so a user cannot save/name another user's run by guessing a `run_id`.
  4. If no row was updated (bad `run_id`, or it belongs to someone else), return `404`.
  5. On success, return the saved `run_id` and final `run_name` (useful for the frontend to reflect the fallback name if the user left the field blank).

### Modified: `GET /api/my-runs`

Add `AND is_saved = TRUE` to the existing `WHERE run_by = %s AND run_type IN ('simulate', 'agent')` clause, and add `run_name` to the selected columns and the returned JSON per run. No other change — still last 20 rows, still joins each row's `{run_id}_summary.json` for scenario details exactly as it does today.

## Frontend Changes

### Results view (`frontend/index.html` + `frontend/app.js`)

- Add a "Save Simulation" button to the results view, visible only when `state.auth.role_name === 'user'` (same guard already used for `myRunsBtn`), shown once a simulation completes successfully (the `run_id` is already present in the `/api/simulate` / `/api/agent/run` response, so no extra fetch is needed to enable it).
- Clicking it opens a small modal with a single text input, labeled "Nama Simulasi" / "Simulation Name" (per existing BM/EN dual-language pattern in `lang.js`), and Save/Cancel buttons.
- Submitting the modal calls `POST /api/runs/save` with `{run_id, run_name}` (sending `""` if the user left it blank — the backend applies the fallback name).
- On success: close the modal, show a success toast, and switch the button to a disabled "Saved ✓" state for the remainder of that results view (prevents saving the same run twice; a fresh simulation run gets a fresh button).
- On failure: show an error toast, leave the button enabled for retry.

### My Runs page

Add a `run_name` column to the runs table, displayed as the first column (before timestamp/scope/policy), so users can scan by the names they chose rather than by timestamp.

## Testing

- `smoke_test.py` / `api_smoke_test.py`: extend to cover `POST /api/runs/save` (happy path, blank-name fallback, wrong-owner 404, bad run_id 400) and confirm `/api/my-runs` only returns saved rows.
- Manual: run a simulation as Policy Maker, confirm it does NOT appear in My Runs until saved; save it with a custom name and confirm it appears with that name; save one with a blank name and confirm the fallback name appears; confirm Superadmin/Admin's Audit Log still shows every simulation run regardless of save state.
