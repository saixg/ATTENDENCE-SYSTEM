# api = bridge blw frontend and the backend
#fastApi are the frameworks to run quickly



from fastapi import FastAPI
import datetime

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Hello World! My backend is working 🚀"}

@app.get("/myname")
def my_name():
    return {"name": "Venkat"}

@app.get("/today")
def today():
    return {"date": str(datetime.date.today())}