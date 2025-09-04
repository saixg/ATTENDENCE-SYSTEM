import cv2
import time
import argparse
import numpy as np
import os

from src.anti_spoof_predict import AntiSpoofPredict
from src.generate_patches import CropImage
from src.utility import parse_model_name


def main():
    parser = argparse.ArgumentParser(description="Silent-Face-Anti-Spoofing demo with webcam")
    parser.add_argument("--device_id", type=int, default=0, help="Camera device id (default=0)")
    parser.add_argument("--model_dir", type=str, default="./resources/anti_spoof_models", help="Model directory")
    args = parser.parse_args()

    # Initialize
    cap = cv2.VideoCapture(args.device_id)
    model_test = AntiSpoofPredict(device_id=args.device_id)
    image_cropper = CropImage()

    print("[INFO] Starting webcam anti-spoofing demo... Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Failed to capture image from camera")
            break

        image_bbox = model_test.get_bbox(frame)

        # Draw bounding box if face is detected
        if image_bbox is not None:
            cv2.rectangle(frame, (image_bbox[0], image_bbox[1]),
                          (image_bbox[0] + image_bbox[2], image_bbox[1] + image_bbox[3]),
                          (0, 255, 0), 2)

            prediction = np.zeros((1, 3))
            test_speed = 0

            # Run prediction on all models
            for model_name in os.listdir(args.model_dir):
                h_input, w_input, model_type, scale = parse_model_name(model_name)
                model_path = os.path.join(args.model_dir, model_name)

                # Crop face
                param = {"org_img": frame, "bbox": image_bbox, "scale": scale,
                         "out_w": w_input, "out_h": h_input, "crop": True}
                cropped_face = image_cropper.crop(**param)

                # Predict
                start = time.time()
                prediction += model_test.predict(cropped_face, model_path)
                test_speed += time.time() - start

            label = np.argmax(prediction)
            value = prediction[0][label] / 2  # normalize

            if label == 1:
                text = f"Real Face. Score: {value:.2f}"
                color = (0, 255, 0)
            else:
                text = f"Fake Face. Score: {value:.2f}"
                color = (0, 0, 255)

            cv2.putText(frame, text, (image_bbox[0], image_bbox[1] - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        cv2.imshow("Anti-Spoofing Demo", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
