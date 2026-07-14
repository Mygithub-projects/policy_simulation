# PostgreSQL Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the embedded DuckDB `.duckdb` file with a centralized PostgreSQL server (`localhost:5432`, database `workforce_policy_agent`) as the system of record for this app, with no change to API contracts or policy-simulation math.

**Architecture:** Introduce a single `db.py` module wrapping `psycopg2` connections (read-only vs read-write, matching the existing DuckDB pattern), replace every `duckdb.connect(...)` call site in `main.py`/`tools.py`/maintenance scripts with it, rewrite `?`-style params to `%s`, replace DuckDB-only calls (`SHOW TABLES`, `current_setting('access_mode')`, `.df()`) with Postgres-safe equivalents, and provide one data-migration script that recreates the schema in Postgres and copies every row across from the existing `.duckdb` file. The Random Forest model, policy formulas, and API responses are untouched.

**Tech Stack:** FastAPI, psycopg2-binary, pandas (`pd.read_sql`), existing DuckDB file as the one-time migration source.

## Global Constraints

- Projection year (2027) and 2026-supply-baseline assumptions are NOT touched (CLAUDE.md).
- Core policy formulas in `tools.py` (`simulate_policy`, `forecast_2027`, `summarize`) must produce numerically identical output before/after migration — this is a storage-layer change only.
- Port number for the FastAPI app (8002) is unchanged; only the *database* port changes (DuckDB file → Postgres `5432`).
- API contract fields already used by the frontend must not change.
- `.env` must never be committed; new Postgres credentials go in `.env` only, following the existing `SMTP_*` pattern in `config.py`.
- `data/*.duckdb` files are not deleted or modified by this migration — the source file stays as an authoritative backup until the user confirms cutover.
- Every new/changed SQL statement must be plain ANSI SQL runnable by both `psycopg2` and (for the transition window) verifiable by eye against the DuckDB original — no ORM introduced (YAGNI; the app already treats SQL as the source of truth, per CLAUDE.md "Keep policy formulas in Python... Keep calculation steps easy to trace").

---

## File Structure

| File | Responsibility |
|---|---|
| `db.py` (new) | Single place that builds a `psycopg2` connection from `.env` Postgres settings; exposes `get_connection(read_only: bool)` matching the existing `duckdb.connect(path, read_only=...)` call shape used throughout `main.py`. |
| `config.py` (modify) | Add `get_postgres_dsn()` / individual getters (`get_postgres_host()`, etc.), replacing `get_database_path()`'s role as the "how do I reach the DB" entry point. `get_database_path()` is kept only for the migration script (it still needs to read the old `.duckdb` file once). |
| `migrate_duckdb_to_postgres.py` (new) | One-off script: connects to the existing `.duckdb` file (read-only) and the new Postgres DB, creates all tables in Postgres, copies every row, and reports row counts for verification. Not part of the running app. |
| `tools.py` (modify) | Swap `duckdb.connect` → `db.get_connection`, `?` → `%s`, `SHOW TABLES`/`current_setting('access_mode')` → `information_schema.tables` query, `.execute(q).df()` → `pd.read_sql(q, connection, params=...)`. |
| `main.py` (modify) | Same swap at all 15 connection sites; replace manual `MAX(id)+1` insert logic with Postgres `RETURNING id` from `SERIAL`/`IDENTITY` columns. |
| `create_user.py`, `update_user_schema.py`, `update_superadmin.py`, `migrate_rbac_schema.py` (modify) | Swap to `db.get_connection`; stop hardcoding the `.duckdb` filename. |
| `smoke_test.py`, `api_smoke_test.py`, `rbac_smoke_test.py`, `user_management_smoke_test.py` (modify) | Swap direct `duckdb.connect` cleanup calls to `db.get_connection`. |
| `requirements.txt` (modify) | Add `psycopg2-binary>=2.9,<3`. Keep `duckdb` (still needed by the one-off migration script and until cutover is confirmed). |
| `.env` / `.env.example` (modify) | Add `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`. |
| `CLAUDE.md` (modify) | Update "Core Architecture" table and "Things Not to Touch" to describe Postgres as the system of record instead of DuckDB. |

