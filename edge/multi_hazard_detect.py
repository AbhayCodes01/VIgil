import cv2
import time
from ultralytics import YOLO

# ============================================================
# MODEL PATHS
# ============================================================

OBJECT_MODEL_PATH = "edge/yolo11n.pt"
ROAD_MODEL_PATH = "edge/last.pt"
FIRE_MODEL_PATH = "edge/fire_smoke.pt"

# ============================================================
# CONFIGURATION
# ============================================================

OBJECT_CONFIDENCE = 0.55
ROAD_CONFIDENCE = 0.40
FIRE_CONFIDENCE = 0.40

STALLED_TIME_SECONDS = 5.0
STATIONARY_DISTANCE_PIXELS = 12

# ============================================================
# CLASSES
# ============================================================

OBJECT_CLASSES = {
    0,  # person
    2,  # car
    3,  # motorcycle
    5,  # bus
    7   # truck
}

VEHICLE_CLASSES = {
    2,  # car
    3,  # motorcycle
    5,  # bus
    7   # truck
}

# ============================================================
# LOAD MODELS
# ============================================================

print("Loading VigilCloud models...")

object_model = YOLO(OBJECT_MODEL_PATH)
road_model = YOLO(ROAD_MODEL_PATH)
fire_model = YOLO(FIRE_MODEL_PATH)

print("Object model:", object_model.names)
print("Road model:", road_model.names)
print("Fire model:", fire_model.names)

print("All models loaded successfully.")

# ============================================================
# CAMERA
# ============================================================

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("ERROR: Could not open camera.")
    exit()

print("Camera opened successfully.")
print("Press Q to quit.")

# ============================================================
# VEHICLE TRACKING
# ============================================================

vehicle_tracks = {}

# ============================================================
# MAIN LOOP
# ============================================================

while True:

    success, frame = camera.read()

    if not success:
        print("ERROR: Could not read frame.")
        break

    # ========================================================
    # 1. VEHICLE / PERSON DETECTION
    # ========================================================

    object_results = object_model.track(
        source=frame,
        conf=OBJECT_CONFIDENCE,
        classes=list(OBJECT_CLASSES),
        persist=True,
        tracker="bytetrack.yaml",
        verbose=False
    )

    object_result = object_results[0]

    # ========================================================
    # 2. ROAD DAMAGE DETECTION
    # ========================================================

    road_results = road_model.predict(
        source=frame,
        conf=ROAD_CONFIDENCE,
        verbose=False
    )

    road_result = road_results[0]

    # ========================================================
    # 3. FIRE / SMOKE DETECTION
    # ========================================================

    fire_results = fire_model.predict(
        source=frame,
        conf=FIRE_CONFIDENCE,
        verbose=False
    )

    fire_result = fire_results[0]

    # ========================================================
    # DRAW ROAD HAZARDS
    # ========================================================

    if road_result.boxes is not None:

        for i in range(len(road_result.boxes)):

            box = road_result.boxes[i]

            cls_id = int(box.cls.item())
            confidence = float(box.conf.item())

            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

            class_name = road_model.names[cls_id]

            label = f"{class_name} {confidence:.2f}"

            cv2.rectangle(
                frame,
                (int(x1), int(y1)),
                (int(x2), int(y2)),
                (0, 165, 255),
                2
            )

            cv2.putText(
                frame,
                label,
                (int(x1), max(25, int(y1) - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 165, 255),
                2
            )

    # ========================================================
    # DRAW FIRE / SMOKE
    # ========================================================

    if fire_result.boxes is not None:

        for i in range(len(fire_result.boxes)):

            box = fire_result.boxes[i]

            cls_id = int(box.cls.item())
            confidence = float(box.conf.item())

            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

            class_name = fire_model.names[cls_id]

            label = f"{class_name.upper()} {confidence:.2f}"

            cv2.rectangle(
                frame,
                (int(x1), int(y1)),
                (int(x2), int(y2)),
                (0, 0, 255),
                3
            )

            cv2.putText(
                frame,
                label,
                (int(x1), max(25, int(y1) - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )

    # ========================================================
    # VEHICLE DETECTION + STALLED VEHICLE
    # ========================================================

    if object_result.boxes is not None:

        boxes = object_result.boxes

        for i in range(len(boxes)):

            cls_id = int(boxes.cls[i].item())

            confidence = float(boxes.conf[i].item())

            class_name = object_model.names[cls_id]

            if cls_id not in VEHICLE_CLASSES:
                continue

            if boxes.id is None:
                continue

            track_id = int(boxes.id[i].item())

            x1, y1, x2, y2 = boxes.xyxy[i].cpu().numpy()

            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)

            now = time.time()

            # ------------------------------------------------
            # NEW VEHICLE
            # ------------------------------------------------

            if track_id not in vehicle_tracks:

                vehicle_tracks[track_id] = {
                    "x": center_x,
                    "y": center_y,
                    "stationary_since": now,
                    "stalled": False
                }

            else:

                track = vehicle_tracks[track_id]

                previous_x = track["x"]
                previous_y = track["y"]

                movement = (
                    (center_x - previous_x) ** 2 +
                    (center_y - previous_y) ** 2
                ) ** 0.5

                # ------------------------------------------------
                # VEHICLE MOVED
                # ------------------------------------------------

                if movement > STATIONARY_DISTANCE_PIXELS:

                    track["stationary_since"] = now
                    track["stalled"] = False

                # ------------------------------------------------
                # VEHICLE STATIONARY
                # ------------------------------------------------

                else:

                    stationary_time = (
                        now - track["stationary_since"]
                    )

                    if stationary_time >= STALLED_TIME_SECONDS:

                        track["stalled"] = True

                track["x"] = center_x
                track["y"] = center_y

            track = vehicle_tracks[track_id]

            # ------------------------------------------------
            # DRAW STALLED VEHICLE
            # ------------------------------------------------

            if track["stalled"]:

                stationary_time = (
                    now - track["stationary_since"]
                )

                label = (
                    f"STALLED VEHICLE "
                    f"{stationary_time:.1f}s"
                )

                cv2.rectangle(
                    frame,
                    (int(x1), int(y1)),
                    (int(x2), int(y2)),
                    (0, 0, 255),
                    3
                )

                cv2.putText(
                    frame,
                    label,
                    (int(x1), max(25, int(y1) - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2
                )

            else:

                label = (
                    f"{class_name} "
                    f"{confidence:.2f}"
                )

                cv2.rectangle(
                    frame,
                    (int(x1), int(y1)),
                    (int(x2), int(y2)),
                    (255, 0, 0),
                    2
                )

                cv2.putText(
                    frame,
                    label,
                    (int(x1), max(25, int(y1) - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 0, 0),
                    2
                )

    # ========================================================
    # VIGILCLOUD HEADER
    # ========================================================

    cv2.rectangle(
        frame,
        (0, 0),
        (frame.shape[1], 80),
        (20, 20, 20),
        -1
    )

    cv2.putText(
        frame,
        "VIGILCLOUD",
        (20, 32),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        "MULTI-HAZARD EDGE DETECTION",
        (20, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (200, 200, 200),
        2
    )

    # ========================================================
    # SHOW
    # ========================================================

    cv2.imshow(
        "VigilCloud - Multi-Hazard Detection",
        frame
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# ============================================================
# CLEANUP
# ============================================================

camera.release()
cv2.destroyAllWindows()

print("VigilCloud multi-hazard detector stopped.")