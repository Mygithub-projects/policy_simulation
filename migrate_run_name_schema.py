"""One-off migration: adds run_name and is_saved columns to simulation_run_log.
Additive only — does not modify any existing column."""

import db

con = db.get_connection(read_only=False)
cursor = con.cursor()

cursor.execute("ALTER TABLE simulation_run_log ADD COLUMN IF NOT EXISTS run_name VARCHAR")
cursor.execute("ALTER TABLE simulation_run_log ADD COLUMN IF NOT EXISTS is_saved BOOLEAN DEFAULT FALSE")
con.commit()

cursor.execute(
    "SELECT column_name, data_type FROM information_schema.columns "
    "WHERE table_schema = 'g5_p1' AND table_name = 'simulation_run_log' ORDER BY ordinal_position"
)
print(cursor.fetchall())
cursor.close()
con.close()
