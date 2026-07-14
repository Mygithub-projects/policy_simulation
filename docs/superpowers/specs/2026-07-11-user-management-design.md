# User Management (Create / List / Deactivate / Reset Password) — Design Spec

Date: 2026-07-11
Status: Approved, ready for implementation planning

## Context

The RBAC feature (see `2026-07-08-rbac-design.md`) added a superadmin-only Admin page
with a single "Create User" form. It has three gaps this spec closes:

1. There is no way to see, deactivate, or reset the password of an existing user —
   the form only creates new accounts.
2. The superadmin types a password by hand when creating a user. There is no
   password-reset flow and no way to email a user their credentials.
3. `users.is_first_login` is stored and returned by `/api/auth/login`, but nothing
   reads it — a brand-new account's temporary password can be used forever with no
   forced change.

This spec adds full user lifecycle management (create/list/deactivate/reset) with
auto-generated temporary passwords delivered by email, and a mandatory
change-password gate that fires whenever `is_first_login` is true.

## Decisions (from clarifying questions, 2026-07-11)

1. **Email delivery** — SMTP via `.env` credentials (Gmail SMTP + app password
   already provided and added to `.env`), using Python's `smtplib`. No third-party
   email API.
2. **Delete = deactivate, not hard delete** — the trash icon sets
   `users.is_active = false` (existing column, no schema change). The row and all
   `audit_log` / `simulation_run_log` history referencing that username stay intact.
3. **Forced password change ships in this pass** — a new post-login screen blocks
   dashboard access whenever `is_first_login` is true.
4. **Create-user form drops the password field entirely** — a temporary password is
   always generated server-side and emailed. There is no "admin types a password"
   path anymore.
5. **Admin page layout** — two collapsible sections: "Create User" (existing form,
   minus the password field) and "Manage Users" (new table + row actions).
6. **Table columns** — Username, Email, Role, Status (Active/Inactive), Created,
   Last Login. Includes inactive (deactivated) users, not just active ones.
7. **Safety guards on deactivation** — blocked (400) if the target is the caller's
   own account, or the last remaining active superadmin.

## Data model

**No schema changes.** Every column this feature needs already exists on `users`:
`email`, `is_active`, `is_first_login`, `password_changed_at`. The existing
`audit_log` table (from the RBAC feature) gets four new `action` values:
`user_created`, `password_reset`, `user_deactivated`, `password_changed`.

## Password generation

A module-level helper, `generate_temp_password() -> str`:
- 12 characters.
- Drawn from an alphabet that excludes visually ambiguous characters
  (`0`, `O`, `I`, `l`, `1`) to reduce transcription errors when a user reads it
  off an email on a phone.
- Guaranteed to include at least one uppercase letter, one lowercase letter, one
  digit, and one symbol (from a small safe set: `!@#$%^&*`), by construction —
  not by post-hoc validation/retry.

## Email

New module `email_utils.py`:

- `send_temp_password_email(to_email: str, username: str, temp_password: str, lang: str) -> bool`
  — sends the appropriate BM or EN template (below, verbatim), returns `True`/`False`
  for success (never raises — a caller that can't reach the mail server must not
  crash the request).
- Reads `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`,
  `SMTP_FROM_ADDRESS` from `.env` via `config.py` (new getter functions, following
  the existing `has_openai_key()`-style pattern).
