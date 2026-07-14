# RBAC (Role-Based Access Control) — Design Spec

Date: 2026-07-08
Status: Approved, ready for implementation planning

## Context

The system currently has three DB roles (`superadmin`, `admin`, `user`) but almost no
enforcement of what each role can do:

- The frontend hides the "Pengurusan Pengguna" (User Management) button unless
  `role_name === 'superadmin'`, but this is the only role check anywhere in the app.
- The backend has **no session/token validation at all**. `/api/auth/login` returns a
  random token, but no endpoint ever checks it. Any client can call any endpoint
  (including `POST /api/admin/create-user`) without being logged in.
- The app is a **single-page dashboard**, not a multi-page app. There are no routes for
  "Forecasting Workspace", "Executive Dashboard", "State Risk Comparison", or "Audit Log" —
  everything lives in one `index.html` with JS-toggled sections, plus a separate Admin page.
- Only one CSV download exists (`GET /api/runs/{run_id}/detail.csv`, full per-school detail).
  There is no "summary" report.
- No audit logging happens anywhere, though the database already has two relevant tables
  (`simulation_run_log`, `recommendation_output_log`) that nothing writes to.

This spec defines how the requested Superadmin / Forecasting Admin / Policy Maker
permission matrix maps onto this actual architecture, based on a clarifying-question pass
with the project owner (recorded below).

## Role mapping

Reuse the existing DB roles directly — no renaming, no new role table changes.

| DB `role_name` | Business name | Summary |
|---|---|---|
| `superadmin` | Superadmin | Unrestricted. |
| `admin` | Forecasting Admin | Everything except User Management. Audit Log only if flagged for that account. |
| `user` | Policy Maker | No User Management, no Forecasting Workspace (n/a — see decision below), no Audit Log, no Detailed Download. Policy Simulation otherwise fully usable. |

## Decisions (from clarifying questions)

1. **Pages** — Map RBAC onto existing UI sections instead of building new routes/pages.
   The sidebar (scope filters + policy config) and the three chart cards (comparison,
   subject, risk ranking) stay as one page; Audit Log becomes a new page reached the same
   way the Admin page is today (a header button that swaps the visible `<main>`).
2. **Audit Log** — Scope covers simulation runs **and** logins **and** user-management
   actions (the project owner chose the most complete option). Uses the existing
   `simulation_run_log` table for runs, plus a new `audit_log` table for login/user-mgmt
   events (see Data model below).
3. **Backend enforcement** — Add real enforcement, not just UI hiding: an in-memory
   session store + a `require_role(...)` FastAPI dependency, so protected endpoints
   reject unauthorized calls made directly against the API.
4. **Summary report** — New endpoint returning aggregated KPI + per-subject rows (no
   per-school detail), distinct from the existing detailed CSV.
5. **Policy Simulation "Limited" for Policy Maker** — No lever or mode restriction.
   The only restriction is which download buttons they see.
6. **"Forecasting Workspace" hidden for Policy Maker** — There is no standalone
   baseline-only forecast UI today (`POST /api/forecast/2027` is unused by the frontend).
   Nothing needs to be hidden in the UI; the endpoint itself becomes backend-restricted
   to `superadmin`/`admin` so it can't be reached directly by a Policy Maker if something
   calls it later (e.g. the AI agent).

## Data model changes (additive only — no existing table structure changes)

```sql
-- New table: generic audit trail for login + user-management events
CREATE TABLE audit_log (
    id              INTEGER PRIMARY KEY,
    occurred_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actor_username  VARCHAR,
    actor_role      VARCHAR,
    action          VARCHAR,   -- e.g. 'login_success', 'login_failed', 'user_created'
    details         VARCHAR    -- free-text context, no secrets
);

-- New column: per-account audit-log visibility flag for Forecasting Admins
ALTER TABLE users ADD COLUMN can_view_audit_log BOOLEAN DEFAULT FALSE;
```

`simulation_run_log` (already exists, currently unused) starts being populated on every
`/api/simulate` and `/api/agent/run` call: `run_id`, `scenario_id` (reuse `run_id` if no
separate id is available), `run_by` (username), `run_type` (`'simulate'` or `'agent'`),
`target_scope` (subject/negeri/ppd/kod_sekolah as a short string), `notes` (optional).

## Backend changes

### Session store

```python
SESSIONS: dict[str, dict] = {}  # token -> {"username": ..., "role_name": ...}
```

