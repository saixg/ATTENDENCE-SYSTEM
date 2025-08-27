from fastapi import FastAPI
import sqlite3
app = FastAPI()
def intilaze():
    conn = sqlite3.connect("thar.db")
    cursor = conn.cursor()
    cursor.execute(""" CREATE TABLE IF NOT EXISTS STD(
        Enrollment_id integer primary key,
        name text,
        branch text)""")
    conn.commit()
    conn.close()
intilaze()
@app.post("/add_students_table")
def insert(Enrollment_id :int ,name:str, branch:str):
    conn = sqlite3.connect("thar.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO STD VALUES (?,?,?)",(Enrollment_id,name,branch))
    conn.commit()
    conn.close()
    return {"MESSAGE":"student added successfully"}
@app.get("/read_students")
def read():
    conn = sqlite3.connect("thar.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM STD ")
    row = cursor.fetchall()
    conn.close()
    return {"MESSAGE":row}