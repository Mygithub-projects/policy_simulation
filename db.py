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
