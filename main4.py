import sqlite3

# connect to database (creates file if not exists)
conn = sqlite3.connect("attendance.db")
cursor = conn.cursor()

# create a table
cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    roll INTEGER PRIMARY KEY,
    name TEXT,
    branch TEXT
)
""")

conn.commit()
conn.close()
