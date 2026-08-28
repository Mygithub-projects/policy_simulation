# CLAUDE.md

## Project Identity

This project is the English-interface version of the **Education Workforce Policy Simulation and Recommendation** MVP.

It supports decision-makers in estimating 2027 teacher demand and understanding the impact of selected policy changes. The application combines:

- FastAPI backend
- PostgreSQL database (migrated from an original DuckDB-file MVP)
- Random Forest Regressor model stored as `.pk1`
- Rule-based policy simulation
- Logical agent orchestration
- HTML/CSS/JavaScript frontend

This is a **decision-support prototype**, not a production HR placement system. All recommendations and simulation results require human review.

## Core Architecture

The application uses one FastAPI backend. The "agents" are logical Python components, not separate apps or external services.

Main files and folders:

| Path | Purpose |
|---|---|
| `main.py` | FastAPI entry point and API routes. |
| `agents.py` | Orchestrator, Scenario Agent, Simulation Agent, Recommendation Agent, and Explanation Agent. |
| `tools.py` | PostgreSQL access, Random Forest forecast, policy simulation formulas, and CSV output generation. |
| `schemas.py` | Internal scenario and policy request schema. |
| `api_models.py` | Pydantic request models exposed by FastAPI. |
| `reports/pdf_report.py` | Builds the PDF simulation report server-side with ReportLab (`POST /api/runs/{run_id}/report.pdf`). Replaced an earlier client-side html2canvas/html2pdf.js screenshot approach, which produced blank charts, missing page margins on overflow, and a duplicated-content bug — all structural consequences of screenshotting the DOM instead of generating a real paginated document. The report's 3 charts are likewise drawn natively with ReportLab's own charting module (`reportlab.graphics.charts`) from raw `labels`/`datasets` data, not a captured PNG of the dashboard's Chart.js canvas — a canvas's pixel size/aspect ratio depends on the browser's layout at capture time, which made captured charts come out inconsistently sized; drawing from data keeps them correctly sized on the page every time, matching the dashboard's colors, orientation, and legend. All report text is still translated client-side (same as the rest of the app) and passed in already-formatted; this module only lays it out. |
| `frontend/` | HTML, CSS, and JavaScript user interface. |
| `frontend/aurora-bg.js` | Vanilla-JS WebGL aurora-glow background (ported from the React Bits `SoftAurora` component, no React/`ogl` dependency). Purely decorative — mounted behind the login screen only, not the landing pages or the dashboard. |
| `frontend/aurora-bg.css` | Positioning styles for the aurora background container (`.aurora-bg`). |
| `frontend/true-focus.js` | Vanilla-JS port of the React Bits `TrueFocus` component (no React/`motion` dependency). Auto-cycles a glowing focus frame across the landing pages' hero headline words. |
| `frontend/true-focus.css` | Styles for the focus word blur and glowing corner-bracket frame (`.focus-word`, `.focus-frame`). |
| `data/` | Original DuckDB backup file (historical reference only; PostgreSQL now serves as the operational database). Treat as sensitive. |
| `models/` | Trained Random Forest model file. |
| `outputs/` | Generated scenario CSV outputs only. |
| `requirements.txt` | Python dependencies. |
| `run_api.bat` | Windows helper script to start the API. |
| `smoke_test.py` | Backend workflow smoke test. |
| `api_smoke_test.py` | API-level smoke test. |

Note: `landing.html` and `landing-en.html` are served directly at `/` and `/en` via `FileResponse` (not under the `/app` static mount), so any local asset they reference (e.g. `true-focus.js`/`true-focus.css`) must use an `/app/...` absolute path to resolve against the `StaticFiles` mount — a bare relative path 404s.

## Development Workflow

Use this normal workflow when developing or testing:

1. Open Anaconda Prompt in this project folder.
2. Activate the Python environment.
3. Install dependencies if needed.
4. Confirm `.env` configuration.
5. Run smoke tests.
6. Start FastAPI.
7. Open the frontend in the browser.
8. Test direct policy simulation.
9. Test Agent Chat interpretation.
10. Confirm generated outputs are written only to `outputs/`.

