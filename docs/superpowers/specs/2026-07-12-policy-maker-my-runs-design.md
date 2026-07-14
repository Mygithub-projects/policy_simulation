# "Simulasi Saya" (My Runs) for Policy Maker — Design

## Background

The Policy Maker (`user`) role can fully use Policy Simulation but is restricted
from the detailed CSV download. In practice, Policy Makers run several
scenarios in one session and want to come back later — often to prepare a
report for the Minister — and download a PDF for a scenario they ran earlier,
without re-configuring the sidebar from scratch. Today the summary PDF can
only be generated from whatever is currently loaded in the dashboard, so once
that state is gone (navigation, logout, browser close), the report is gone
too.

Discussed and approved 2026-07-12.

## Scope

- **Policy Maker (`user` role) only**, for now. Superadmin/Admin are not
  given an equivalent list in this iteration — they already have full access
  plus the Audit Log to review history.
- List + re-download only. No side-by-side scenario comparison in this
  iteration (noted as a possible future enhancement).
- PDF download only — no CSV button on this list (Policy Maker already
  cannot download the detailed CSV; the summary CSV button is intentionally
  left off this list too, to keep it simple per the user's explicit choice).
- Shows the **last 20 runs** for the logged-in Policy Maker, newest first.
  Includes both direct-form simulations and Agent AI-triggered simulations
  (`run_type` `simulate` and `agent`), since both are "a simulation this
  policy maker ran."

## UI

- A new header button, **"Simulasi Saya"**, next to the existing
  Admin/Audit Log buttons — visible only when `state.auth.role_name === 'user'`.
- Clicking it opens a **new separate page** (`myRunsPage`, same pattern as
  `adminPage`/`auditLogPage`: a sibling `<main>` toggled via
  `style.display`), not a sidebar section — chosen specifically so it does
  not disturb the layout for other roles and stays out of the way when not
  in use.
- Table columns:
  1. Tarikh & Masa (run timestamp)
  2. Skop (subject / negeri / PPD / school, using the same formatting
     helpers already used for the scenario banner)
  3. Dasar Disimulasikan (policy summary — e.g. "Nisbah Opsyen 75%" or
     "Gabungan: Nisbah Opsyen + Waktu Pengajaran", built client-side from
     the scenario's `active_policies` + values, reusing the existing
     `getPolicyLabels()` helper)
  4. A single "Muat Turun Laporan PDF" button per row
- Empty state: a friendly message when the Policy Maker hasn't run any
  simulation yet ("Belum ada simulasi dijalankan").

## Backend

**No database schema changes.** Everything needed already exists:
- `simulation_run_log` (existing table) already stores `run_id`,
  `run_by`, `run_timestamp`, `run_type` per run.
- Each run's `{run_id}_summary.json` (already written by
  `WorkforceTools.save_run`) already stores the full scenario dict used for
  that run.

New endpoint: **`GET /api/my-runs`**
- `Depends(require_role("user"))` — enforced server-side, matching the
  "Policy Maker only, for now" decision. (Superadmin/Admin calling this
  endpoint directly get a 403, consistent with how other role-restricted
  endpoints behave in this codebase.)
- Query: `SELECT run_id, run_timestamp FROM simulation_run_log WHERE run_by
  = ? AND run_type IN ('simulate', 'agent') ORDER BY run_timestamp DESC
  LIMIT 20`, parameterized with `session["username"]`.
- For each `run_id`, locate and read `{run_id}_summary.json` from
  `get_output_directories()` (same lookup + path-safety pattern already
  used by the existing `/api/runs/{run_id}/detail.csv` and
  `.../summary.csv` endpoints) to pull out the `scenario` dict.
- Response: `{"runs": [{"run_id": ..., "run_timestamp": ..., "scenario":
  {...ScenarioRequest.to_dict()}}]}`. A run whose summary.json file is
  missing (e.g. manually deleted from `outputs/`) is skipped rather than
  erroring the whole list.

## Download Flow

Clicking "Muat Turun Laporan PDF" on a row:

1. Switches to the main dashboard (`goToDashboard()`).
2. Calls the existing `POST /api/simulate` endpoint directly with the
   row's archived `scenario` dict as the body (its fields already match
   `ScenarioInput` 1:1, since that dict was produced by
   `ScenarioRequest.to_dict()` in the first place — just add the current
   UI language as `lang`) — re-running the exact same scenario. This is
   deterministic (same inputs → same outputs), so the regenerated report
   is identical to the one that would have been downloaded at the time.
   Note `question` is not a `ScenarioInput` field, so it is simply dropped
   if present in the archived scenario dict.
3. Renders the full results as normal (`renderResults(...)`), same as a
   fresh manual run — the user briefly sees the dashboard populate.
4. Once charts finish rendering, automatically calls the existing
   `downloadSummaryPDF()` — no new PDF-generation code path; this reuses
   100% of the current client-side PDF pipeline (chart canvases,
   `buildPdfKpiHtml`, `buildPdfParamsHtml`, html2pdf export).

This was chosen over generating the PDF "invisibly" in the background,
because Chart.js needs a real, visible-sized canvas to render into —
attempting this off-screen risks the same blank/broken-chart failure
mode that was already fixed once for the manual PDF button (see prior
`z-index`/`scrollY`/decode-race fixes). Showing the dashboard populate
before downloading is simpler, safer, and — for this app's older/less
technical user base — more transparent than a silent background process.

**Side effect (accepted):** re-running the scenario writes a brand new
`simulation_run_log` row and a new `{run_id}_summary.json`/CSV pair, same
as any other simulation run. This means the just-downloaded run will
itself appear in the "Simulasi Saya" list on next load. This is expected,
not a bug — the list is a rolling window of the last 20 runs, so it
naturally includes re-downloads.

## Out of Scope (for this iteration)

- Side-by-side scenario comparison.
- Making this list available to Superadmin/Admin.
- CSV download from this list.
- Deleting/clearing entries from the list.
