# ===============================
# Robust Liveness Attendance (ONNX + MediaPipe + MiDaS depth + Challenge)
# ===============================
# - ONNX anti-spoofing (rolling average)
# - MediaPipe blink/head detection
# - Challenge-response (blink / turn)
# - Monocular depth (MiDaS small) to detect flat photos/videos
# - Fusion: require texture (ONNX) + behavior (challenge or passive) + depth variation
# ===============================

import os
import cv2
import numpy as np
import face_recognition
import onnxruntime
import csv
import random
import time
import math
from collections import deque
from datetime import datetime, date

# Optional imports for depth
try:
    import torch
    MIDAS_AVAILABLE = True
except Exception:
    MIDAS_AVAILABLE = False

import mediapipe as mp

# ---------------------------
# CONFIG (tweak these)
# ---------------------------
ONNX_MODEL_PATH = "AntiSpoofing_bin_1.5_128.onnx"
IMAGES_PATH = "images"
ATTENDANCE_FILE = "Attendance.csv"
CAM_INDEX = 0

ROLLING_WINDOW = 7
UPPER_THRESHOLD = -1.0   # ONNX avg > this signals texture confidence for real
LOWER_THRESHOLD = -3.0

BLINK_EAR_THRESHOLD = 0.22
BLINK_MIN_INTERVAL = 0.25

HEAD_TURN_DELTA = 0.025

CHALLENGE_INTERVAL = 8.0
CHALLENGE_TIMEOUT = 4.0
CHALLENGE_TYPES = ["BLINK", "TURN_LEFT", "TURN_RIGHT"]

# Depth config
USE_DEPTH = True
MIDAS_MODEL_TYPE = "MiDaS_small"  # small = faster
MIDAS_IMG_SIZE = 256              # MiDaS input size (smaller->faster but lower res)
DEPTH_VARIATION_THRESHOLD = 0.08  # normalized depth variance threshold — tune on your cam
DEPTH_SMOOTH_WINDOW = 5           # smooth depth variation over frames

