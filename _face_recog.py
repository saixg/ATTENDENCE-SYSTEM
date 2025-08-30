# ===============================  
# AI Attendance System (Blink + Head Movement Liveness)  
# ===============================  

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'



import warnings
import logging
warnings.filterwarnings("ignore")
logging.getLogger("absl").setLevel(logging.ERROR)
logging.getLogger("google").setLevel(logging.ERROR)

import cv2
import face_recognition
import numpy as np
import csv
from datetime import datetime, date
import mediapipe as mp
import time

# -------------------------------  
# Suppress unnecessary logs for clean console  
# -------------------------------  
# -------------------------------  
# Attendance CSV setup  
# -------------------------------  
ATTENDANCE_FILE = "Attendance.csv"
if not os.path.exists(ATTENDANCE_FILE):
    with open(ATTENDANCE_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Time", "Date"])

def is_attendance_done(name):
    today_str = date.today().strftime("%Y-%m-%d")
    if not os.path.exists(ATTENDANCE_FILE):
        return False
    with open(ATTENDANCE_FILE, "r") as f:
        for line in f.readlines()[1:]:
            parts = line.strip().split(",")
            if len(parts) >= 3:
                if parts[0] == name and parts[2] == today_str:
                    return True
    return False

def mark_attendance(name):
    if is_attendance_done(name):
        print(f"ℹ️ Attendance already marked for {name} today.")
        return
    now = datetime.now()
    time_string = now.strftime("%H:%M:%S")
    date_string = now.strftime("%Y-%m-%d")
    with open(ATTENDANCE_FILE, "a", newline="") as f:
        f.write(f"{name},{time_string},{date_string}\n")
    print(f"✅ Attendance marked for {name}")

# -------------------------------  
# Load known faces  
# -------------------------------  
path = 'images'
images = []
student_names = []
for file in os.listdir(path):
    curimg = cv2.imread(os.path.join(path, file))
    if curimg is None:
        print(f"⚠️ Could not load image {file}")
        continue
    images.append(curimg)
    student_names.append(os.path.splitext(file)[0])

def face_encodings(images_list):
    encode_list = []
    for idx, img in enumerate(images_list):
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encodes = face_recognition.face_encodings(img)
        if len(encodes) > 0:
            encode_list.append(encodes[0])
            print(f"✅ Face encoded for {student_names[idx]}")
        else:
            print(f"⚠️ No face found in {student_names[idx]}")
    return encode_list

print("Encoding faces...")
known_encodings = face_encodings(images)
print("Encoding complete!")

# -------------------------------  
# MediaPipe Face Mesh setup  
# -------------------------------  
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True, max_num_faces=1)

# -------------------------------  
# EAR (Eye Aspect Ratio) for blink detection  
# -------------------------------  
def eye_aspect_ratio(landmarks, eye_indices, w, h):
    p1 = np.array([landmarks[eye_indices[1]].x*w, landmarks[eye_indices[1]].y*h])
    p2 = np.array([landmarks[eye_indices[5]].x*w, landmarks[eye_indices[5]].y*h])
    p3 = np.array([landmarks[eye_indices[2]].x*w, landmarks[eye_indices[2]].y*h])
    p4 = np.array([landmarks[eye_indices[4]].x*w, landmarks[eye_indices[4]].y*h])
    p0 = np.array([landmarks[eye_indices[0]].x*w, landmarks[eye_indices[0]].y*h])
    p5 = np.array([landmarks[eye_indices[3]].x*w, landmarks[eye_indices[3]].y*h])
    vertical1 = np.linalg.norm(p2 - p4)
    vertical2 = np.linalg.norm(p3 - p5)
    horizontal = np.linalg.norm(p0 - p1)
    return (vertical1 + vertical2) / (2.0 * horizontal)

EAR_THRESH = 0.25  # blink threshold
HEAD_MOVE_THRESH = 5  # pixels movement for head movement

# -------------------------------  
# Initialize per-student states  
# -------------------------------  
student_state = {}  # stores blinked, head_moved, last nose pos, attendance_marked

# -------------------------------  
# Start webcam  
# -------------------------------  
cap = cv2.VideoCapture(0)
print("Starting webcam... Press 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    h, w, _ = frame.shape
    rgb_small_frame = cv2.cvtColor(cv2.resize(frame, (0,0), fx=0.25, fy=0.25), cv2.COLOR_BGR2RGB)

    # Face recognition
    faces_current = face_recognition.face_locations(rgb_small_frame)
    encodes_current = face_recognition.face_encodings(rgb_small_frame, faces_current)

    # MediaPipe landmarks
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)

    # Process each recognized face
    for encodeFace, faceLoc in zip(encodes_current, faces_current):
        matches = face_recognition.compare_faces(known_encodings, encodeFace)
        face_distances = face_recognition.face_distance(known_encodings, encodeFace)
        best_idx = np.argmin(face_distances)

        if matches[best_idx]:
            name = student_names[best_idx].upper()
            y1,x2,y2,x1 = faceLoc
            y1,x2,y2,x1 = y1*4, x2*4, y2*4, x1*4  # rescale

            # Initialize student state
            if name not in student_state:
                student_state[name] = {"blinked": False,
                                       "head_moved": False,
                                       "attendance_marked": False,
                                       "last_nose_pos": None}

            # Blink detection
            blink_detected = False
            if results.multi_face_landmarks:
                for landmarks in results.multi_face_landmarks:
                    left_eye = [33, 160, 158, 133, 153, 144]
                    right_eye = [362, 385, 387, 263, 373, 380]
                    left_ear = eye_aspect_ratio(landmarks.landmark, left_eye, w, h)
                    right_ear = eye_aspect_ratio(landmarks.landmark, right_eye, w, h)
                    ear = (left_ear + right_ear)/2.0
                    if ear < EAR_THRESH:
                        blink_detected = True

                    # Head movement detection using nose tip (landmark 1)
                    nose = landmarks.landmark[1]
                    nose_pos = np.array([nose.x*w, nose.y*h])
                    last_pos = student_state[name]["last_nose_pos"]
                    if last_pos is not None:
                        if np.linalg.norm(nose_pos - last_pos) > HEAD_MOVE_THRESH:
                            student_state[name]["head_moved"] = True
                    student_state[name]["last_nose_pos"] = nose_pos

            if blink_detected:
                student_state[name]["blinked"] = True

            # Mark attendance if either blink or head movement and not already marked
            if (student_state[name]["blinked"] or student_state[name]["head_moved"]) \
                and not student_state[name]["attendance_marked"]:
                mark_attendance(name)
                student_state[name]["attendance_marked"] = True

            # Draw box
            cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,0),2)
            cv2.putText(frame,name,(x1,y1-40),cv2.FONT_HERSHEY_SIMPLEX,1,(0,255,0),2)

            # Draw tick if attendance marked
            if student_state[name]["attendance_marked"]:
               cv2.circle(frame, (x2-20, y1+20), 15, (0,255,0), -1)  # filled green circle
               cv2.putText(frame, "✔", (x2-28, y1+28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)

            else:
                cv2.putText(frame,"Blink or move head 👁️",(x1,y2+30),cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,0,255),2)

    cv2.imshow("AI Attendance System", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

