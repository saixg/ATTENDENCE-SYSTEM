import cv2
import os
import sys
import face_recognition
import numpy as np
from datetime import datetime

# ---------- CONFIG ----------
KNOWN_FACES_DIR = "known_faces"
MODEL_DIR = os.path.join("resources", "anti_spoof_models")
ATTENDANCE_FILE = "Attendance.csv"
TOLERANCE = 0.45  # tighter threshold for higher accuracy
FRAME_RESIZE = 0.25  # scale down for faster recognition

# ---------- ANTI-SPOOF IMPORT ----------
sys.path.append(r"Silent-Face-Anti-Spoofing-master")  # safer absolute path is recommended
from src.anti_spoof_predict import AntiSpoofPredict
from src.generate_patches import CropImage
from src.utility import parse_model_name

# ---------- LOAD MODELS ----------
model_test = AntiSpoofPredict(0)
image_cropper = CropImage()

# restrict to .pth models only
anti_spoof_models = [
    m for m in os.listdir(MODEL_DIR) if m.endswith(".pth")
]
if not anti_spoof_models:
    raise RuntimeError("No anti-spoof models found in MODEL_DIR")

# ---------- LOAD KNOWN FACES ----------
known_encodings, known_names = [], []
if not os.path.exists(KNOWN_FACES_DIR):
    raise RuntimeError("KNOWN_FACES_DIR not found")

for filename in os.listdir(KNOWN_FACES_DIR):
    path = os.path.join(KNOWN_FACES_DIR, filename)
    if not (filename.lower().endswith(".jpg") or filename.lower().endswith(".png")):
        continue
    img = face_recognition.load_image_file(path)
    encodings = face_recognition.face_encodings(img)
    if encodings:
        known_encodings.append(encodings[0])
        known_names.append(os.path.splitext(filename)[0])
print(f"[INFO] Loaded {len(known_names)} known faces.")

# ---------- ATTENDANCE ----------
marked_today = set()

def mark_attendance(name):
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M:%S")
    entry = f"{name},{today},{now}\n"

    if not os.path.exists(ATTENDANCE_FILE):
        with open(ATTENDANCE_FILE, "w") as f:
            f.write("Name,Date,Time\n")

    with open(ATTENDANCE_FILE, "a") as f:
        f.write(entry)

    marked_today.add(name)
    print(f"[INFO] Marked attendance for {name} at {now}")

# ---------- VIDEO LOOP ----------
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise RuntimeError("Webcam not accessible")

print("[INFO] Starting attendance system... Press 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # resize frame for faster face detection
    small_frame = cv2.resize(frame, (0, 0), fx=FRAME_RESIZE, fy=FRAME_RESIZE)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    # detect faces
    face_locations = face_recognition.face_locations(rgb_small_frame)
    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        # scale back to original frame size
        top, right, bottom, left = [int(v / FRAME_RESIZE) for v in [top, right, bottom, left]]
        name, color = "Unknown", (0, 0, 255)

        # face recognition
        if known_encodings:
            matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=TOLERANCE)
            face_distances = face_recognition.face_distance(known_encodings, face_encoding)
            if matches and True in matches:
                best_match = np.argmin(face_distances)
                name = known_names[best_match]

        # anti-spoofing
        if name != "Unknown":
            prediction = np.zeros((1, 3))
            for model_name in anti_spoof_models:
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
                if img is None or img.size == 0:
                    continue
                prediction += model_test.predict(img, model_path)

            label = np.argmax(prediction)
            if label == 1:  # real
                color = (0, 255, 0)
                if name not in marked_today:
                    mark_attendance(name)

        # draw UI
        cv2.rectangle(frame, (left, top), (right, bottom), color, 3)
        cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    cv2.imshow("Attendance System", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
