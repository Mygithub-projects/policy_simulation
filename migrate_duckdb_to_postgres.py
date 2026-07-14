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
