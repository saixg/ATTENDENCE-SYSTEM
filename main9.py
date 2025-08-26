import sqlite3
from fastapi import FastAPI
app = FastAPI()
def hi():
    conn = sqlite3.connect("List.db")
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS list(
        roll_no integer primary key,
        name text,
        branch text )""")
    conn.commit()
    conn.close()
hi()
@app.post("/add_Students")
def h(roll_no:int,name:str,branch:str):
    try:
        conn = sqlite3.connect("List.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO List values(?,?,?)",(roll_no,name,branch))
        conn.commit()
        return {"Message":f"student{name} added succesfully"}
    except sqlite3.IntegrityError:
        return {"message":f"student with roll_no{roll_no}already exists in list"}
    finally:
        conn.close()