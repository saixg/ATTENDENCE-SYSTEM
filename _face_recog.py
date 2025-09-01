import os
import cv2
import face_recognition
import numpy as np
import mediapipe as mp
import torch
from ultralytics import YOLO
import cvzone
from datetime import datetime
import csv
import warnings

warnings.filterwarnings("ignore")

# ================== Paths ==================
KNOWN_FACES_DIR = "images"
ATTENDANCE_FILE = "Attendance.csv"
LIVENESS_MODEL_PATH = "l_version_1_300.pt"

# ================== Load YOLO Liveness Model ==================
liveness_model = YOLO(LIVENESS_MODEL_PATH)
classNames = ["fake", "real"]

# ================== Initialize Mediapipe Face Mesh ==================
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

# ================== Blink Detection Helper ==================
def compute_EAR(landmarks, idx1, idx2, idx3, idx4, idx5, idx6, width, height):
    # Eye Aspect Ratio for blink detection
    x1, y1 = int(landmarks[idx1].x * width), int(landmarks[idx1].y * height)
    x2, y2 = int(landmarks[idx2].x * width), int(landmarks[idx2].y * height)
    x3, y3 = int(landmarks[idx3].x * width), int(landmarks[idx3].y * height)
    x4, y4 = int(landmarks[idx4].x * width), int(landmarks[idx4].y * height)
    x5, y5 = int(landmarks[idx5].x * width), int(landmarks[idx5].y * height)
    x6, y6 = int(landmarks[idx6].x * width), int(landmarks[idx6].y * height)

    # vertical distances
    A = np.linalg.norm([x2 - x6, y2 - y6])
    B = np.linalg.norm([x3 - x5, y3 - y5])
    # horizontal distance
    C = np.linalg.norm([x1 - x4, y1 - y4])

    # Avoid division by zero
    if C == 0:
        return 0
    
    ear = (A + B) / (2.0 * C)
    return ear

# Adjusted thresholds
EAR_THRESHOLD = 0.25  # Slightly higher threshold
EAR_FRAMES = 3        # More frames to confirm blink

