'''GET Request Exercise
Create /today_name endpoint:

Takes name in query parameter

Returns { "message": "Hello <name>, today is <current date>" }'''
from fastapi import FastAPI
import datetime

app = FastAPI()
@app.get("/today_name")
def name(name:str):
    return {"Message":f"hello,{name}","Date":str(datetime.date.today())}
