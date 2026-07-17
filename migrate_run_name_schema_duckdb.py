"""One-off migration: adds run_name and is_saved columns to the historical
DuckDB backup file's simulation_run_log table, keeping its schema in sync
with PostgreSQL even though the running application no longer queries this
file at runtime (PostgreSQL is the sole operational database)."""

import duckdb

from config import get_database_path

con = duckdb.connect(str(get_database_path()), read_only=False)
con.execute("ALTER TABLE simulation_run_log ADD COLUMN IF NOT EXISTS run_name VARCHAR")
con.execute("ALTER TABLE simulation_run_log ADD COLUMN IF NOT EXISTS is_saved BOOLEAN DEFAULT FALSE")

print(con.execute("DESCRIBE simulation_run_log").fetchall())
con.close()