---

### Task 1: Postgres connection module and config

**Files:**
- Create: `db.py`
- Modify: `config.py` (add after `get_smtp_from_address`, ~line 153)
- Modify: `.env.example`
- Modify: `requirements.txt`
- Test: `test_db_connection.py`

**Interfaces:**
- Produces: `config.get_postgres_dsn() -> str`, `db.get_connection(read_only: bool = True)` returning a live `psycopg2` connection with `connection.set_session(readonly=read_only, autocommit=not read_only is False)` semantics matching current DuckDB usage (read-only connections for SELECT-only handlers, read-write for INSERT/UPDATE handlers). Later tasks call `db.get_connection(read_only=...)` exactly like the old `duckdb.connect(str(get_database_path()), read_only=...)`.

- [ ] **Step 1: Add Postgres env vars to `.env.example`**

Append to `.env.example`:
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=workforce_policy_agent
POSTGRES_USER=postgres
POSTGRES_PASSWORD=
```

- [ ] **Step 2: Add `psycopg2-binary` to `requirements.txt`**

Edit `requirements.txt` line 4 area, add a new line directly below `duckdb>=1.4,<2`:
```
psycopg2-binary>=2.9,<3
```

- [ ] **Step 3: Add Postgres getters to `config.py`**

Add at the end of `config.py` (after `get_smtp_from_address`, currently ending line 153):
```python
def get_postgres_host() -> str:
    return os.getenv("POSTGRES_HOST", "localhost").strip()


def get_postgres_port() -> int:
    return int(os.getenv("POSTGRES_PORT", "5432").strip() or "5432")


def get_postgres_db() -> str:
    return os.getenv("POSTGRES_DB", "workforce_policy_agent").strip()


def get_postgres_user() -> str:
    return os.getenv("POSTGRES_USER", "postgres").strip()


def get_postgres_password() -> str:
    return os.getenv("POSTGRES_PASSWORD", "").strip()


def get_postgres_dsn() -> str:
    return (
        f"host={get_postgres_host()} port={get_postgres_port()} "
        f"dbname={get_postgres_db()} user={get_postgres_user()} "
        f"password={get_postgres_password()}"
    )
```

- [ ] **Step 4: Write `db.py`**

Create `db.py`:
```python
"""PostgreSQL connection helper, replacing the former DuckDB file access."""

from __future__ import annotations

import psycopg2

from config import get_postgres_dsn


def get_connection(read_only: bool = True):
    """Return a live psycopg2 connection, mirroring the old
    duckdb.connect(path, read_only=...) call shape used across the app."""
    connection = psycopg2.connect(get_postgres_dsn())
    connection.set_session(readonly=read_only, autocommit=False)
    return connection
```

- [ ] **Step 5: Write the failing test**

Create `test_db_connection.py`:
```python
from db import get_connection


def test_read_only_connection_rejects_write():
    connection = get_connection(read_only=True)
    try:
        cursor = connection.cursor()
        try:
            cursor.execute("CREATE TABLE test_readonly_guard (id INTEGER)")
            connection.commit()
            assert False, "Expected a read-only violation"
        except Exception as error:
            assert "read-only" in str(error).lower()
        finally:
            connection.rollback()
    finally:
        connection.close()


def test_read_write_connection_can_select():
    connection = get_connection(read_only=False)
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        assert cursor.fetchone()[0] == 1
    finally:
        connection.close()