# ================== Attendance Function ==================
def mark_attendance(name):
    if not os.path.exists(ATTENDANCE_FILE):
        with open(ATTENDANCE_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Time"])
    
    # Check if already marked today
    today = datetime.now().strftime("%Y-%m-%d")
    with open(ATTENDANCE_FILE, "r") as f:
        lines = f.readlines()
        for line in lines:
            if name in line and today in line:
                return  # Already marked today
    
    with open(ATTENDANCE_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([name, now])
        print(f"Attendance marked for {name} at {now}")

# ================== Load Known Faces ==================
known_face_encodings = []
known_face_names = []

print("Loading known faces...")
for file in os.listdir(KNOWN_FACES_DIR):
    if file.lower().endswith(('.jpg', '.jpeg', '.png')):
        path = os.path.join(KNOWN_FACES_DIR, file)
        img = face_recognition.load_image_file(path)
        encodings = face_recognition.face_encodings(img)
        if encodings:  # Check if face was found
            encoding = encodings[0]
            known_face_encodings.append(encoding)
            known_face_names.append(os.path.splitext(file)[0])
            print(f"Loaded face: {os.path.splitext(file)[0]}")

print(f"Total faces loaded: {len(known_face_names)}")

# ================== Rolling buffer for liveness ==================
score_buffer = {}  # key: name, value: list of scores
BUFFER_SIZE = 7    # Increased buffer size
REAL_THRESHOLD = 0.5  # Lowered threshold for better sensitivity
SPOOF_THRESHOLD = 0.3

# ================== Blink tracking ==================
blink_counter = {}
total_blinks = {}
frame_count = {}

# ================== Video Capture ==================
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

print("Starting attendance system... Press 'q' to quit")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Use higher resolution for face detection
    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")
    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

    # Process each detected face
    for face_encoding, face_location in zip(face_encodings, face_locations):
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.6)
        name = "Unknown"

        if True in matches:
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index] and face_distances[best_match_index] < 0.6:
                name = known_face_names[best_match_index]

        # Scale back to original frame size
        top, right, bottom, left = [v * 2 for v in face_location]
        
        # Add some padding for face crop
        padding = 20
        face_crop = frame[max(0, top-padding):bottom+padding, 
                         max(0, left-padding):right+padding]

        # Initialize counters for this person
        if name not in frame_count:
            frame_count[name] = 0
            total_blinks[name] = 0
        frame_count[name] += 1

        # ================== YOLO Liveness Check ==================
        liveness_conf = 0.0
        if face_crop.size > 0 and face_crop.shape[0] > 50 and face_crop.shape[1] > 50:
            try:
                # Resize face crop for better model performance
                resized_crop = cv2.resize(face_crop, (224, 224))
                results = liveness_model(resized_crop, verbose=False)
                
                for r in results:
                    if r.boxes is not None:
                        for box in r.boxes:
                            cls = int(box.cls[0])
                            conf = float(box.conf[0])
                            # Consider both real and fake scores
                            if classNames[cls] == "real":
                                liveness_conf = conf
                            # If fake score is very high, adjust real confidence
                            elif classNames[cls] == "fake" and conf > 0.8:
                                liveness_conf = max(0, liveness_conf - 0.2)
            except Exception as e:
                print(f"YOLO processing error: {e}")

        # ================== Update Rolling Buffer ==================
        if name not in score_buffer:
            score_buffer[name] = []
        score_buffer[name].append(liveness_conf)
        if len(score_buffer[name]) > BUFFER_SIZE:
            score_buffer[name].pop(0)

        avg_conf = sum(score_buffer[name]) / len(score_buffer[name]) if score_buffer[name] else 0

        # ================== Blink Detection ==================
        blinked = False
        if face_crop.size > 0 and face_crop.shape[0] > 50 and face_crop.shape[1] > 50:
            try:
                rgb_face = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
                results_mesh = face_mesh.process(rgb_face)
                
                if results_mesh.multi_face_landmarks:
                    landmarks = results_mesh.multi_face_landmarks[0].landmark
                    h, w, _ = face_crop.shape
                    
                    # Correct eye landmark indices for MediaPipe
                    # Left eye: 362, 385, 387, 263, 373, 380
                    # Right eye: 33, 160, 158, 133, 153, 144
                    ear_left = compute_EAR(landmarks, 362, 385, 387, 263, 373, 380, w, h)
                    ear_right = compute_EAR(landmarks, 33, 160, 158, 133, 153, 144, w, h)
                    
                    ear = (ear_left + ear_right) / 2.0
                    
                    if name not in blink_counter:
                        blink_counter[name] = 0
                        
                    if ear < EAR_THRESHOLD:
                        blink_counter[name] += 1
                    else:
                        if blink_counter[name] >= EAR_FRAMES:
                            blinked = True
                            total_blinks[name] += 1
                        blink_counter[name] = 0
            except Exception as e:
                print(f"Blink detection error: {e}")

        # ================== Final Decision with Multiple Factors ==================
        label = "SPOOF"
        confidence_text = f"Conf: {avg_conf:.2f}"
        
        if name != "Unknown":
            # Calculate blink rate (blinks per 30 frames)
            blink_rate = total_blinks[name] / max(1, frame_count[name] / 30)
            
            # Multiple criteria for real face detection
            criteria_met = 0
            total_criteria = 3
            
            # Criterion 1: YOLO confidence
            if avg_conf >= REAL_THRESHOLD:
                criteria_met += 1
            
            # Criterion 2: Recent blink detected
            if blinked or total_blinks[name] > 0:
                criteria_met += 1
            
            # Criterion 3: Reasonable blink rate (not too high, not zero)
            if 0 < blink_rate < 5:  # Reasonable blink rate
                criteria_met += 1
            
            # Require at least 2 out of 3 criteria for REAL
            if criteria_met >= 2:
                label = "REAL"
                mark_attendance(name)
            elif avg_conf < SPOOF_THRESHOLD and total_blinks[name] == 0:
                label = "SPOOF"
            else:
                label = "SUSPICIOUS"
            
            confidence_text += f" | Blinks: {total_blinks[name]} | Rate: {blink_rate:.1f}"

        # ================== Draw Results ==================
        color = (0, 255, 0) if label == "REAL" else (0, 0, 255) if label == "SPOOF" else (0, 255, 255)
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        
        # Draw name and status
        cv2.putText(frame, f"{name}", (left, top - 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(frame, f"{label}", (left, top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        cv2.putText(frame, confidence_text, (left, bottom + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    # Add system info
    cv2.putText(frame, f"Known faces: {len(known_face_names)}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    cv2.putText(frame, "Press 'q' to quit", (10, frame.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    cv2.imshow("Attendance + Liveness + Blink", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
print("System stopped.")