"""One-off migration: adds audit_log table and users.can_view_audit_log column.
Additive only — does not modify any existing table's existing columns."""

import db

con = db.get_connection(read_only=False)
cursor = con.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY,
        occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        actor_username VARCHAR,
        actor_role VARCHAR,
        action VARCHAR,
        details VARCHAR
    )
""")
cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS can_view_audit_log BOOLEAN DEFAULT FALSE")
con.commit()


def _describe(table_name):
    cursor.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = 'g5_p1' AND table_name = %s ORDER BY ordinal_position",
        [table_name],
    )
    return cursor.fetchall()


print(_describe("audit_log"))
print(_describe("users"))
cursor.close()
con.close()
