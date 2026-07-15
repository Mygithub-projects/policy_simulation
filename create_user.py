import hashlib

import db

# Open database
con = db.get_connection(read_only=False)

# Create password hash
username = 'testuser'
password = 'TestUser123!'
iterations = 260000
salt = 'testsalt2'
hash_bytes = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), iterations)
password_hash = f'pbkdf2_sha256${iterations}${salt}${hash_bytes.hex()}'

cursor = con.cursor()

# Get max id
cursor.execute('SELECT COALESCE(MAX(id), 0) FROM users')
max_id = cursor.fetchone()[0]
new_id = max_id + 1

# Insert user
cursor.execute(
    'INSERT INTO users (id, username, email, password_hash, role_name, is_active, is_first_login) VALUES (%s, %s, %s, %s, %s, %s, %s)',
    [new_id, username, 'testuser@test.com', password_hash, 'user', True, False]
)
con.commit()

print(f'✓ User created: {username}')
print(f'  Password: {password}')
print(f'  Role: user')
print()

# Show all users
print('All users in database:')
cursor.execute('SELECT id, username, role_name, is_active FROM users ORDER BY id')
rows = cursor.fetchall()
for row in rows:
    print(f'  {row[0]}: {row[1]} ({row[2]}) - active: {row[3]}')

cursor.close()
con.close()
