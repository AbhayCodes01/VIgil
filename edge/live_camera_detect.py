import cv2
from ultralytics import YOLO

MODEL_PATH = "edge/yolo11n.pt"
CONFIDENCE = 0.55

ROAD_CLASSES = {
    0,  # person
    2,  # car
    3,  # motorcycle
    5,  # bus
    7   # truck
}

print("Loading YOLO11n...")
model = YOLO(MODEL_PATH)

print("Model loaded.")
print("Starting camera...")

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("ERROR: Could not open camera.")
    exit()

print("Camera opened successfully.")
print("Press Q to quit.")

while True:
    success, frame = camera.read()

    if not success:
        print("ERROR: Could not read frame.")
        break

    results = model.predict(
    source=frame,
    conf=CONFIDENCE,
    classes=list(ROAD_CLASSES),
    verbose=False
)

    annotated_frame = results[0].plot()

    cv2.imshow("VigilCloud - Multihazard Object Detection", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()