## Installation

Recommended setup:

```powershell
conda create -n workforce-agent python=3.12 -y
conda activate workforce-agent
pip install -r requirements.txt
```

If the environment already exists:

```powershell
conda activate workforce-agent
pip install -r requirements.txt
```

## Running the Application

Run tests first:

```powershell
python smoke_test.py
python api_smoke_test.py
```

Start FastAPI:

```powershell
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8002
```

Or run:

```powershell
run_api.bat
```

Open the app:

```text
http://127.0.0.1:8002
```

Open API docs:

```text
http://127.0.0.1:8002/docs
```

## Environment Variables

Configuration is loaded from `.env`.

Supported AI providers:

```text
AI_PROVIDER=groq
GROQ_API_KEY=your-key
GROQ_MODEL=llama-3.3-70b-versatile
```

or:

```text
AI_PROVIDER=openai
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4.1-mini
```

or:

```text
AI_PROVIDER=local
```

SMTP (for the User Management feature's temporary-password emails):

```text
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-address@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_ADDRESS=your-address@gmail.com
```

PostgreSQL (the operational database for users, audit logs, and analytical data):

```text
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=workforce_policy_agent
POSTGRES_USER=your-username
POSTGRES_PASSWORD=your-password
```

Important rules:

- Never commit `.env`.
- Never print, expose, or copy API keys or SMTP credentials into logs or documentation.
- If no external AI key is available, the direct simulation interface still works.
- If `AI_PROVIDER=local`, do not call Groq or OpenAI.
- The recommended language-model temperature for this project is `0`.
- If SMTP credentials are missing/invalid, user creation and password reset must still succeed (email failure is reported in the API response, not treated as a hard failure).

## AI and Modelling Behaviour

There are two different kinds of intelligence in this project:

1. **Random Forest Regressor**
   - Predicts teacher demand for 2027.
   - Loaded from `models/random_forest_teacher_demand.pk1`.
   - Does not use temperature.

2. **Language Model**
   - Interprets natural-language user questions.
   - Generates plain-language explanations.
   - Must not perform final arithmetic for policy simulation.
   - Final numbers must come from deterministic Python logic in `tools.py`.

Policy simulation must remain transparent and explainable. Do not hide important calculations inside prompts.

## Policy Simulation Scope

The application supports four policy levers:

1. Target subject-option teacher ratio.
2. Annual subject teaching hours per class.
3. Annual teacher teaching-hour capacity.
4. Co-teaching share.

The application supports:

- Single policy mode.
- Combined policy mode, where two, three, or all four policies can be changed together.

Core assumptions:

- Projection year is 2027.
- 2026 teacher supply is assumed to remain available for the MVP baseline.
- One available teacher is treated as 1.0 FTE.
- Policy calculations are deterministic.
- Recommendations require human review.

## Coding Style

Keep the project simple, readable, and explainable.

Preferred style:

- Use clear and explicit variable names.
- Keep policy formulas in Python, not inside LLM prompts.
- Keep calculation steps easy to trace.
- Prefer small functions over large hidden logic blocks.
- Avoid unnecessary abstractions.
- Avoid over-engineering.
- Keep UI wording stakeholder-friendly.
- Comment policy-sensitive assumptions.
- Use deterministic code for any value displayed as a decision number.

Do not introduce complex frameworks unless the user explicitly requests them.

## Testing Checklist

Before marking a change as complete, run:

```powershell
python smoke_test.py
python api_smoke_test.py
```

For frontend or simulation changes, manually test:

- Subject filter.
- State filter.
- PPD filter.
- School filter.
- Year/form filter.
- Single policy mode.
- Combined policy mode.
- Target option-ratio policy.
- Subject teaching-hours policy.
- Teacher teaching-hour capacity policy.
- Co-teaching policy.
- Agent Chat.
- CSV output generation.

Expected output location:

```text
outputs/
```

## Things Not to Touch Without Explicit Approval

Do not modify these unless the user clearly asks:

- PostgreSQL schema for `users`, `audit_log`, `simulation_run_log`, and the analytical tables (`master_model_2022_2026`, `base_murid_detail_2022_2026`). (Exception, pre-approved: the two additive changes listed under [RBAC](#role-based-access-control-rbac--approved-design-in-progress) — new `audit_log` table and new `users.can_view_audit_log` column. No existing table's structure changes.)
- The original `data/*.duckdb` file (retained as a migration-source backup — do not delete).
- `models/random_forest_teacher_demand.pk1`.
- `.env` secrets.
- Core policy formulas.
- Projection year assumption.
- 2026 supply baseline assumption.
- Port number.
- API contract fields already used by the frontend.

Do not:

- Delete user data.
- Delete backup database files.
- Commit generated outputs.
- Upload the database or model to external services.
- Expose teacher identifiers.
- Print sensitive values from `.env`.
- Call external AI when provider is configured as `local`.

## Data Privacy and Governance

Treat all database files as sensitive.

The teacher identifier field `kputama` has been anonymized into dummy IDs such as:

```text
A0000001
A0000002
A0000003
```

This preserves uniqueness while removing the original identifier.

Rules:

- Do not reverse-anonymize IDs.
- Do not expose original teacher identifiers.
- Do not upload the database to external AI services.
- Do not include raw personal data in generated documentation.
- Keep generated CSV files inside `outputs/`.

## Known Assumptions and Limitations

Current MVP limitations:

- Main projection target is 2027.
- Historical data from 2022-2026 supports short-term projection, but does not automatically guarantee reliable long-term forecasting.
- The Random Forest model predicts demand, not staffing decisions.
- The Recommendation Agent uses rule-based scoring, not machine learning.
- Human-in-the-loop exists as human review, but not yet as a formal approve/reject workflow.
- MCP is not implemented.
- A2A protocol is not implemented.
- Agents are internal Python classes, not interoperable external agents.

## Human Review Requirement

The system may recommend:

- Additional teachers.
- Redeployment.
- Subject-option training.
- Monitoring of policy impact.

However, these recommendations must be reviewed by a human decision-maker. The system should not automatically approve hiring, transfer, or policy action.

## Role-Based Access Control (RBAC) — Approved Design (in progress)

> **Superseded by "RBAC Role Merge & Email Login" below** (2026-07-27) — the three-role table and the `admin`/`user` distinctions in this section no longer reflect the current system. Kept for history; read the section below for the current state.

Three roles, reusing the existing `users.role_name` values directly (no renaming):

| DB role | Business name | Access |
|---|---|---|
| `superadmin` | Superadmin | Unrestricted — all pages, all actions. |
| `admin` | Forecasting Admin | Everything except User Management. Audit Log visible only if `users.can_view_audit_log` is set for that account. |
| `user` | Policy Maker | No User Management, no Forecasting Workspace (n/a today — see below), no Audit Log, no "Download Detailed Output". Policy Simulation is otherwise fully usable (no extra lever/mode restrictions). Has an additional "Simulasi Saya" (My Runs) page not available to the other two roles — see below. |

Key decisions from the design discussion (2026-07-08), since the matrix doesn't map 1:1 onto the current single-page UI:

- **No separate pages/routes.** "Forecasting Workspace" / "Executive Dashboard" / "State Risk Comparison" map onto existing sections of the one dashboard (sidebar scope+policy config, and the three chart cards). No new navigation/routing is being introduced.
- **"Forecasting Workspace" has nothing to hide today.** There is no standalone baseline-only forecast UI (the `/api/forecast/2027` endpoint is unused by the frontend); it will simply be backend-restricted to `superadmin`/`admin` in case something calls it later.
- **Policy Simulation "Limited" for Policy Maker = downloads only.** No lever or mode (single/combined) is restricted — only the reporting buttons.
- **Backend enforcement is being added for real**, not just UI hiding: an in-memory session store (`token → {username, role_name}`) plus a `require_role(...)` dependency, so protected endpoints reject unauthorized calls even via direct API access. Protected: `POST /api/admin/create-user` (superadmin only), `GET /api/runs/{run_id}/detail.csv` and `POST /api/forecast/2027` (superadmin/admin only), new `GET /api/audit-log` (superadmin always, admin if flagged).
- **Audit trail uses existing infrastructure**: the DB already has an unused `simulation_run_log` table — this feature starts writing to it on every `/api/simulate` / `/api/agent/run` call, plus a new `audit_log` table for login and user-management events, plus a new `users.can_view_audit_log BOOLEAN DEFAULT FALSE` column (both additive schema changes, pre-approved as part of this feature — see "Things Not to Touch" below).
- **New "Download Summary Report"** endpoint/button returns aggregated KPI + per-subject rows (no per-school detail) and is available to all three roles; the existing detailed CSV stays superadmin/admin only.

This section supersedes the "Role-based access" and "Audit log for every simulation" bullets that used to live under Future Enhancement Ideas below — they are no longer just ideas, they're the active spec.

## RBAC Role Merge & Email Login (implemented)

Collapses the three-role RBAC model above (superadmin/admin/user) down to two — `superadmin` and `user` — and switches login from username to email. Design discussion: 2026-07-27.

Key decisions:

- **Two roles only.** `superadmin` stays unrestricted, unchanged. `user` now carries the union of the old `admin` + `user` permissions — full CSV/PDF/summary downloads, Audit Log if `users.can_view_audit_log` is set, plus "Simulasi Saya" (My Runs). Nobody lost a capability they had before the merge.
- **`admin` is gone, not renamed.** Every `require_role(...)` check in `main.py` that used to list `"admin"` and `"user"` separately now just checks `"user"` (e.g. `/api/forecast/2027`, `/api/runs/{run_id}/detail.csv`, `/api/audit-log`, `/api/simulate`, `/api/agent/run`). `/api/my-runs` and `/api/runs/save` stay `require_role("user")`-only, unchanged — that restriction was never about admin vs. user, so the merge doesn't touch it.
- **Existing accounts were migrated, not just new ones.** Every `role_name='admin'` row was relabeled to `'user'` via a one-time `migrate_role_merge.py` data migration — no schema change, since `role_name` is a plain `VARCHAR` with no DB-level `CHECK` constraint (see `migrate_duckdb_to_postgres.py`).
- **Email replaces username as the login credential**, but `username` stays in the schema and UI purely as a display name — audit log actor, avatar initial, `simulation_run_log.run_by` — it is no longer looked up during login. `LoginInput.email` replaces `LoginInput.username`; the login endpoint looks up `WHERE email = %s` instead of `WHERE username = %s`.
- **Create-user now also checks email uniqueness**, not just username — since email drives login, two accounts sharing an email would make login match an arbitrary one of them.
- **No legacy fallback.** The migration applies uniformly; there is no username-login path kept around for old accounts.

## User Management (Create / List / Deactivate / Reset Password) — Approved Design (in progress)

Extends the RBAC "Pengurusan Pengguna" admin page (superadmin only) from a bare create-user form into full user lifecycle management, with forced password rotation. Design discussion: 2026-07-11.

Key decisions:

- **UI structure**: the Admin page becomes two collapsible sections — "Create User" (existing form, password field removed) and "Manage Users" (a table of every user ever created, including deactivated ones, with Username/Email/Role/Status/Created/Last Login columns and 🗑️/📝 action icons per row).
- **No more admin-typed passwords.** `CreateUserInput` drops the `password` field entirely. A 12-character random temporary password (mixed case/digits/symbols, no ambiguous characters) is generated server-side on both account creation and password reset, and emailed to the user's registered address — never returned in any API response, to avoid it lingering in browser devtools/logs.
- **One email template, two triggers.** The BM/EN "temporary password" template (provided 2026-07-11, stored verbatim in `email_utils.py`) is used both for new-account creation and for the reset-password action — both are "here's your temporary password, log in and change it."
- **Email failure doesn't block the action.** If SMTP sending fails, the user is still created/reset (`is_first_login=true` either way); the API response reports the email failure so the admin knows to retry via the reset-password action. Uses new `.env` vars: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_ADDRESS`.
- **Deactivate, not hard-delete.** The trash icon sets `users.is_active=false` (existing column, no schema change) — never removes the row, so `audit_log`/`simulation_run_log` history stays linked to a real user. Blocked (400) if the target is the caller's own account, or the last remaining active superadmin — prevents an accidental full lockout.
- **Forced password change is real, not just a flag.** A new "Set New Password" screen appears immediately after login whenever `is_first_login` is true (new account or post-reset) and blocks all dashboard access until submitted. Requires re-entering the current (temporary) password as confirmation. New endpoint: `POST /api/auth/change-password`, any authenticated role.
- **New superadmin-only endpoints**: `GET /api/admin/users` (list, includes inactive), `POST /api/admin/users/{id}/reset-password`, `POST /api/admin/users/{id}/deactivate`.
- **Every action writes to `audit_log`**: `user_created`, `password_reset`, `user_deactivated`, `password_changed` — extends the existing audit trail from the RBAC feature above, no new tables.

## Policy Maker "Simulasi Saya" (My Runs) — Approved Design (implemented)

Lets the Policy Maker (`user`) role browse their own last 20 simulation runs and re-download the summary PDF for any of them, without re-configuring the sidebar from scratch — added because Policy Makers typically run several scenarios in one session, then compare/download reports later (e.g. to present to the Minister), and previously lost that ability the moment the dashboard state was gone (navigation, logout, browser close). Design discussion: 2026-07-12. Spec: `docs/superpowers/specs/2026-07-12-policy-maker-my-runs-design.md`. Plan: `docs/superpowers/plans/2026-07-12-policy-maker-my-runs-implementation.md`.

Key decisions:

- **Policy Maker only, for now.** Superadmin does not get an equivalent list in this iteration — it already has full access plus the Audit Log. Enforced server-side (`GET /api/my-runs` is gated by `Depends(require_role("user"))` only, not `superadmin`). Unaffected by the later RBAC role merge (see "RBAC Role Merge & Email Login" above) — this restriction was never about admin vs. user.
- **List + re-download only.** No side-by-side scenario comparison in this iteration (a possible future enhancement). PDF only — no CSV button on this list.
- **Separate page via a header button** ("Simulasi Saya" / "My Runs"), same pattern as the existing Admin/Audit Log pages — not a sidebar section, so it doesn't disturb the layout for other roles.
- **No database schema changes.** The existing `simulation_run_log` table (run_id, run_by, run_timestamp, run_type) plus each run's already-written `{run_id}_summary.json` file (which stores the full scenario dict) provide everything the list needs — `GET /api/my-runs` just joins those two existing sources, filtered to the caller's own `run_by` and `run_type IN ('simulate', 'agent')`, last 20 rows.
- **Download re-runs the scenario, it does not replay a stored file.** The summary PDF is generated client-side from live Chart.js canvases and in-memory state — there is no server-side PDF file to fetch. Clicking download switches to the dashboard, calls `POST /api/simulate` with the row's archived scenario (deterministic, so the regenerated report is identical to the original), renders the results, waits ~1200ms for the charts' entrance animation to finish, then auto-triggers the existing PDF pipeline. This was chosen over generating the PDF invisibly in the background, because Chart.js needs a real, visible-sized canvas to draw into correctly.
- **Accepted side effect**: re-running the scenario writes a new `simulation_run_log` row (and summary files), same as any simulation run — so a just-downloaded run reappears at the top of "Simulasi Saya" on next load. This is expected, not a bug.

## Sidebar Icon Rail + Accordion Groups (implemented)

Restructures the always-expanded, ever-growing sidebar (Steps 1-3 + AI Agent, all visible and scrolling at once) into a collapsible icon rail with three accordion groups, so the dashboard reclaims sidebar width once a result is on screen. Prompted by panel feedback that the app's font sizes read too small — this landed first because narrower, better-organized sidebar content was judged a prerequisite for any later type-scale increase, not a replacement for it (see "Known follow-up" below). Loosely inspired by a React Bits `CardNav` reference (colored expanding cards, eased/staggered reveal), but re-scoped to fit this app: no React/GSAP dependency was introduced, matching the existing precedent set by `aurora-bg.js` and `true-focus.js` (both React Bits components ported to vanilla JS with the animation library dropped).

Key decisions:

- **Three groups, not four+.** `#sidebar` ([index.html](frontend/index.html)) now holds a 44px icon rail (`.sidebar-rail`) plus a scrollable accordion panel (`.sidebar-groups`) with exactly three sections: **Forecast Analysis** (the original Steps 1-3 — scope, policy, run — unchanged internally), **AI Agent** (the existing agent chat section, unchanged internally), and **Report** (new — see below). Only one group is open at a time.
- **Report actions were relocated, not duplicated.** The save/download buttons (`btnDownload`, `btnDownloadSummary`, `btnDownloadSummaryCsv`, `btnSaveSimulation`) moved from the main panel's table header ([index.html](frontend/index.html), `#recTable`'s `.header-actions`) into the new Report sidebar group. The table header now only shows `#tableInfo` (the row count). All four buttons keep their original element IDs, so no `app.js` show/hide logic needed to change — only their DOM location moved. A new `#reportEmptyHint` line shows in their place before any run exists.
- **Per-group accent colors reuse existing tokens, not new hex values.** Forecast Analysis uses `--gold` (already the step-badge/primary-action color), AI Agent uses `--teal` (already the agent's brand color), Report uses a neutral border/text tone since it carries no prior brand meaning of its own.
- **Collapse is whole-sidebar, not per-group.** Clicking the rail's chevron (`#sidebarRailToggle` → `toggleSidebar()`) shrinks the entire sidebar to the 44px icon rail (`.sidebar.collapsed`), handing that width back to the main panel. Clicking any rail icon (`setActiveGroup(group)`) re-expands the sidebar (if collapsed) and opens that icon's group.
- **Auto-collapses after any result loads, from either trigger.** Whichever action produces a result — the Forecast Analysis "Run Simulation 2027" button (`runSimulation()`) or the AI Agent's "Ask" button (`runAgent()`) — calls `collapseSidebarAfterResult(group)` in `app.js` right after `renderResults()`, which collapses the sidebar and keeps that trigger's rail icon highlighted so it stays clear what produced the result on screen. `downloadPdfForRun()` (the "Simulasi Saya" re-download path) does the same.
- **Starts expanded, Forecast Analysis open, every page load.** No collapsed/expanded state is persisted (no localStorage) — `resetAll()` and initial page load both reset to expanded + Forecast Analysis, matching the "always start fresh" behavior the rest of the form reset already has.
- **Height animation is vanilla JS, not CSS `height: auto`.** `setGroupOpen()` in `app.js` measures `scrollHeight` and transitions `max-height` (browsers can't transition to/from `auto`), then relaxes to `max-height: none` once open so dynamically-rendered content inside it (e.g. `#policyValueArea`, which changes size per policy card) isn't clipped later. The staggered fade-in of each group's top-level children (echoing `CardNav`'s per-card stagger) is pure CSS `:nth-child` transition-delays — no JS-driven stagger loop needed.
- **`focusAgentSection()` (the floating agent-fab shortcut) now calls `setActiveGroup('agent')` before scrolling to it** — previously this just scrolled to `.agent-section--sidebar`, but that section can now be inside a closed (zero-height) accordion group.

Known follow-up (not part of this change): the original panel feedback was about font sizes across the whole dashboard being too small — this sidebar restructure only widened room for the *sidebar's own* future type-scale increase; the broader font-size pass across KPI cards, charts, and tables discussed earlier is still separate, unimplemented work.

## Light / Dark Theme Toggle (implemented)

Adds a header toggle (🌙/☀️, next to the language switch) that switches the whole dashboard between the original dark theme and a new light theme, so the app is no longer dark-only. Explored as a prototype first — colors were mapped and screenshotted in both themes before committing to the approach — then extended to cover real data and the guided tour once the direction was confirmed. Design discussion: 2026-08-28.

Key decisions:

- **CSS custom properties, not a rewrite.** [styles.css](frontend/styles.css) already centralized most colors in one `:root` token block, so the light theme is a second `:root[data-theme="light"]` block redefining those same tokens — not a parallel stylesheet. The one gap was the ~90 places that wrote `rgba(255,255,255,0.XX)` (and a few `rgba(7,9,26,0.XX)` / `rgba(13,18,40,0.XX)`) directly as "light/dark overlay on a dark surface" instead of through a token; these were swept to reference new RGB-triplet custom properties (`--fg-rgb`, `--chrome-rgb`, `--surface-rgb`, `--teal-rgb`, `--gold-rgb` — no `rgba()` wrapper, so a rule writes `rgba(var(--fg-rgb), 0.XX)` and every opacity step flips from one redefinition instead of needing its own light-mode override).
- **The login screen stays dark-only, on purpose.** Its aurora glow background ([aurora-bg.js](frontend/aurora-bg.js)) is dark-only by design, so `:root[data-theme="light"] .login-screen { ... }` re-declares the original dark token values scoped to that screen — the global toggle never reaches it, regardless of which theme is active elsewhere.
- **Applied before first paint.** An inline script at the top of `index.html`'s `<head>` (before the stylesheet link) reads `localStorage.getItem('theme')` and sets `<html data-theme="...">` immediately, so there's no flash of the wrong theme on load. `toggleTheme()` in `app.js` flips the attribute and persists the choice back to `localStorage`.
- **The guided tour ([tour.js](frontend/tour.js)) was re-themed too, not left dark-only.** Its injected `<style>` block used to hardcode the original dark palette directly; it now reads the same CSS custom properties as the rest of the app, so the tour card matches whichever theme is active — including if the user toggles theme mid-tour. A new tour step was added introducing the toggle itself. Growing the tour to 13 steps (one progress dot per step) also outgrew the footer's fixed button/dot layout, clipping the Previous/Next buttons — fixed by widening the tooltip and tightening the dot spacing and button padding.
- **Left unthemed for now**: the marketing landing pages (`landing.html`/`landing-en.html`) and native `<select>` dropdown popups (`.form-control option`, browser-rendered chrome that's unreliable to restyle across browsers) — both minor, out of scope for this pass.
- **Chart.js charts were not touched.** They were never given explicit tick/grid colors, only Chart.js's own defaults (a mid-gray), which already read acceptably on both a dark and a light background — so no theme-aware chart re-render logic was needed.

## Future Enhancement Ideas

Possible future improvements:

- Formal human approval/reject workflow.
- Side-by-side scenario comparison (the "list past runs" half of this is now implemented for Policy Maker — see "Simulasi Saya" above — comparison view is still an idea).
- Extending "Simulasi Saya" (My Runs) to Superadmin/Admin roles.
- Model validation dashboard.
- Editing `can_view_audit_log` for existing users outside of user creation (still only settable at creation time even after this feature).
- Reactivating a deactivated user (currently one-way: deactivate only, no "restore" action).
- Session expiry / persistent session storage (current RBAC design uses an in-memory session dict that resets on server restart).
- MCP tool exposure for external AI clients.
- A2A only if agents are separated into independent services.
- Improved long-range forecasting if more data becomes available.

## Safe Development Principle

When uncertain, preserve the existing working MVP.

Prefer:

- Small, reversible changes.
- Clear explanations.
- Backups before data changes.
- Read-only database access.
- Human approval before changing assumptions.

Do not make the project more complicated than necessary for the current proof of concept.
