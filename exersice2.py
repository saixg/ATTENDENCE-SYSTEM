
'''
POST Request Exercise
Create /register_student_test endpoint:

Takes name and age in JSON body

Returns { "message": "Student <name> registered" }

Test both endpoints in /docs or browse'''


from fastapi import FastAPI
from pydantic import BaseModel
app =FastAPI()
class Student(BaseModel):
    name:str
    age:int
@app.post("/register_student_test_endpoint")
def register_student_test_endpoint(student:Student):
    return {"Message":f"Student {student.name} (age {student.age}) added successfully"}