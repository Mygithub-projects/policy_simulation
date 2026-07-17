# Task 3 Report — Backend: filter `GET /api/my-runs` to saved runs only

## What was implemented

- `main.py`: `get_my_runs` handler (`GET /api/my-runs`) now:
  - Selects `run_id, run_timestamp, run_name` (was `run_id, run_timestamp`).
  - Adds `AND is_saved = TRUE` to the WHERE clause, alongside the existing
    `run_by = %s AND run_type IN ('simulate', 'agent')` filter.
  - Keeps `ORDER BY run_timestamp DESC LIMIT 20` unchanged.
  - Includes `run_name` in each returned dict, alongside the existing
    `run_id`, `run_timestamp`, `scenario` keys.
- `run_save_smoke_test.py`: appended assertions verifying that after saving
  `run_id` (with a custom name) and `run_id_2` (blank name -> generated name),
  both appear in `GET /api/my-runs`, and the custom-named entry's `run_name`
  matches exactly.

## TDD evidence

### RED

Command: `python run_save_smoke_test.py` (before modifying `main.py`)

```
run_save_smoke_test: initial checks passed
run_save_smoke_test: save endpoint checks passed
Traceback (most recent call last):
  File "...\run_save_smoke_test.py", line 134, in <module>
    assert saved_entry["run_name"] == "My Johor Science Scenario"
           ~~~~~~~~~~~^^^^^^^^^^^^
KeyError: 'run_name'
```

### GREEN

Command: `python run_save_smoke_test.py` (after modifying `main.py`)

```
run_save_smoke_test: initial checks passed
run_save_smoke_test: save endpoint checks passed
run_save_smoke_test: my-runs filtering checks passed
```

## smoke_test.py / api_smoke_test.py results

Both ran clean (only pre-existing pandas/starlette deprecation warnings, no errors):

- `python smoke_test.py`: printed Health, Summary, Explanation, Artifacts — completed without error.
- `python api_smoke_test.py`: printed "API smoke test passed", Health, Simulation summary, Co-teaching summary, Combined all-policy summary, Agent scenario — completed without error.

## Files changed

- `C:\nisa_punya\PRESTIJ\data\education_workforce_agent_mvp_en\.claude\worktrees\run-first-save-later\main.py` (`get_my_runs` handler, lines ~749-777)
- `C:\nisa_punya\PRESTIJ\data\education_workforce_agent_mvp_en\.claude\worktrees\run-first-save-later\run_save_smoke_test.py` (appended new assertions)

Commit: `443b955` — "feat: filter GET /api/my-runs to saved runs and include run_name"

## Self-review findings

- Query adds `AND is_saved = TRUE` only; `run_by = %s AND run_type IN ('simulate', 'agent')`, `ORDER BY run_timestamp DESC LIMIT 20` all unchanged.
- `run_name` is selected and returned per row alongside `run_id`/`run_timestamp`/`scenario` (none removed).
- All three test scripts run and pass cleanly (evidence above).

No issues found. (Note: this report replaces a stale `task-3-report.md` found in the repo from an earlier/unrelated task numbering — "Frontend regenerate-and-download PDF flow" — which did not match this task's brief.)
