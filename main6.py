import sqlite3
conn = sqlite3.connect("students.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    roll INTEGER,
    name TEXT,
    branch TEXT
)
""")
cursor.execute("INSERT INTO students values(?,?,?)",(104,"rahul","AI ml"))
cursor.execute("select * from students")
rows = cursor.fetchall()
for i in rows:
    print(i)
conn.commit()
conn.close()