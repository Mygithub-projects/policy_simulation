import db

con = db.get_connection(read_only=False)
cursor = con.cursor()
cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_first_login BOOLEAN DEFAULT TRUE")
cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP")
con.commit()
cursor.execute(
    "SELECT column_name, data_type FROM information_schema.columns "
    "WHERE table_schema = 'g5_p1' AND table_name = 'users' ORDER BY ordinal_position"
)
print(cursor.fetchall())
cursor.close()
con.close()