# ---------------------------
# Helpers: Attendance CSV
# ---------------------------
if not os.path.exists(ATTENDANCE_FILE):
    with open(ATTENDANCE_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Time", "Date"])

def is_attendance_done(name):
    today_str = date.today().strftime("%Y-%m-%d")
    with open(ATTENDANCE_FILE, "r") as f:
        for line in f.readlines()[1:]:
            parts = line.strip().split(",")
            if len(parts) >= 3 and parts[0] == name and parts[2] == today_str:
                return True
    return False

def mark_attendance(name):
    if is_attendance_done(name):
        print(f"ℹ️ Attendance already marked for {name} today.")
        return
    now = datetime.now()
    with open(ATTENDANCE_FILE, "a", newline="") as f:
        f.write(f"{name},{now.strftime('%H:%M:%S')},{now.strftime('%Y-%m-%d')}\n")
    print(f"✅ Attendance marked for {name}")

# ---------------------------
# Load known faces
# ---------------------------
if not os.path.exists(IMAGES_PATH):
    raise FileNotFoundError(f"Put images named <NAME>.jpg in folder: {IMAGES_PATH}")

images = []
student_names = []
for file in os.listdir(IMAGES_PATH):
    path = os.path.join(IMAGES_PATH, file)
    img = cv2.imread(path)
    if img is None:
        print(f"⚠️ Could not load {file}")
        continue
    images.append(img)
    student_names.append(os.path.splitext(file)[0])

def encode_faces(img_list):
    encs = []
    names = []
    for idx, img in enumerate(img_list):
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        e = face_recognition.face_encodings(rgb)
        if len(e) > 0:
            encs.append(e[0])
            names.append(student_names[idx])
            print(f"✅ Encoded {student_names[idx]}")
        else:
            print(f"⚠️ No face found in {student_names[idx]}")
    return encs, names

print("Encoding known faces...")
known_encodings, known_names = encode_faces(images)
print("Done.")

# ---------------------------
# ONNX model loader
# ---------------------------
ort_session = onnxruntime.InferenceSession(ONNX_MODEL_PATH)

def onnx_predict(face_img):
    try:
        resized = cv2.resize(face_img, (128,128))
    except Exception:
        return -10.0
    lab = cv2.cvtColor(resized, cv2.COLOR_BGR2LAB)
    l,a,b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    cl = clahe.apply(l)
    merged = cv2.merge((cl,a,b))
    rgb = cv2.cvtColor(merged, cv2.COLOR_BGR2RGB)
    inp = rgb.astype(np.float32) / 255.0
    inp = np.transpose(inp, (2,0,1)).astype(np.float32)[np.newaxis, ...]
    outputs = ort_session.run(None, {ort_session.get_inputs()[0].name: inp})
    # model returns scalar score
    try:
        return float(outputs[0][0][0])
    except:
        return float(outputs[0][0])

# ---------------------------
# MiDaS depth setup (optional)
# ---------------------------
midas = None
midas_transform = None
device = "cpu"
if USE_DEPTH and MIDAS_AVAILABLE:
    try:
        import torchvision.transforms as transforms
        # Load MiDaS via torch.hub (first run will download)
        midas = torch.hub.load("intel-isl/MiDaS", MIDAS_MODEL_TYPE)
        midas.to(device)
        midas.eval()
        # Use the default transform from MiDaS repo if available
        try:
            midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
            if MIDAS_MODEL_TYPE == "MiDaS_small":
                midas_transform = midas_transforms.small_transform
            else:
                midas_transform = midas_transforms.default_transform
        except Exception:
            # fallback custom transform
            midas_transform = lambda img: torch.from_numpy(cv2.resize(img, (MIDAS_IMG_SIZE, MIDAS_IMG_SIZE))).permute(2,0,1).unsqueeze(0).float() / 255.0
        print("MiDaS loaded on device:", device)
    except Exception as e:
        print("⚠️ MiDaS load failed - continuing without depth. Error:", e)
        midas = None
        midas_transform = None
elif USE_DEPTH and not MIDAS_AVAILABLE:
    print("⚠️ PyTorch not available; depth disabled. Install torch for depth support.")
    midas = None
    midas_transform = None

def compute_depth_variation(face_img):
    """
    Returns a normalized depth-variation scalar (0..1)
    Higher means more 3D variation (real face). Photo is flatter -> smaller.
    """
    if midas is None or midas_transform is None:
        return None
    # convert BGR to RGB and transform
    img_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
    try:
        inp = midas_transform(img_rgb).to(device)
        with torch.no_grad():
            prediction = midas(inp)
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=img_rgb.shape[:2],
                mode="bicubic",
                align_corners=False
            ).squeeze()
        depth_map = prediction.cpu().numpy()
        # normalize depth to 0..1
        dmin, dmax = np.min(depth_map), np.max(depth_map)
        if dmax - dmin < 1e-6:
            norm = np.zeros_like(depth_map)
        else:
            norm = (depth_map - dmin) / (dmax - dmin)
        # metric: use standard deviation of normalized depth
        variation = float(np.std(norm))
        return variation
    except Exception as e:
        # on any error, fallback to None
        print("⚠️ Depth compute error:", e)
        return None

# Small cache for depth smoothing per name
depth_windows = {}

# ---------------------------
# MediaPipe (behavioral)
# ---------------------------
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

def eye_aspect_ratio(landmarks, left=True):
    if left:
        pts = [33, 160, 158, 133, 153, 144]
    else:
        pts = [362, 385, 387, 263, 373, 380]
    p = [(landmarks[i].x, landmarks[i].y) for i in pts]
    A = math.hypot(p[1][0]-p[5][0], p[1][1]-p[5][1])
    B = math.hypot(p[2][0]-p[4][0], p[2][1]-p[4][1])
    C = math.hypot(p[0][0]-p[3][0], p[0][1]-p[3][1])
    if C == 0:
        return 1.0
    return (A + B) / (2.0 * C)

