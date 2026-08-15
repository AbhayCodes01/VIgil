import argparse
import cv2
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--weights",
        default="best.pt",
        help="Path to YOLO weights"
    )
    args = parser.parse_args()

    print(f"Loading YOLO model: {args.weights}")

    model = YOLO(args.weights)

    print("✓ YOLO model loaded")
    print("✓ Starting live camera...")
    print("Press Q to quit.")

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("ERROR: Could not open camera.")
        return

    while True:
        ret, frame = cap.read()

        if not ret:
            print("ERROR: Could not read frame.")
            break

        results = model.predict(
            source=frame,
            conf=0.4,
            iou=0.5,
            verbose=False
        )

        annotated_frame = results[0].plot()

        cv2.imshow("VigilCloud - Live Pothole Detection", annotated_frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()