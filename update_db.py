import sqlite3

DB_PATH = "database.db"
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Add profile_pic column
try:
    c.execute("ALTER TABLE users ADD COLUMN profile_pic TEXT")
    print("Column 'profile_pic' added.")
except sqlite3.OperationalError:
    print("Column 'profile_pic' already exists.")

# Add description column
try:
    c.execute("ALTER TABLE users ADD COLUMN description TEXT")
    print("Column 'description' added.")
except sqlite3.OperationalError:
    print("Column 'description' already exists.")

conn.commit()
conn.close()
print("Update finished.")
