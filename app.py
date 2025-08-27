from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import os

app = Flask(__name__)
CORS(app)  # Allow frontend requests

# Connect to MongoDB Atlas
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://admin:password@cluster0.mongodb.net/attendance")
client = MongoClient(MONGO_URL)
db = client["attendance"]
students = db["students"]

@app.route("/")
def home():
    return {"message": "Backend is running"}

# Mark attendance endpoint
@app.route("/mark_attendance", methods=["POST"])
def mark_attendance():
    data = request.json
    name = data.get("name")
    if not name:
        return jsonify({"error": "Name is required"}), 400

    students.insert_one({"name": name})
    return jsonify({"message": f"Attendance marked for {name}"}), 200

# Get all students
@app.route("/students", methods=["GET"])
def get_students():
    all_students = list(students.find({}, {"_id": 0}))
    return jsonify({"students": all_students})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)