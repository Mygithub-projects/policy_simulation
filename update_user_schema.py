import os
import duckdb

path = os.path.abspath(os.path.join("data", "workforce_policy_agent_preclean_20260619_144113.duckdb"))
con = duckdb.connect(path)
con.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_first_login BOOLEAN DEFAULT TRUE")
con.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP")
con.commit()
print(con.execute("DESCRIBE users").fetchall())
con.close()