# ---------------------------
# Session state
# ---------------------------
session_marked = set()
score_windows = {}
prev_label = {}
last_blink_time = 0.0
last_challenge_time = {}
pending_challenge = {}
challenge_passed = {}
prev_nose = {}
face_last_seen = {}

def issue_challenge(name):
    typ = random.choice(CHALLENGE_TYPES)
    pending_challenge[name] = (typ, time.time())
    last_challenge_time[name] = time.time()
    challenge_passed[name] = False
    return typ

# ---------------------------
# Camera loop
# ---------------------------
cap = cv2.VideoCapture(CAM_INDEX)
if not cap.isOpened():
    raise RuntimeError("Cannot open camera.")

print("Starting. Press 'q' to quit.")
while True:
    ret, frame = cap.read()
    if not ret:
        print("⚠️ Camera frame grab failed.")
        break
    h, w = frame.shape[:2]

    # Fast small frame for face_recognition
    rgb_small = cv2.cvtColor(cv2.resize(frame, (0,0), fx=0.25, fy=0.25), cv2.COLOR_BGR2RGB)
    face_locs = face_recognition.face_locations(rgb_small)
    face_encs = face_recognition.face_encodings(rgb_small, face_locs)

    # MediaPipe on full frame for behavior & mesh drawing
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(frame_rgb)

    # compute passive blink and nose x (global)
    blink_flag = False
    nose_x_global = None
    if results.multi_face_landmarks:
        for flm in results.multi_face_landmarks:
            mp_drawing.draw_landmarks(frame, flm, mp_face_mesh.FACEMESH_CONTOURS,
                                      landmark_drawing_spec=mp_drawing.DrawingSpec(color=(0,255,0), thickness=1, circle_radius=1),
                                      connection_drawing_spec=mp_drawing.DrawingSpec(color=(0,128,255), thickness=1))
            left_ear = eye_aspect_ratio(flm.landmark, left=True)
            right_ear = eye_aspect_ratio(flm.landmark, left=False)
            ear = (left_ear + right_ear) / 2.0
            now_t = time.time()
            if ear < BLINK_EAR_THRESHOLD and (now_t - last_blink_time) > BLINK_MIN_INTERVAL:
                blink_flag = True
                last_blink_time = now_t
            nose_x_global = flm.landmark[1].x

    # iterate faces detected by face_recognition (small coords -> upscale)
    for enc, loc in zip(face_encs, face_locs):
        top, right, bottom, left = loc
        top, right, bottom, left = [int(v*4) for v in (top, right, bottom, left)]
        top, left = max(0, top), max(0, left)
        bottom, right = min(h-1, bottom), min(w-1, right)

        # recognize
        name = "UNKNOWN"
        if len(known_encodings) > 0 and enc is not None:
            dists = face_recognition.face_distance(known_encodings, enc)
            best = np.argmin(dists)
            if dists[best] < 0.55:
                name = known_names[best].upper()

        face_last_seen[name] = time.time()

        # prepare per-person containers
        if name not in score_windows:
            score_windows[name] = deque(maxlen=ROLLING_WINDOW)
        if name not in prev_label:
            prev_label[name] = "SUSPICIOUS"
        if name not in prev_nose:
            prev_nose[name] = nose_x_global if nose_x_global is not None else 0.5
        if name not in last_challenge_time:
            last_challenge_time[name] = 0
        if name not in challenge_passed:
            challenge_passed[name] = False
        if name not in depth_windows:
            depth_windows[name] = deque(maxlen=DEPTH_SMOOTH_WINDOW)

        # crop face for predictions
        crop = frame[top:bottom, left:right]
        if crop.size == 0:
            continue

        # ONNX score
        onnx_score = onnx_predict(crop)
        score_windows[name].append(onnx_score)
        avg_score = float(sum(score_windows[name]) / len(score_windows[name]))

        # depth variation
        depth_var = None
        if midas is not None:
            dv = compute_depth_variation(crop)
            if dv is not None:
                depth_windows[name].append(dv)
                depth_var = float(sum(depth_windows[name]) / len(depth_windows[name]))
        # else depth_var remains None

        # per-person head movement using nose x
        per_head_moved = False
        if nose_x_global is not None:
            prev_x = prev_nose[name]
            dx = nose_x_global - prev_x
            if dx < -HEAD_TURN_DELTA:
                per_head_moved = True
                head_left = True
            elif dx > HEAD_TURN_DELTA:
                per_head_moved = True
                head_right = True
            prev_nose[name] = nose_x_global

        # issue challenge if needed
        now = time.time()
        needs_challenge = (not challenge_passed.get(name, False)) and (now - last_challenge_time.get(name, 0) > CHALLENGE_INTERVAL)
        if needs_challenge and name != "UNKNOWN":
            issue_challenge(name)

        # evaluate pending challenge
        ch_passed = False
        if name in pending_challenge:
            ch_type, ch_start = pending_challenge[name]
            if now - ch_start > CHALLENGE_TIMEOUT:
                pending_challenge.pop(name, None)
                challenge_passed[name] = False
            else:
                if ch_type == "BLINK" and blink_flag:
                    ch_passed = True
                if ch_type == "TURN_LEFT" and per_head_moved and dx < 0:
                    ch_passed = True
                if ch_type == "TURN_RIGHT" and per_head_moved and dx > 0:
                    ch_passed = True
                if ch_passed:
                    challenge_passed[name] = True
                    pending_challenge.pop(name, None)

        # behavioral OK: either passed challenge OR passive blink/turn recently
        behavioral_ok = challenge_passed.get(name, False) or blink_flag or per_head_moved

        # Decide label: AND-fusion with hysteresis
        label = prev_label[name]
        # Depth must be present and above threshold for strong check; if depth not available, we allow but warn.
        depth_ok = (depth_var is not None and depth_var > DEPTH_VARIATION_THRESHOLD) if midas is not None else True

        # Final rule:
        # require ONNX avg confident AND behavioral_ok AND depth_ok
        if avg_score > UPPER_THRESHOLD and behavioral_ok and depth_ok:
            label = "REAL"
        elif avg_score < LOWER_THRESHOLD:
            label = "SUSPICIOUS"
        # else keep previous to avoid flicker
        prev_label[name] = label

        # Attendance
        if label == "REAL" and name != "UNKNOWN" and name not in session_marked:
            mark_attendance(name)
            session_marked.add(name)

        # Visual overlays
        color = (0,255,0) if label == "REAL" else (0,0,255)
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        info = f"{name} | {label} | onnx:{avg_score:.2f}"
        if depth_var is not None:
            info += f" depth:{depth_var:.3f}"
        else:
            info += " depth:N/A"
        info += f" blink:{blink_flag} head:{per_head_moved}"
        cv2.putText(frame, info, (left, top-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # challenge overlay
        if name in pending_challenge:
            ctype, cstart = pending_challenge[name]
            remaining = int(CHALLENGE_TIMEOUT - (now - cstart))
            cv2.putText(frame, f"CHALLENGE: {ctype} ({remaining}s)", (left, bottom+20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,165,255), 2)
        else:
            if not challenge_passed.get(name, False) and (now - last_challenge_time.get(name, 0) < CHALLENGE_TIMEOUT):
                cv2.putText(frame, "CHALLENGE FAILED", (left, bottom+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)

    # HUD
    cv2.putText(frame, "Press 'q' to quit", (10,20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,200), 1)
    if midas is None and USE_DEPTH:
        cv2.putText(frame, "Depth DISABLED (install torch to enable)", (10,40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)

    cv2.imshow("Liveness Attendance (MiDaS+ONNX+Behavior)", frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
