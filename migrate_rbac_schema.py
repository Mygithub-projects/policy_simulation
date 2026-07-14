"""One-off migration: adds audit_log table and users.can_view_audit_log column.
Additive only — does not modify any existing table's existing columns."""

import duckdb

from config import get_database_path

con = duckdb.connect(str(get_database_path()))

con.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY,
        occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        actor_username VARCHAR,
        actor_role VARCHAR,
        action VARCHAR,
        details VARCHAR
    )
""")
con.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS can_view_audit_log BOOLEAN DEFAULT FALSE")
con.commit()

print(con.execute("DESCRIBE audit_log").fetchall())
print(con.execute("DESCRIBE users").fetchall())
con.close()
