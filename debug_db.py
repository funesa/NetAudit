import sqlite3
import os

db_path = os.path.join(os.environ['APPDATA'], 'NetAudit Enterprise', 'netaudit.db')
print(f"Checking DB: {db_path}")
print(f"Size: {os.path.getsize(db_path)} bytes")

conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print(f"Tables: {tables}")

for table in tables:
    name = table[0]
    c.execute(f"SELECT COUNT(*) FROM \"{name}\"")
    count = c.fetchone()[0]
    print(f"Table '{name}': {count} rows")

conn.close()