In-memory, module-level in `main.py`. Populated in `login()`, removed in a new
`POST /api/auth/logout`. No expiry in this pass (documented as a known limitation —
resets on server restart, tokens live until logout).

### `require_role` dependency

A FastAPI dependency that:
- Reads `X-Auth-Token` from request headers.
- 401s if missing or not in `SESSIONS`.
- 403s if the session's `role_name` is not in the allowed set for that endpoint.
- Returns the session dict (`{username, role_name}`) so the endpoint can use it (e.g. to
  stamp `run_by` in the audit/run log).

### Endpoint gating

| Endpoint | Allowed roles |
|---|---|
| `POST /api/auth/login` | public |
| `POST /api/auth/logout` | any authenticated |
| `GET /api/health`, `GET /api/filters/{field}` | public (unchanged — read-only reference data) |
| `POST /api/simulate` | superadmin, admin, user |
| `POST /api/agent/run` | superadmin, admin, user |
| `POST /api/forecast/2027` | superadmin, admin |
| `GET /api/runs/{run_id}/detail.csv` | superadmin, admin |
| `GET /api/runs/{run_id}/summary.csv` (new) | superadmin, admin, user |
| `POST /api/admin/create-user` | superadmin |
| `GET /api/audit-log` (new) | superadmin always; admin only if `can_view_audit_log` true for that session |

`create_user()` also writes an `audit_log` row (`action='user_created'`), and `login()`
writes `login_success` / `login_failed` rows.

### New summary CSV

Built from the same in-memory `summary` + `subject_summary` structures already produced
by `orchestrator.execute(...)` at simulate-time — no new calculation logic, just a second
CSV writer alongside the existing detail writer in `tools.py`, and a matching download
route.

## Frontend changes

- `apiFetch` attaches `X-Auth-Token: state.auth.token` to every request automatically.
- On a 401/403 response, `apiFetch` throws as today, but the caller shows a toast:
  *"You do not have permission to perform this action."* If the call was triggered from
  a gated page (Admin, Audit Log), the page also redirects back to the dashboard —
  this is the "no bypass via direct access" behavior, backed by the real backend 403.
- `goToAdminPage()` / new `goToAuditLogPage()` add a client-side role check up front
  (defense in depth, not the actual security boundary — that's the backend).
- Header gains an "Audit Log" button next to the existing "Pengurusan Pengguna" button.
  Visible if `role_name === 'superadmin'`, or (`role_name === 'admin'` and the login
  response's `can_view_audit_log` is true).
- "Download Detailed Output" button (`btnDownload`) hidden entirely when
  `role_name === 'user'`.
- New "Download Summary Report" button, always shown to any logged-in role once a run
  exists.
- Create User form: a "Can view audit log" checkbox appears only when the role dropdown
  is set to `admin`; ignored/omitted otherwise. Sent as part of the create-user payload.
- New Audit Log page: a simple read-only table (timestamp, user, role, action, details),
  populated from `GET /api/audit-log`, styled consistently with the existing Admin page
  (reusing `.admin-panel` / `.result-card` styling from the earlier theme fix).

## Explicitly out of scope for this pass

- No new page routing/navigation system — everything still lives in `index.html` with
  JS-toggled `<main>` panels.
- No restriction on policy levers or single/combined mode for Policy Maker.
- No changes to the Forecasting Workspace concept beyond backend-gating the unused
  `/api/forecast/2027` endpoint.
- No session persistence/expiry (in-memory only, resets on restart).
- No editing of `can_view_audit_log` (or role) for existing users — only settable at
  account creation. Editing is listed as a future enhancement.

## Testing checklist additions

On top of the existing smoke tests, manually verify:

- Login as each of the three roles; confirm header buttons match the matrix.
- Direct API call (e.g. via `/docs` or curl) to `POST /api/admin/create-user` without a
  token → 401; with a `user` or `admin` token → 403; with `superadmin` token → 200.
- `GET /api/runs/{run_id}/detail.csv` as `user` → 403; as `admin`/`superadmin` → 200.
- `GET /api/runs/{run_id}/summary.csv` as any role → 200.
- `GET /api/audit-log` as `user` → 403; as `admin` without the flag → 403; as `admin`
  with the flag → 200; as `superadmin` → 200.
- Confirm `simulation_run_log` gains a row after every simulate/agent run.
- Confirm `audit_log` gains rows for login success, login failure, and user creation.
