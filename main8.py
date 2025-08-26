import sqlite3
from fastapi import FastAPI
app = FastAPI()
def hi():
    conn = sqlite3.connect("Students.db")
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS Student_list(
                   roll_no INTEGER PRIMARY KEY,
                   name TEXT,
                   branch TEXT)""")

    conn.commit()
    conn.close()
hi()
@app.post("/add_Student")
def h(roll_no :int , name:str,branch:str):
    conn = sqlite3.connect("Students.db")
    cursor = conn.cursor()
    cursor.execute("Insert into Student_list values(?,?,?)",(roll_no,name,branch))
    conn.commit()
    conn.close()
    return{"message":"Student added sucssfully"}
@app.get("/students")
def gets():
    conn=sqlite3.connect("Students.db")
    cursor = conn.cursor()
    cursor.execute("Select * from Student_list")
    row = cursor.fetchall()
    conn.close()
    return {"message":row}