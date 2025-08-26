'''import sqlite3

# connect to database
conn = sqlite3.connect("attendance.db")
cursor = conn.cursor()

# (re)create table with auto-increment roll
cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    roll INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    branch TEXT
)
""")'''

# insert a student (roll auto-generated)
'''cursor.execute("INSERT INTO students (name, branch) VALUES (?, ?)", 
               ("Venkat", "AI DS"))

conn.commit()

# fetch and show all students
cursor.execute("SELECT * FROM students")
rows = cursor.fetchall()

print("📋 Students in table:")
for row in rows:
    print(row)

conn.close()'''

import sqlite3
conn = sqlite3.connect("Teachers.db")
cursor = conn.cursor()
'''cursor.execute(""" create table teachers(
    teacher_id integer primary key,
    name text,
    branch text
)""")'''
cursor.execute("insert into Teachers values(?,?,?)",(1,"hasini","AI dept"))
cursor.execute("insert into Teachers values(?,?,?)",(2,"Talluri","ML dept"))
cursor.execute("select * from Teachers")
rows = cursor.fetchall()
for i in rows:
    print(i)