import sqlite3
from fastapi import FastAPI
app = FastAPI()
def heloo():
    conn = sqlite3.connect("marks.db")
    cursor = conn.cursor()
    cursor.execute("""  CREATE TABLE IF NOT EXISTS style (
        roll_no INTEGER PRIMARY KEY,
        name TEXT,
        branch TEXT
    )
    """)
    conn.commit()
    conn.close( )
heloo()
# -- api conncet to sql
@app.post("/add_student")
def add(roll_no:int,name:str,branch:str):
    conn = sqlite3.connect("marks.db")
    cursor = conn.cursor()
    cursor.execute("insert into style values(?,?,?)",(roll_no,name,branch))
    conn.commit()
    conn.close()
    return{"Message":"Student added succssfully"}
@app.get("/students")
def gets():
    conn = sqlite3.connect("marks.db")
    cursor = conn.cursor()
    cursor.execute("select * from style ")
    rows = cursor.fetchall()
    conn.close()
    return {"message":rows}
