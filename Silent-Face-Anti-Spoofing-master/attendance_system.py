import cv2
import os
import sys
import face_recognition
import numpy as np
from datetime import datetime

# Add Silent-Face-Anti-Spoofing repo to Python path
sys.path.append(os.path.join(os.getcwd(), "Silent-Face-Anti-Spoofing-master"))

from src.anti_spoof_predict import AntiSpoofPredict
from src.generate_patches import CropImage
from src.utility import parse_model_name

# Paths
KNOWN_FACES_DIR = "known_faces"
MODEL_DIR = os.path.join( "resources", "anti_spoof_models")
ATTENDANCE_FILE = "Attendance.csv"

# Load anti-spoofing model
model_test = AntiSpoofPredict(0)
image_cropper = CropImage()

# Load known faces
known_encodings, known_names = [], []
for filename in os.listdir(KNOWN_FACES_DIR):
    path = os.path.join(KNOWN_FACES_DIR, filename)
    img = face_recognition.load_image_file(path)
    encoding = face_recognition.face_encodings(img)[0]
    known_encodings.append(encoding)
    known_names.append(os.path.splitext(filename)[0])

# Attendance helper
def mark_attendance(name):
    today = datetime.now().strftime("%Y-%m-%d")
    if not os.path.exists(ATTENDANCE_FILE):
        with open(ATTENDANCE_FILE, "w") as f:
            f.write("Name,Date,Time\n")
    with open(ATTENDANCE_FILE, "r+") as f:
        lines = f.readlines()
        entries = [line.strip().split(",") for line in lines[1:]]
        for entry in entries:
            if entry[0] == name and entry[1] == today:
                return  # already marked today
        now = datetime.now().strftime("%H:%M:%S")
        f.write(f"{name},{today},{now}\n")

# Webcam
cap = cv2.VideoCapture(0)

print("[INFO] Starting attendance system...")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        name, color = "Unknown", (0, 0, 255)

        # Compare with known faces
        matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.5)
        face_distances = face_recognition.face_distance(known_encodings, face_encoding)
        if True in matches:
            best_match = np.argmin(face_distances)
            name = known_names[best_match]

        # Anti-spoofing check
        face_img = frame[top:bottom, left:right]
        if face_img.size > 0:
            prediction = np.zeros((1, 3))
            for model_name in os.listdir(MODEL_DIR):
                model_path = os.path.join(MODEL_DIR, model_name)
                h_input, w_input, model_type, scale = parse_model_name(model_name)
                param = {
                    "org_img": frame,
                    "bbox": (left, top, right, bottom),
                    "scale": scale,
                    "out_w": w_input,
                    "out_h": h_input,
                    "crop": True,
                }
                img = image_cropper.crop(**param)
                prediction += model_test.predict(img, model_path)

            label = np.argmax(prediction)
            if label == 1:  # real
                color = (0, 255, 0)
                if name != "Unknown":
                    mark_attendance(name)

        # Draw face box
        cv2.rectangle(frame, (left, top), (right, bottom), color, 4)
        cv2.putText(frame, name, (left, top - 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)

    cv2.imshow("Attendance System", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
