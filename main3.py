#now in day 2 i am doing get vs post 
# 1 get reuqest:
# it is uesd to fetch data from backend
#data send by url
#get - ASK and data is to url 
# Post - DATA send to backend but it will store and send data to the body 
#in this i am not getting in the url i want to go to any json body like fast api or swagger ui in that i am getting the fun of
#add_student and that i am getting to name:"string" age:0 as i enter the details and i am getting the code return in it 
#i got that post will not get in the url it will get in json formt in body only

from fastapi import FastAPI

app = FastAPI()
'''@app.get("/greet")
def greet(name:str):
    return {"message":f"hello,{name}!"}
'''
from pydantic import BaseModel

# Define structure of data
class Student(BaseModel):
    name: str
    age: int

@app.post("/add_student")
def add_student(student: Student):
    return {"message": f"Student {student.name} (age {student.age}) added successfully"}