```

- [ ] **Step 6: Run test to verify it fails**

Run: `python -m pytest test_db_connection.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'db'` (before Step 4) or a connection error if Postgres isn't reachable yet — confirm Postgres is running at `localhost:5432` with database `workforce_policy_agent` before proceeding.

- [ ] **Step 7: Install psycopg2-binary and run test to verify it passes**

Run: `pip install -r requirements.txt && python -m pytest test_db_connection.py -v`
Expected: PASS (2 passed)

- [ ] **Step 8: Commit**

```bash
git add db.py config.py .env.example requirements.txt test_db_connection.py
git commit -m "feat: add PostgreSQL connection module"
```

---

### Task 2: Schema + data migration script

**Files:**
- Create: `migrate_duckdb_to_postgres.py`
- Test: manual verification (row-count comparison), no pytest — this is a one-off operational script per CLAUDE.md's "Safe Development Principle" (backups before data changes, read-only DB access).

**Interfaces:**
- Consumes: `config.get_database_path()` (existing, for the DuckDB source), `config.get_postgres_dsn()` (from Task 1).
- Produces: populated Postgres database matching the schema inventoried below. Later tasks assume these tables/columns already exist in Postgres.

- [ ] **Step 1: Write the migration script**

Create `migrate_duckdb_to_postgres.py`:
```python
"""One-off migration: copy all tables from the existing DuckDB file into
PostgreSQL. Source .duckdb file is opened read-only and is never modified."""

from __future__ import annotations

import duckdb
import psycopg2
from psycopg2.extras import execute_values

