import cv2
from ultralytics import YOLO

# ============================================================
# MODELS
# ============================================================

ROAD_MODEL_PATH = "last.pt"
GENERAL_MODEL_PATH = "yolo11n.pt"

road_model = YOLO(ROAD_MODEL_PATH)
general_model = YOLO(GENERAL_MODEL_PATH)

# ============================================================
# CONFIGURATION
# ============================================================

ROAD_CONFIDENCE = 0.10
GENERAL_CONFIDENCE = 0.35

# Objects that matter for VigilCloud
VEHICLES = {
    "car",
    "motorcycle",
    "bus",
    "truck"
}

ANIMALS = {
    "dog",
    "horse",
    "sheep",
    "cow",
    "bird"
}

# ============================================================
# CAMERA
# ============================================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    raise RuntimeError("Could not open camera")

print("========================================")
print("       VIGILCLOUD MULTI-HAZARD")
print("========================================")
print("Camera started")
print("Press Q to quit")
print()

while True:

    ret, frame = cap.read()

    if not ret:
        print("Failed to read camera frame")
        break

    # ========================================================
    # ROAD DAMAGE DETECTION
    # ========================================================

    road_results = road_model.predict(
        source=frame,
        conf=ROAD_CONFIDENCE,
        verbose=False
    )

    # ========================================================
    # GENERAL OBJECT DETECTION
    # ========================================================

    general_results = general_model.predict(
        source=frame,
        conf=GENERAL_CONFIDENCE,
        verbose=False
    )

    # ========================================================
    # DRAW ROAD DAMAGE
    # ========================================================

    for result in road_results:

        for box in result.boxes:

            cls_id = int(box.cls[0])
            confidence = float(box.conf[0])

            label = road_model.names[cls_id]

            x1, y1, x2, y2 = map(
                int,
                box.xyxy[0]
            )

            text = f"{label} {confidence:.2f}"

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 0, 255),
                2
            )

            cv2.putText(
                frame,
                text,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2
            )

    # ========================================================
    # DRAW GENERAL OBJECTS
    # ========================================================

    for result in general_results:

        for box in result.boxes:

            cls_id = int(box.cls[0])
            confidence = float(box.conf[0])

            label = general_model.names[cls_id]

            # Ignore irrelevant COCO classes
            if (
                label not in VEHICLES
                and label not in ANIMALS
                and label != "person"
                and label != "bicycle"
            ):
                continue

            x1, y1, x2, y2 = map(
                int,
                box.xyxy[0]
            )

            text = f"{label} {confidence:.2f}"

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                text,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

    # ========================================================
    # DISPLAY
    # ========================================================

    cv2.imshow(
        "VigilCloud - Multi-Hazard Detection",
        frame
    )

    # Q = quit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()