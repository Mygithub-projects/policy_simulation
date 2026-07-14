import os
import duckdb
import hashlib

# Open database
path = os.path.abspath(os.path.join('data', 'workforce_policy_agent_preclean_20260619_144113.duckdb'))
con = duckdb.connect(path)

# Create password hash
username = 'testuser'
password = 'TestUser123!'
iterations = 260000
salt = 'testsalt2'
hash_bytes = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), iterations)
password_hash = f'pbkdf2_sha256${iterations}${salt}${hash_bytes.hex()}'

# Get max id
max_id = con.execute('SELECT COALESCE(MAX(id), 0) FROM users').fetchone()[0]
new_id = max_id + 1

# Insert user
con.execute(
    'INSERT INTO users (id, username, email, password_hash, role_name, is_active, is_first_login) VALUES (?, ?, ?, ?, ?, ?, ?)',
    [new_id, username, 'testuser@test.com', password_hash, 'user', True, False]
)
con.commit()

print(f'✓ User created: {username}')
print(f'  Password: {password}')
print(f'  Role: user')
print()

# Show all users
print('All users in database:')
rows = con.execute('SELECT id, username, role_name, is_active FROM users ORDER BY id').fetchall()
for row in rows:
    print(f'  {row[0]}: {row[1]} ({row[2]}) - active: {row[3]}')

con.close()