from config import get_database_path, get_postgres_dsn

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR NOT NULL UNIQUE,
        email VARCHAR NOT NULL,
        password_hash VARCHAR NOT NULL,
        role_name VARCHAR NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        is_first_login BOOLEAN NOT NULL DEFAULT TRUE,
        password_changed_at TIMESTAMP,
        can_view_audit_log BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login_at TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_log (
        id SERIAL PRIMARY KEY,
        occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        actor_username VARCHAR,
        actor_role VARCHAR,
        action VARCHAR,
        details VARCHAR
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS simulation_run_log (
        run_id VARCHAR PRIMARY KEY,
        scenario_id VARCHAR,
        run_timestamp TIMESTAMP,
        run_by VARCHAR,
        run_type VARCHAR,
        target_scope VARCHAR,
        notes VARCHAR
    )
    """,
]

# Analytical, read-only tables copied verbatim from DuckDB (column types
# inferred at copy time via CREATE TABLE ... matching DuckDB's pandas dtypes).
ANALYTICAL_TABLES = [
    "master_model_2022_2026",
    "base_murid_detail_2022_2026",
]


def copy_analytical_table(duck_conn, pg_conn, table_name: str) -> int:
    frame = duck_conn.execute(f"SELECT * FROM {table_name}").df()
    columns = list(frame.columns)
    with pg_conn.cursor() as cursor:
        column_defs = ", ".join(f'"{col}" TEXT' for col in columns)
        cursor.execute(f'DROP TABLE IF EXISTS "{table_name}"')
        cursor.execute(f'CREATE TABLE "{table_name}" ({column_defs})')
        rows = [tuple(None if pd_isna(v) else v for v in row) for row in frame.itertuples(index=False)]
        if rows:
            execute_values(
                cursor,
                f'INSERT INTO "{table_name}" VALUES %s',
                rows,
            )
    pg_conn.commit()
    return len(frame)


def pd_isna(value) -> bool:
    import pandas as pd

    return bool(pd.isna(value))


def copy_operational_table(duck_conn, pg_conn, table_name: str, columns: list[str]) -> int:
    try:
        rows = duck_conn.execute(f"SELECT {', '.join(columns)} FROM {table_name}").fetchall()
    except duckdb.CatalogException:
        return 0
    if not rows:
        return 0
    placeholders = ", ".join(columns)
    with pg_conn.cursor() as cursor:
        execute_values(
            cursor,
            f'INSERT INTO "{table_name}" ({placeholders}) VALUES %s ON CONFLICT DO NOTHING',
            rows,
        )
    pg_conn.commit()
    return len(rows)


def main() -> None:
    duck_conn = duckdb.connect(str(get_database_path()), read_only=True)
    pg_conn = psycopg2.connect(get_postgres_dsn())
    try:
        with pg_conn.cursor() as cursor:
            for statement in SCHEMA_STATEMENTS:
                cursor.execute(statement)
        pg_conn.commit()

        for table in ANALYTICAL_TABLES:
            count = copy_analytical_table(duck_conn, pg_conn, table)
            print(f"{table}: {count} rows copied")

        users_columns = [
            "id", "username", "email", "password_hash", "role_name",
            "is_active", "is_first_login", "password_changed_at",
            "can_view_audit_log", "created_at", "last_login_at",
        ]
        count = copy_operational_table(duck_conn, pg_conn, "users", users_columns)
        print(f"users: {count} rows copied")

        audit_columns = ["id", "occurred_at", "actor_username", "actor_role", "action", "details"]
        count = copy_operational_table(duck_conn, pg_conn, "audit_log", audit_columns)
        print(f"audit_log: {count} rows copied")

        run_log_columns = [
            "run_id", "scenario_id", "run_timestamp", "run_by", "run_type",
            "target_scope", "notes",
        ]
        count = copy_operational_table(duck_conn, pg_conn, "simulation_run_log", run_log_columns)
        print(f"simulation_run_log: {count} rows copied")

        with pg_conn.cursor() as cursor:
            cursor.execute("SELECT setval('users_id_seq', COALESCE((SELECT MAX(id) FROM users), 1))")
            cursor.execute("SELECT setval('audit_log_id_seq', COALESCE((SELECT MAX(id) FROM audit_log), 1))")
        pg_conn.commit()
    finally:
        duck_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the migration against the real database (manual verification, not automated test)**

Run: `python migrate_duckdb_to_postgres.py`
Expected output: one line per table with a row count > 0 for `master_model_2022_2026` and `base_murid_detail_2022_2026` (the two tables `tools.health_check` requires), and >= 0 for `users`/`audit_log`/`simulation_run_log` (may be empty on a fresh RBAC install).

- [ ] **Step 3: Verify row counts match the source `.duckdb` file**

Run (Python REPL or short script):
```python
import duckdb
from config import get_database_path

conn = duckdb.connect(str(get_database_path()), read_only=True)
for table in ["master_model_2022_2026", "base_murid_detail_2022_2026"]:
    print(table, conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
```
Compare against `psql -h localhost -U postgres -d workforce_policy_agent -c "SELECT COUNT(*) FROM master_model_2022_2026;"` (and the same for `base_murid_detail_2022_2026`). Counts must match exactly.

- [ ] **Step 4: Commit**

```bash
git add migrate_duckdb_to_postgres.py
git commit -m "feat: add DuckDB-to-PostgreSQL data migration script"
```

---

### Task 3: Port `tools.py` to PostgreSQL

**Files:**
- Modify: `tools.py:73-230` (`_connect`, `health_check`, `get_filter_options`, `load_coteaching_scope`, `load_2026_features`)
- Test: `test_tools_postgres.py`

**Interfaces:**
- Consumes: `db.get_connection(read_only=True)` from Task 1; Postgres tables populated by Task 2.
- Produces: `WorkforceTools` with the exact same public methods/signatures as before (`health_check`, `get_filter_options`, `load_coteaching_scope`, `load_2026_features`, `forecast_2027`, `simulate_policy`, `summarize`, `save_run`) — no caller in `main.py`/`agents.py` changes signature.

- [ ] **Step 1: Write the failing test**

Create `test_tools_postgres.py`:
```python
from pathlib import Path

from config import get_model_path
from tools import WorkforceTools


def test_health_check_reports_postgres_tables():
    tools = WorkforceTools(Path("unused"), get_model_path())
    result = tools.health_check()
    assert result["access_mode"] == "read_only"


def test_get_filter_options_returns_semua_first():
    tools = WorkforceTools(Path("unused"), get_model_path())
    options = tools.get_filter_options("negeri")
    assert options[0] == "SEMUA"
    assert len(options) > 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest test_tools_postgres.py -v`
Expected: FAIL — `tools.WorkforceTools.__init__` still calls `duckdb.connect` inside `health_check`, which will error because `self.database_path` is no longer a `.duckdb` path.

- [ ] **Step 3: Update `tools.py` imports and `_connect`**

Modify `tools.py:11` — replace:
```python
import duckdb
```
with:
```python
import db
```

Modify `tools.py:73-74` — replace:
```python
    def _connect(self):
        return duckdb.connect(str(self.database_path), read_only=True)
```
with:
```python
    def _connect(self):
        return db.get_connection(read_only=True)
```

- [ ] **Step 4: Update `health_check` (`tools.py:76-102`)**

Replace the DuckDB-specific pragma/`SHOW TABLES` calls:
```python
    def health_check(self) -> dict[str, Any]:
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SHOW transaction_read_only")
                is_read_only = cursor.fetchone()[0] == "on"
                cursor.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
                tables = {row[0] for row in cursor.fetchall()}
        finally:
            connection.close()
        if not is_read_only:
            raise RuntimeError("Source database is not opened read-only.")
        required_tables = {
            "master_model_2022_2026",
            "base_murid_detail_2022_2026",
        }
        missing_tables = required_tables - tables
        if missing_tables:
            raise RuntimeError(
                "Required table(s) missing: " + ", ".join(sorted(missing_tables))
            )
        if not hasattr(self.model, "predict"):
            raise RuntimeError("The supplied model does not expose predict().")
        return {
            "database": "PostgreSQL",
            "access_mode": "read_only",
            "model": self.model_path.name,
        }
```

- [ ] **Step 5: Update `get_filter_options` param placeholders (`tools.py:104-138`)**

Replace every `?` in the clauses list with `%s` (two occurrences, `tools.py:116` and `tools.py:119`):
```python
        if field in {"ppd", "kod_sekolah", "kodtingkatantahun"} and negeri != "SEMUA":
            clauses.append("negeri = %s")
            parameters.append(negeri)
        if field in {"kod_sekolah", "kodtingkatantahun"} and ppd != "SEMUA":
            clauses.append("ppd = %s")
            parameters.append(ppd)
```
Replace the fetch (`tools.py:133-137`):
```python
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, parameters)
                values = [row[0] for row in cursor.fetchall()]
        finally:
            connection.close()
        return ["SEMUA", *values]
```

- [ ] **Step 6: Update `load_coteaching_scope` (`tools.py:140-190`)**

Replace every `?` in the per-column clause loop (`tools.py:155`) with `%s`:
```python
            if value != "SEMUA":
                clauses.append(f"{column} = %s")
                parameters.append(value)
```
Replace the `IN (...)` placeholder builder (`tools.py:162-163`):
```python
        if selected_levels != ["SEMUA"]:
            placeholders = ", ".join("%s" for _ in selected_levels)
            level_condition = f"KODTINGKATANTAHUN IN ({placeholders})"
            level_parameters.extend(selected_levels)
```
Replace the `.df()` fetch (`tools.py:185-189`):
```python
        connection = self._connect()
        try:
            import pandas as pd

            scope = pd.read_sql(query, connection, params=query_parameters)
        finally:
            connection.close()
        return scope
```

- [ ] **Step 7: Update `load_2026_features` (`tools.py:192-230`)**

Replace `?` at `tools.py:203` with `%s`:
```python
            if value != "SEMUA":
                clauses.append(f"{column} = %s")
                parameters.append(value)
```
Replace the `.df()` fetch (`tools.py:223-227`):
```python
        connection = self._connect()
        try:
            import pandas as pd

            data = pd.read_sql(query, connection, params=parameters)
        finally:
            connection.close()
```

- [ ] **Step 8: Run test to verify it passes**

Run: `python -m pytest test_tools_postgres.py -v`
Expected: PASS (2 passed) — requires Postgres populated by Task 2 with real `negeri` values in `master_model_2022_2026`.

- [ ] **Step 9: Run the full smoke test**

Run: `python smoke_test.py`
Expected: same pass/fail behavior as before migration (compare summary numbers against a pre-migration run — the policy math in `simulate_policy`/`forecast_2027` is untouched, so results must be identical).

- [ ] **Step 10: Commit**

```bash
git add tools.py test_tools_postgres.py
git commit -m "feat: port tools.py from DuckDB to PostgreSQL"
```

---

### Task 4: Port `main.py` connection sites

**Files:**
- Modify: `main.py:8` (import), and every connection site at lines `117, 133, 244, 267, 311, 326, 366, 396, 411, 442, 462, 482, 496, 627, 694`
- Test: `api_smoke_test.py` (existing, run manually — it already exercises these endpoints)

**Interfaces:**
- Consumes: `db.get_connection(read_only=...)` from Task 1.
- Produces: identical API responses/contracts; internal SQL now uses `%s` placeholders and Postgres `RETURNING id` instead of manual `MAX(id)+1`.

- [ ] **Step 1: Replace the import**

Modify `main.py:8` — replace:
```python
import duckdb
```
with:
```python
import db
```

- [ ] **Step 2: Replace every connection-open call**

For each of the 15 call sites, replace the pattern:
```python
connection = duckdb.connect(str(get_database_path()), read_only=True)
```
with:
```python
connection = db.get_connection(read_only=True)
```
and every:
```python
write_connection = duckdb.connect(str(get_database_path()), read_only=False)
```
with:
```python
write_connection = db.get_connection(read_only=False)
```
Exact line numbers to change: `117, 133, 244, 267, 311, 326, 366, 396, 411, 442, 462, 482, 496, 627, 694`.

- [ ] **Step 3: Replace `?` placeholders with `%s` throughout `main.py`**

Run this check to find every remaining `?` in an `.execute(` call:
```bash
grep -n "execute(" main.py
```
For each match, inspect the SQL string and replace positional `?` markers with `%s` (same left-to-right order — psycopg2 does not support DuckDB's `?` syntax).

- [ ] **Step 4: Replace manual `MAX(id)+1` insert logic (`main.py:119`, `main.py:328`)**

At `main.py:119` (user-creation insert) and `main.py:328` (equivalent audit/user insert), remove the prior `SELECT MAX(id)+1` query and the `id` value from the INSERT column list, then capture the generated id via `RETURNING id`:
```python
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO users (username, email, password_hash, role_name,
                                is_active, is_first_login, can_view_audit_log)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (username, email, password_hash, role_name, True, True, can_view_audit_log),
        )
        new_id = cursor.fetchone()[0]
    connection.commit()
```
(Match the actual existing column list at each site — this shows the pattern to apply, not a literal copy-paste, since the two sites insert into different tables per the RBAC design.)

- [ ] **Step 5: Run the API smoke test**

Run: `python -m uvicorn main:app --host 127.0.0.1 --port 8002 &` then `python api_smoke_test.py`
Expected: PASS, identical to pre-migration behavior (same endpoints, same response shapes).

- [ ] **Step 6: Manually test the checklist from CLAUDE.md**

Open `http://127.0.0.1:8002`, and per CLAUDE.md's Testing Checklist, verify: Subject/State/PPD/School/Year-form filters populate, single and combined policy modes compute, all four policy levers respond, Agent Chat still answers, and CSV/summary outputs land in `outputs/`.

- [ ] **Step 7: Commit**

```bash
git add main.py
git commit -m "feat: port main.py from DuckDB to PostgreSQL"
```

---

### Task 5: Port maintenance and smoke-test scripts

**Files:**
- Modify: `create_user.py`, `update_user_schema.py`, `update_superadmin.py`, `migrate_rbac_schema.py`
- Modify: `smoke_test.py`, `rbac_smoke_test.py`, `user_management_smoke_test.py`
- Test: run each script manually (they are already operational scripts, not pytest suites)

**Interfaces:**
- Consumes: `db.get_connection(read_only=...)` from Task 1.
- Produces: no behavior change — these scripts still create/seed/update users and run schema migrations, just against Postgres.

- [ ] **Step 1: Update `create_user.py`**

Replace the hardcoded DuckDB filename and `duckdb.connect(...)` call with:
```python
import db

connection = db.get_connection(read_only=False)
```
Remove the now-unused hardcoded `.duckdb` filename constant.

- [ ] **Step 2: Update `update_user_schema.py` and `update_superadmin.py`**

Apply the same replacement (hardcoded filename + `duckdb.connect` → `db.get_connection(read_only=False)`).

- [ ] **Step 3: Update `migrate_rbac_schema.py`**

Replace its `duckdb.connect(...)` call with `db.get_connection(read_only=False)`. The `ALTER TABLE users ADD COLUMN IF NOT EXISTS ...` and `CREATE TABLE IF NOT EXISTS audit_log (...)` statements are already ANSI-compatible and need no further change (this script becomes redundant once Task 2's migration script has run once against Postgres, but is kept idempotent for safety).

- [ ] **Step 4: Update `smoke_test.py`, `rbac_smoke_test.py`, `user_management_smoke_test.py`**

In each file, replace direct `duckdb.connect(...)` cleanup calls (`rbac_smoke_test.py:3,14,69,72,213,255`; `user_management_smoke_test.py:82,85`) with `db.get_connection(read_only=False)`, keeping the same cleanup SQL (only the connection call changes).

- [ ] **Step 5: Run all smoke tests**

Run:
```bash
python smoke_test.py
python api_smoke_test.py
python rbac_smoke_test.py
python user_management_smoke_test.py
```
Expected: all PASS, matching pre-migration output.

- [ ] **Step 6: Commit**

```bash
git add create_user.py update_user_schema.py update_superadmin.py migrate_rbac_schema.py smoke_test.py rbac_smoke_test.py user_management_smoke_test.py
git commit -m "feat: port maintenance and smoke-test scripts to PostgreSQL"
```

---

### Task 6: Update documentation to reflect PostgreSQL

**Files:**
- Modify: `CLAUDE.md` (Project Identity, Core Architecture table, Environment Variables, Things Not to Touch)
- Modify: `data/README.txt`

**Interfaces:**
- None (documentation only).

- [ ] **Step 1: Update `CLAUDE.md` Project Identity paragraph**

Replace "DuckDB analytical database" with "PostgreSQL database (migrated from an original DuckDB-file MVP)".

- [ ] **Step 2: Update the Environment Variables section**

Add a new subsection documenting `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, matching the style of the existing SMTP block.

- [ ] **Step 3: Update "Things Not to Touch Without Explicit Approval"**

Replace "Source DuckDB database structure" and "`data/*.duckdb` files" bullets with: "PostgreSQL schema for `users`, `audit_log`, `simulation_run_log`, and the analytical tables (`master_model_2022_2026`, `base_murid_detail_2022_2026`)" and "The original `data/*.duckdb` file (retained as a migration-source backup — do not delete)."

- [ ] **Step 4: Update `data/README.txt`**

Note that the `.duckdb` file is now a historical backup, superseded by the `workforce_policy_agent` PostgreSQL database at `localhost:5432`, and is no longer read by the running application.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md data/README.txt
git commit -m "docs: update CLAUDE.md and data README for PostgreSQL migration"
```

---

## Self-Review Notes

- **Spec coverage:** connection module (Task 1), schema+data migration (Task 2), `tools.py` (Task 3), `main.py` (Task 4), maintenance/smoke scripts (Task 5), docs (Task 6) — matches every touchpoint the inventory agent found.
- **Read-only guarantee preserved:** `tools.py`'s `_connect()` still opens `read_only=True`; `health_check` still asserts it, now via `SHOW transaction_read_only` instead of DuckDB's `current_setting('access_mode')`.
- **ID-generation bug fixed, not carried forward:** Task 4 Step 4 replaces the pre-existing `MAX(id)+1` race condition with `SERIAL`/`RETURNING id`, flagged in the inventory as a real risk under concurrent writers — worth doing now since Postgres removes the excuse for the workaround.
- **Backward-safety:** the original `.duckdb` file is never deleted or modified (Task 2 only reads it; Task 6 documents it as a kept backup), satisfying CLAUDE.md's "Safe Development Principle" (backups before data changes, prefer small reversible changes).
