import os
import duckdb
import hashlib

# Open database
path = os.path.abspath(os.path.join('data', 'workforce_policy_agent_preclean_20260619_144113.duckdb'))
con = duckdb.connect(path)

# Update superadmin password
username = 'superadmin'
password = 'SuperAdmin123!'
iterations = 260000
salt = 'supersalt123'
hash_bytes = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), iterations)
password_hash = f'pbkdf2_sha256${iterations}${salt}${hash_bytes.hex()}'

print(f'Updating {username} password...')
print(f'Generated hash: {password_hash[:80]}...')

# Delete old record and insert new one
con.execute('DELETE FROM users WHERE username = ?', [username])
con.execute(
    'INSERT INTO users (id, username, email, password_hash, role_name, is_active, is_first_login) VALUES (?, ?, ?, ?, ?, ?, ?)',
    [1, username, 'superadmin@example.com', password_hash, 'superadmin', True, False]
)
con.commit()

print(f'✓ Password updated for {username}')
print()

# Verify
result = con.execute('SELECT id, username, role_name, is_active, is_first_login FROM users WHERE username = ?', [username]).fetchall()
if result:
    row = result[0]
    print(f'User verified:')
    print(f'  ID: {row[0]}')
    print(f'  Username: {row[1]}')
    print(f'  Role: {row[2]}')
    print(f'  Active: {row[3]}')
    print(f'  First Login: {row[4]}')
else:
    print('ERROR: User not found!')

con.close()
print()
print('Try logging in with:')
print(f'  Username: {username}')
print(f'  Password: {password}')
