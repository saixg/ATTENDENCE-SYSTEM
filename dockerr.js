const mongoose = require("mongoose");

mongoose.connect("mongodb://admin:admin123@localhost:27017/attendance_db?authSource=admin")
  .then(() => console.log("Connected to MongoDB"))
  .catch(err => console.error("Error connecting:", err));

const StudentSchema = new mongoose.Schema({
  name: String,
  present: Boolean
});

const Student = mongoose.model("Student", StudentSchema);

// Example insert
Student.create({ name: "Hasini", present: true });
