import cv2
import face_recognition
import numpy as np
import os

path = 'images'
images = []
student_names = []
mylist = os.listdir(path)
print("students found:", mylist)

for file in mylist:
    curimg = cv2.imread(f'{path}/{file}')
    images.append(curimg)
    student_names.append(os.path.splitext(file)[0])
def face_encodings(images_list):
    encode_list = []
    for idx, img in enumerate(images_list):
        print(f"Processing image {idx+1}/{len(images_list)}")
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encodes = face_recognition.face_encodings(img)
        if len(encodes) > 0:
            encode = encodes[0]
            encode_list.append(encode)
            print(f"✅ Face encoded for image {idx+1}")
        else:
            print(f"⚠️ No face found in image {idx+1}")
    return encode_list

print("encoding faces....")
known_encodings = face_encodings(images)
print("encoding complete !")
# --- Step 3: Real-time Face Recognition with Webcam ---

print("Starting webcam for real-time recognition...")

cap = cv2.VideoCapture(0)  # 0 = default webcam

while True:
    success, frame = cap.read()   # Capture frame
    if not success:
        print("❌ Failed to grab frame from webcam")
        break

    # Resize frame for faster processing (1/4 size)
    small_frame = cv2.resize(frame, (0, 0), None, 0.25, 0.25)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    # Detect faces + encode them in current frame
    faces_current = face_recognition.face_locations(rgb_small_frame)
    encodes_current = face_recognition.face_encodings(rgb_small_frame, faces_current)

    # Compare with known faces
    for encodeFace, faceLoc in zip(encodes_current, faces_current):
        matches = face_recognition.compare_faces(known_encodings, encodeFace)
        face_distances = face_recognition.face_distance(known_encodings, encodeFace)

        # Best match index
        best_match_index = np.argmin(face_distances)

        if matches[best_match_index]:
            name = student_names[best_match_index].upper()

            # Scale back face location to original frame size
            y1, x2, y2, x1 = faceLoc
            y1, x2, y2, x1 = y1*4, x2*4, y2*4, x1*4

            # Draw rectangle + label
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.rectangle(frame, (x1, y2-35), (x2, y2), (0, 255, 0), cv2.FILLED)
            cv2.putText(frame, name, (x1+6, y2-6), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (255, 255, 255), 2)

    # Show the result
    cv2.imshow("Webcam", frame)

    # Exit on 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
print("face recognized")
cap.release()
cv2.destroyAllWindows()
