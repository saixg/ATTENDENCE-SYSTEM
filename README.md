HackHertz – AI-Powered Attendance System

    🚨 Problem Statement

Traditional attendance systems are error-prone and vulnerable to misuse:

Proxy attendance: Students mark presence for absent peers.

Manual effort: Teachers waste time on roll calls and validations.

No insights: Institutions lack visibility into attendance patterns and engagement.

     💡 Our Solution

We designed an AI-driven, real-time attendance system with advanced security and insights:

Face Recognition + Liveness Detection → Prevents spoofing via photos, videos, or masks.

AI Insights Dashboard → Generates actionable insights on participation, absenteeism trends, and anomalies.

Automation → Attendance captured seamlessly with minimal human effort.

    🔑 Features

🎥 Real-time face detection using computer vision.

🔒 Liveness verification with anti-spoofing model.

📊 AI-based analytics for student engagement and performance tracking.

🌐 Web-based dashboard for teachers and admins.

⚡ Scalable backend to support classrooms and institutions.

    🛠️ Tech Stack

Python (OpenCV, NumPy, scikit-learn, face_recognition)

Silent-Face-Anti-Spoofing model for liveness detection

Flask / FastAPI for backend services

React.js / Next.js for frontend dashboard

SQLite / PostgreSQL for database storage

    🚀 Setup Instructions

Clone the repository:

git clone https://github.com/saigx/attendance-system.git
cd ATTENDENCE-SYSTTEM


Create virtual environment and install dependencies:

python -m venv face_env  
source face_env/bin/activate  # or face_env\Scripts\activate on Windows  
pip install -r requirements.txt  


Run the backend server:

python app.py  


Access the dashboard at http://localhost:5000/

📈 Future Scope

🔊 Voice-based authentication.

📱 Mobile app integration.

🧠 Deeper AI insights (predictive absenteeism, behavioral trends).

☁️ Hybrid cloud + edge deployment for large campuses.

