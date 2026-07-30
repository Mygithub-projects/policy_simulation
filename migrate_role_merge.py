"""
One-time data migration for the RBAC role merge: collapses the three-role
model (superadmin/admin/user) down to two (superadmin/user) by relabeling
every existing role_name='admin' row to role_name='user'.

No schema change — role_name is a plain VARCHAR with no CHECK constraint
(see migrate_duckdb_to_postgres.py), so this is purely a data update.

Also reports (does not fix) any duplicate or missing emails, since email is
now the login credential — two accounts sharing an email would make login
match an arbitrary one of them.
"""
import db

connection = db.get_connection(read_only=False)
cursor = connection.cursor()

cursor.execute("SELECT id, username, email FROM users WHERE role_name = 'admin' ORDER BY id")
admin_rows = cursor.fetchall()

print(f"Found {len(admin_rows)} account(s) with role_name='admin':")
for user_id, username, email in admin_rows:
    print(f"  id={user_id}  username={username}  email={email}")

if admin_rows:
    cursor.execute("UPDATE users SET role_name = 'user' WHERE role_name = 'admin'")
    connection.commit()
    print(f"\nRelabeled {len(admin_rows)} account(s) from 'admin' to 'user'.")
else:
    print("\nNothing to relabel.")

# Email-uniqueness / completeness check — informational only, since email is
# now the login credential.
cursor.execute(
    "SELECT email, COUNT(*), STRING_AGG(username, ', ') FROM users "
    "GROUP BY email HAVING COUNT(*) > 1"
)
duplicate_emails = cursor.fetchall()
cursor.execute("SELECT username FROM users WHERE email IS NULL OR email = ''")
missing_emails = cursor.fetchall()

print()
if duplicate_emails:
    print("WARNING: duplicate emails found (login will match an arbitrary one of these accounts):")
    for email, count, usernames in duplicate_emails:
        print(f"  {email!r} used by {count} accounts: {usernames}")
else:
    print("No duplicate emails found.")

if missing_emails:
    print("WARNING: accounts with no email on file (cannot log in until fixed):")
    for (username,) in missing_emails:
        print(f"  {username}")
else:
    print("No accounts missing an email.")

cursor.close()
connection.close()