- Uses `smtplib.SMTP(host, port)` + `starttls()` + `login()` + `send_message()`,
  synchronous (acceptable at this project's scale — no background job queue).

**BM template** (used when the target user's stored `lang` preference, or the
request's `lang`, is `bm`):

```text
Subject: Notifikasi Penetapan Semula Kata Laluan

Assalamualaikum dan Salam Sejahtera,

Tuan/Puan,

Dimaklumkan bahawa pihak pentadbir telah menetapkan semula kata laluan akaun
tuan/puan susulan permohonan berkaitan kata laluan yang terlupa.

Kata laluan sementara/default adalah seperti berikut:

Kata laluan sementara: {temp_password}

Tuan/puan dimohon untuk log masuk menggunakan kata laluan tersebut dan
menukarnya kepada kata laluan baharu dengan segera bagi menjaga keselamatan akaun.

Sekiranya tuan/puan masih menghadapi masalah untuk log masuk, sila hubungi pihak
pentadbir sistem untuk bantuan selanjutnya.

Sekian, terima kasih.

Yang menjalankan amanah,
Pentadbir Sistem
Sistem Simulasi Dasar Tenaga Kerja Pendidikan
```

**EN template** (used when `lang` is `en`):

```text
Subject: Password Reset Notification

Dear User,

Please be informed that the administrator has reset your account password
following your request regarding a forgotten password.

Your temporary/default password is as follows:

Temporary Password: {temp_password}

Please log in using the temporary password and change it immediately to ensure
the security of your account.

Should you continue to experience any issues accessing your account, please
contact the system administrator for further assistance.

Thank you.

Best regards,
System Administrator
Education Workforce Policy Simulation System
```

Both templates are used verbatim for **both** account creation and password
reset — the wording ("following your request regarding a forgotten password")
reads slightly reset-flavored for the creation case too, which was an accepted
tradeoff to keep one template instead of two near-duplicates.

**Email failure handling**: if `send_temp_password_email` returns `False`, the
user is still created/reset (the DB write already happened). The API response
includes `"email_sent": false` so the frontend can show a warning
("user created, but the email failed to send — use the reset-password action to
retry"). The raw temporary password is never included in any API response,
regardless of email success — it only ever exists in the email itself.

## Backend changes

### `api_models.py`

```python
class CreateUserInput(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=120)
    role_name: Literal["superadmin", "admin", "user"] = "user"
    can_view_audit_log: bool = False
    lang: Literal["bm", "en"] = "bm"
    # `password` field removed — always server-generated now.

class ChangePasswordInput(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
```

### `main.py` — endpoints

| Endpoint | Method | Roles | Behavior |
|---|---|---|---|
| `/api/admin/create-user` | POST | superadmin | Generates temp password, creates user with `is_first_login=true`, emails temp password, writes `audit_log(user_created)`. Returns `{id, username, email, role_name, is_first_login: true, email_sent: bool}`. |
| `/api/admin/users` | GET | superadmin | Returns all users (active and inactive): `[{id, username, email, role_name, is_active, created_at, last_login_at}]`. |
| `/api/admin/users/{id}/reset-password` | POST | superadmin | Generates a new temp password, sets `is_first_login=true`, emails it, writes `audit_log(password_reset)`. Same response shape as create (minus role/username duplication concerns — returns `{id, email_sent: bool}`). |
| `/api/admin/users/{id}/deactivate` | POST | superadmin | Sets `is_active=false`. 400 if target is caller's own id, or the last active superadmin. Writes `audit_log(user_deactivated)`. |
| `/api/auth/change-password` | POST | any authenticated | Verifies `current_password` against stored hash, updates `password_hash`, sets `is_first_login=false`, `password_changed_at=CURRENT_TIMESTAMP`. Writes `audit_log(password_changed)`. |

`login()` is unchanged in shape (still returns `is_first_login`) — the frontend
now actually acts on that field.

## Frontend changes

- **Create User form** (`frontend/index.html` / `app.js`): password input removed;
  replaced with a note ("A temporary password will be generated and emailed to
  this address"). Submit still posts to `/api/admin/create-user`, now without a
  `password` field.
- **Admin page structure**: wrap "Create User" and a new "Manage Users" block each
  in a collapsible `<details>`-style section (open by default: Create User).
- **Manage Users table**: populated from `GET /api/admin/users` on page load /
  section expand. Columns: Username, Email, Role, Status (badge: green
  Active / gray Inactive), Created (formatted date), Last Login (formatted date or
  "—" if never). Trailing two icon buttons per row:
  - 🗑️ (delete/deactivate) — confirmation dialog ("Deactivate this user? They will
    no longer be able to log in.") before calling
    `POST /api/admin/users/{id}/deactivate`. Disabled (grayed, no click) for
    already-inactive rows and for the row matching the logged-in user's own
    username.
  - 📝 (reset password) — confirmation dialog ("Send a new temporary password to
    {email}?") before calling `POST /api/admin/users/{id}/reset-password`.
    Disabled for inactive rows.
  - Both actions show a toast reporting success, and a distinct warning toast if
    `email_sent: false` came back.
- **Forced password-change screen**: new full-screen overlay (same visual pattern
  as the existing login screen) shown immediately after a successful login when
  the response's `is_first_login` is true — before the dashboard is shown. Fields:
  current (temporary) password, new password, confirm new password (client-side
  match check). Submits to `/api/auth/change-password` with the stored session
  token; on success, clears the first-login flag in local state and proceeds to
  the dashboard. There is no "skip" option — this screen is mandatory.

## Explicitly out of scope for this pass

- Reactivating a deactivated user (one-way deactivate only).
- Editing `can_view_audit_log` for an existing user outside of creation.
- Any password strength meter/policy beyond the existing `min_length=8` on
  `new_password`.
- Rate-limiting or lockout on repeated failed `change-password` attempts.
- Third-party email provider integration (SMTP only).

## Testing checklist additions

- Create a user → confirm email arrives (BM and EN) with a working temporary
  password, `is_first_login=true` in the DB.
- Log in as that user → confirm the change-password screen appears and blocks
  the dashboard; submit wrong current password → rejected; submit correct
  current password + new password → dashboard appears, `is_first_login=false`,
  `password_changed_at` set.
- Reset password for an existing user → confirm new email arrives, old password
  no longer works, new temp password does (and forces change again).
- Deactivate a user → confirm they can no longer log in (401/403 at `/api/auth/login`
  or equivalent inactive-account rejection), row shows "Inactive" in the table.
- Attempt to deactivate your own logged-in account → 400.
- Attempt to deactivate the last remaining active superadmin → 400.
- Turn off/misconfigure SMTP → confirm create-user and reset-password still
  succeed with `email_sent: false`, and no password appears anywhere in the
  API response.
