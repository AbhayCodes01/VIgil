import cv2
import time
import threading
import numpy as np

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
from ultralytics import YOLO


# ============================================================
# PATHS
# ============================================================

EDGE_DIR = Path(__file__).resolve().parent

ROAD_MODEL_PATH = EDGE_DIR / "last.pt"
OBJECT_MODEL_PATH = EDGE_DIR / "yolo11n.pt"
FIRE_MODEL_PATH = EDGE_DIR / "fire_smoke.pt"


# ============================================================
# CONFIGURATION
# ============================================================

CAMERA_INDEX = 0

ROAD_CONFIDENCE = 0.20
OBJECT_CONFIDENCE = 0.40
FIRE_CONFIDENCE = 0.30

IOU = 0.50

# Smaller inference size = faster inference
INFERENCE_SIZE = 512

# Phone upload / processing resolution
PHONE_WIDTH = 640

# JPEG quality
JPEG_QUALITY = 65

# Stalled vehicle detection
STALLED_TIME_SECONDS = 5.0
MOVEMENT_THRESHOLD = 12


# Run expensive models at different intervals.
#
# Object model runs most frequently because it handles
# person/car/truck/bus/motorcycle + stalled vehicles.
#
# Fire and road models don't need to run on every frame.
OBJECT_INTERVAL = 1
FIRE_INTERVAL = 2
ROAD_INTERVAL = 2


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="VigilCloud Multi-Hazard Edge"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# LOAD MODELS
# ============================================================

print("=" * 60)
print("VIGILCLOUD MULTI-HAZARD EDGE")
print("=" * 60)

print(f"Loading object model: {OBJECT_MODEL_PATH}")
object_model = YOLO(str(OBJECT_MODEL_PATH))
print("Object classes:", object_model.names)

print(f"Loading fire/smoke model: {FIRE_MODEL_PATH}")
fire_model = YOLO(str(FIRE_MODEL_PATH))
print("Fire classes:", fire_model.names)

print(f"Loading road model: {ROAD_MODEL_PATH}")
road_model = YOLO(str(ROAD_MODEL_PATH))
print("Road classes:", road_model.names)

print("ALL MODELS LOADED")
print("=" * 60)


# ============================================================
# LAPTOP CAMERA
# ============================================================

camera = cv2.VideoCapture(CAMERA_INDEX)

if camera.isOpened():
    print("Laptop camera: ONLINE")
else:
    print("Laptop camera: OFFLINE")


# ============================================================
# PHONE CAMERA STATE
# ============================================================

phone_lock = threading.Lock()

# Latest frame waiting to be processed.
# IMPORTANT:
# There is only ONE pending frame.
# Old frames are discarded.
pending_phone_frame = None

# Latest processed JPEG
latest_phone_frame = None

# Latest detection data
latest_phone_detections = {
    "objects": [],
    "fire_smoke": [],
    "road_hazards": [],
    "stalled_vehicles": []
}

phone_frame_count = 0
phone_processed_count = 0
phone_last_update = 0
phone_last_processed = 0

phone_worker_running = True


# ============================================================
# VEHICLE TRACKING
# ============================================================

vehicle_tracks = {}


def update_vehicle_tracking(track_id, center):

    now = time.time()

    if track_id not in vehicle_tracks:

        vehicle_tracks[track_id] = {
            "center": center,
            "stationary_since": now
        }

        return False, 0.0

    old = vehicle_tracks[track_id]

    old_x, old_y = old["center"]
    new_x, new_y = center

    movement = (
        (new_x - old_x) ** 2 +
        (new_y - old_y) ** 2
    ) ** 0.5

    if movement > MOVEMENT_THRESHOLD:
        stationary_since = now
    else:
        stationary_since = old["stationary_since"]

    vehicle_tracks[track_id] = {
        "center": center,
        "stationary_since": stationary_since
    }

    duration = now - stationary_since

    return (
        duration >= STALLED_TIME_SECONDS,
        duration
    )


# ============================================================
# AI PROCESSING
# ============================================================

def process_frame(frame, frame_number=0):

    annotated = frame.copy()

    detections = {
        "objects": [],
        "fire_smoke": [],
        "road_hazards": [],
        "stalled_vehicles": []
    }


    # ========================================================
    # 1. OBJECT DETECTION + TRACKING
    # ========================================================

    object_results = object_model.track(
        source=frame,
        conf=OBJECT_CONFIDENCE,
        iou=IOU,
        persist=True,
        tracker="bytetrack.yaml",
        imgsz=INFERENCE_SIZE,
        verbose=False
    )

    result = object_results[0]

    if result.boxes is not None:

        boxes = result.boxes

        for i in range(len(boxes)):

            cls_id = int(boxes.cls[i].item())
            confidence = float(boxes.conf[i].item())

            name = object_model.names[cls_id]

            # Only road-relevant objects
            if name not in [
                "person",
                "car",
                "truck",
                "bus",
                "motorcycle"
            ]:
                continue

            x1, y1, x2, y2 = boxes.xyxy[i].tolist()

            stalled = False
            duration = 0.0

            # ------------------------------------------------
            # STALLED VEHICLE
            # ------------------------------------------------

            if name in [
                "car",
                "truck",
                "bus",
                "motorcycle"
            ]:

                if boxes.id is not None:
                    track_id = int(boxes.id[i].item())
                else:
                    track_id = i

                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)

                stalled, duration = update_vehicle_tracking(
                    track_id,
                    (cx, cy)
                )

            # ------------------------------------------------
            # SAVE OBJECT
            # ------------------------------------------------

            detections["objects"].append({
                "type": name,
                "confidence": round(confidence, 3)
            })

            # ------------------------------------------------
            # DRAW OBJECT
            # ------------------------------------------------

            if stalled:

                detections["stalled_vehicles"].append({
                    "type": name,
                    "confidence": round(confidence, 3),
                    "stationary_seconds": round(duration, 1)
                })

                label = (
                    f"STALLED {name.upper()} "
                    f"{duration:.1f}s"
                )

                box_color = (0, 0, 255)
                thickness = 3

            else:

                label = (
                    f"{name.upper()} "
                    f"{confidence:.2f}"
                )

                box_color = (255, 180, 0)
                thickness = 2

            cv2.rectangle(
                annotated,
                (int(x1), int(y1)),
                (int(x2), int(y2)),
                box_color,
                thickness
            )

            cv2.putText(
                annotated,
                label,
                (
                    int(x1),
                    max(25, int(y1) - 10)
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )


    # ========================================================
    # 2. FIRE / SMOKE
    #
    # Run periodically rather than every frame.
    # ========================================================

    if frame_number % FIRE_INTERVAL == 0:

        fire_results = fire_model.predict(
            source=frame,
            conf=FIRE_CONFIDENCE,
            iou=IOU,
            imgsz=INFERENCE_SIZE,
            verbose=False
        )

        fire_result = fire_results[0]

        if fire_result.boxes is not None:

            for box in fire_result.boxes:

                cls_id = int(box.cls.item())
                confidence = float(box.conf.item())

                x1, y1, x2, y2 = box.xyxy[0].tolist()

                name = fire_model.names[cls_id]

                detections["fire_smoke"].append({
                    "type": name,
                    "confidence": round(confidence, 3)
                })

                label = (
                    f"{name.upper()} "
                    f"{confidence:.2f}"
                )

                cv2.rectangle(
                    annotated,
                    (int(x1), int(y1)),
                    (int(x2), int(y2)),
                    (0, 0, 255),
                    3
                )

                cv2.putText(
                    annotated,
                    label,
                    (
                        int(x1),
                        max(25, int(y1) - 10)
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2
                )


    # ========================================================
    # 3. ROAD HAZARDS
    #
    # Run periodically rather than every frame.
    # ========================================================

    if frame_number % ROAD_INTERVAL == 0:

        road_results = road_model.predict(
            source=frame,
            conf=ROAD_CONFIDENCE,
            iou=IOU,
            imgsz=INFERENCE_SIZE,
            verbose=False
        )

        road_result = road_results[0]

        if road_result.boxes is not None:

            for box in road_result.boxes:

                cls_id = int(box.cls.item())
                confidence = float(box.conf.item())

                x1, y1, x2, y2 = box.xyxy[0].tolist()

                name = road_model.names[cls_id]

                detections["road_hazards"].append({
                    "type": name,
                    "confidence": round(confidence, 3)
                })

                label = (
                    f"{name.upper()} "
                    f"{confidence:.2f}"
                )

                cv2.rectangle(
                    annotated,
                    (int(x1), int(y1)),
                    (int(x2), int(y2)),
                    (0, 165, 255),
                    2
                )

                cv2.putText(
                    annotated,
                    label,
                    (
                        int(x1),
                        max(25, int(y1) - 10)
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 165, 255),
                    2
                )


    # ========================================================
    # HEADER
    # ========================================================

    cv2.rectangle(
        annotated,
        (0, 0),
        (annotated.shape[1], 75),
        (20, 20, 20),
        -1
    )

    cv2.putText(
        annotated,
        "VIGILCLOUD",
        (20, 32),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )

    cv2.putText(
        annotated,
        "LIVE MULTI-HAZARD EDGE AI",
        (20, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (200, 200, 200),
        2
    )

    return annotated, detections


# ============================================================
# JPEG ENCODING
# ============================================================

def encode_frame(frame):

    ok, buffer = cv2.imencode(
        ".jpg",
        frame,
        [
            cv2.IMWRITE_JPEG_QUALITY,
            JPEG_QUALITY
        ]
    )

    if not ok:
        return None

    return buffer.tobytes()


# ============================================================
# PHONE AI WORKER
# ============================================================

def phone_ai_worker():

    global pending_phone_frame
    global latest_phone_frame
    global latest_phone_detections
    global phone_processed_count
    global phone_last_processed

    frame_number = 0

    print("Phone AI worker: STARTED")

    while phone_worker_running:

        frame = None

        # ----------------------------------------------------
        # Get newest frame
        # ----------------------------------------------------

        with phone_lock:

            if pending_phone_frame is not None:

                frame = pending_phone_frame

                # Immediately clear it.
                # If another frame arrives while we're processing,
                # that new frame replaces it.
                pending_phone_frame = None

        if frame is None:

            time.sleep(0.01)
            continue

        # ----------------------------------------------------
        # Process newest available frame
        # ----------------------------------------------------

        frame_number += 1

        try:

            annotated, detections = process_frame(
                frame,
                frame_number
            )

            encoded = encode_frame(annotated)

            if encoded is None:
                continue

            # ------------------------------------------------
            # Save latest processed result
            # ------------------------------------------------

            with phone_lock:

                latest_phone_frame = encoded
                latest_phone_detections = detections

                phone_processed_count += 1
                phone_last_processed = time.time()

        except Exception as error:

            print(
                "PHONE AI ERROR:",
                error
            )

    print("Phone AI worker: STOPPED")


# ============================================================
# START PHONE WORKER
# ============================================================

phone_worker_thread = threading.Thread(
    target=phone_ai_worker,
    daemon=True
)

phone_worker_thread.start()


# ============================================================
# LAPTOP CAMERA STREAM
# ============================================================

def laptop_stream():

    while True:

        ok, frame = camera.read()

        if not ok:

            time.sleep(0.05)
            continue

        frame, _ = process_frame(
            frame,
            int(time.time() * 10)
        )

        data = encode_frame(frame)

        if data is None:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + data
            + b"\r\n"
        )


# ============================================================
# PHONE AI STREAM
# ============================================================

def phone_stream():

    global latest_phone_frame

    while True:

        with phone_lock:
            frame = latest_phone_frame

        if frame is not None:

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + frame
                + b"\r\n"
            )

        time.sleep(0.05)


# ============================================================
# PHONE PAGE
# ============================================================

PHONE_PAGE = """
<!DOCTYPE html>

<html>

<head>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<title>VigilCloud Dashcam</title>

<style>

body {
    margin: 0;
    background: #050505;
    color: white;
    font-family: Arial;
    text-align: center;
}

h2 {
    margin: 15px;
}

video {
    width: 94%;
    max-width: 700px;
    border-radius: 10px;
    background: black;
}

#result {
    width: 94%;
    max-width: 700px;
    margin-top: 10px;
    border-radius: 10px;
    background: black;
}

button {
    margin: 15px;
    padding: 15px 28px;
    font-size: 18px;
    font-weight: bold;
}

#status {
    margin: 10px;
    font-size: 15px;
}

canvas {
    display: none;
}

</style>

</head>


<body>

<h2>VIGILCLOUD DASHCAM</h2>

<div id="status">
    Camera offline
</div>

<video
    id="camera"
    autoplay
    playsinline>
</video>

<br>

<button onclick="startCamera()">
    START CAMERA
</button>

<h3>AI DETECTION</h3>

<img
    id="result"
    src="/phone/stream"
    alt="AI detection feed">

<canvas id="canvas"></canvas>


<script>

const video =
    document.getElementById("camera");

const canvas =
    document.getElementById("canvas");

const statusText =
    document.getElementById("status");

let stream = null;
let sending = false;


async function startCamera() {

    try {

        stream =
            await navigator.mediaDevices.getUserMedia({

                video: {
                    facingMode: {
                        ideal: "environment"
                    },

                    width: {
                        ideal: 1280
                    },

                    height: {
                        ideal: 720
                    }
                },

                audio: false
            });

        video.srcObject = stream;

        statusText.innerText =
            "PHONE CAMERA ACTIVE";

        startSendingFrames();

    }

    catch(error) {

        statusText.innerText =
            "Camera error: " + error.message;

        alert(
            "Camera access failed: "
            + error.message
        );

    }

}


async function sendFrame() {

    if (sending)
        return;

    if (
        !video.videoWidth ||
        !video.videoHeight
    )
        return;

    sending = true;

    try {

        // ------------------------------------------------
        // Resize before upload.
        // This dramatically reduces network traffic.
        // ------------------------------------------------

        const targetWidth = 640;

        const scale =
            targetWidth / video.videoWidth;

        canvas.width =
            targetWidth;

        canvas.height =
            Math.round(
                video.videoHeight * scale
            );

        const ctx =
            canvas.getContext("2d");

        ctx.drawImage(
            video,
            0,
            0,
            canvas.width,
            canvas.height
        );


        const blob =
            await new Promise(resolve =>
                canvas.toBlob(
                    resolve,
                    "image/jpeg",
                    0.60
                )
            );


        await fetch(
            "/phone/frame",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "image/jpeg"
                },

                body: blob
            }
        );


        statusText.innerText =
            "PHONE CAMERA → VIGILCLOUD AI → LIVE";

    }

    catch(error) {

        console.error(error);

        statusText.innerText =
            "Detection connection error";

    }

    finally {

        sending = false;

    }

}


function startSendingFrames() {

    // Upload approximately 4 frames/sec.
    //
    // The server keeps only the newest frame,
    // so it never builds a huge processing queue.

    setInterval(
        sendFrame,
        250
    );

}

</script>

</body>

</html>
"""


# ============================================================
# LAPTOP PHONE DASHBOARD
# ============================================================

PHONE_DASHBOARD = """

<!DOCTYPE html>

<html>

<head>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<title>VigilCloud Phone Monitor</title>

<style>

body {
    margin: 0;
    background: #080808;
    color: white;
    font-family: Arial;
}

header {
    padding: 20px;
    background: #151515;
}

h1 {
    margin: 0;
}

.container {
    padding: 20px;
}

img {
    width: 100%;
    max-width: 1000px;
    background: black;
    border-radius: 10px;
}

.card {
    background: #151515;
    padding: 15px;
    margin-top: 15px;
    border-radius: 10px;
}

.detection {
    padding: 8px;
    border-bottom: 1px solid #333;
}

.status {
    padding: 10px;
    margin-top: 10px;
    background: #202020;
    border-radius: 8px;
}

</style>

</head>


<body>

<header>

<h1>VIGILCLOUD</h1>

<div>
PHONE CAMERA MONITOR
</div>

</header>


<div class="container">

<h2>LIVE PHONE AI FEED</h2>

<img
    src="/phone/stream"
    alt="Phone AI stream">


<div class="card">

<h2>LIVE SYSTEM STATUS</h2>

<div id="status"
     class="status">
    Waiting for phone camera...
</div>

</div>


<div class="card">

<h2>LIVE DETECTIONS</h2>

<div id="detections">
    Waiting for phone camera...
</div>

</div>


</div>


<script>


async function updateDetections() {

    try {

        const response =
            await fetch(
                "/phone/detections"
            );

        const data =
            await response.json();


        document.getElementById(
            "status"
        ).innerHTML =
            "Frames received: "
            + data.frame_count
            + " | AI processed: "
            + data.processed_count;


        let html = "";


        if (
            data.objects.length === 0 &&
            data.fire_smoke.length === 0 &&
            data.road_hazards.length === 0 &&
            data.stalled_vehicles.length === 0
        ) {

            html =
                "No hazards detected";

        }


        for (
            const d of data.objects
        ) {

            html +=
                `<div class="detection">
                    OBJECT:
                    ${d.type}
                    (${d.confidence})
                </div>`;

        }


        for (
            const d of data.fire_smoke
        ) {

            html +=
                `<div class="detection">
                    FIRE/SMOKE:
                    ${d.type}
                    (${d.confidence})
                </div>`;

        }


        for (
            const d of data.road_hazards
        ) {

            html +=
                `<div class="detection">
                    ROAD:
                    ${d.type}
                    (${d.confidence})
                </div>`;

        }


        for (
            const d of data.stalled_vehicles
        ) {

            html +=
                `<div class="detection">
                    STALLED VEHICLE:
                    ${d.type}
                    (${d.stationary_seconds}s)
                </div>`;

        }


        document.getElementById(
            "detections"
        ).innerHTML = html;

    }

    catch(error) {

        console.log(error);

    }

}


setInterval(
    updateDetections,
    500
);

</script>

</body>

</html>

"""


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {

        "service":
            "VigilCloud Multi-Hazard Edge",

        "status":
            "online",

        "camera":
            camera.isOpened(),

        "object_classes":
            object_model.names,

        "fire_classes":
            fire_model.names,

        "road_classes":
            road_model.names,

        "phone_camera":
            "Use /phone",

        "phone_dashboard":
            "Use /phone/dashboard"

    }


# ============================================================
# CAMERA STATUS
# ============================================================

@app.get("/camera/status")
def camera_status():

    with phone_lock:

        received = phone_frame_count
        processed = phone_processed_count

    return {

        "laptop_camera":
            camera.isOpened(),

        "object_model":
            str(OBJECT_MODEL_PATH),

        "fire_model":
            str(FIRE_MODEL_PATH),

        "road_model":
            str(ROAD_MODEL_PATH),

        "phone_frames_received":
            received,

        "phone_frames_processed":
            processed

    }


# ============================================================
# LAPTOP CAMERA
# ============================================================

@app.get("/camera/stream")
def camera_stream():

    return StreamingResponse(

        laptop_stream(),

        media_type=
            "multipart/x-mixed-replace; boundary=frame"

    )


# ============================================================
# PHONE PAGE
# ============================================================

@app.get("/phone")
def phone_camera():

    return HTMLResponse(
        PHONE_PAGE
    )


# ============================================================
# RECEIVE PHONE FRAME
# ============================================================

@app.post("/phone/frame")
async def receive_phone_frame(
    request: Request
):

    global pending_phone_frame
    global phone_frame_count

    data = await request.body()

    if not data:

        return JSONResponse(
            {
                "error":
                    "Empty frame"
            },
            status_code=400
        )


    # ========================================================
    # JPEG → OpenCV
    # ========================================================

    array = np.frombuffer(
        data,
        dtype=np.uint8
    )

    frame = cv2.imdecode(
        array,
        cv2.IMREAD_COLOR
    )


    if frame is None:

        return JSONResponse(
            {
                "error":
                    "Could not decode image"
            },
            status_code=400
        )


    # ========================================================
    # Resize on server as a safety measure
    # ========================================================

    height, width = frame.shape[:2]

    if width > PHONE_WIDTH:

        scale =
            PHONE_WIDTH / width

        frame = cv2.resize(
            frame,
            (
                PHONE_WIDTH,
                int(height * scale)
            ),
            interpolation=cv2.INTER_AREA
        )


    # ========================================================
    # IMPORTANT:
    #
    # Do NOT process AI here.
    #
    # Just replace the pending frame.
    # ========================================================

    with phone_lock:

        pending_phone_frame = frame.copy()

        phone_frame_count += 1


    return JSONResponse({

        "status":
            "received",

        "frame_count":
            phone_frame_count

    })


# ============================================================
# PHONE AI STREAM
# ============================================================

@app.get("/phone/stream")
def phone_live_stream():

    return StreamingResponse(

        phone_stream(),

        media_type=
            "multipart/x-mixed-replace; boundary=frame"

    )


# ============================================================
# PHONE DETECTIONS
# ============================================================

@app.get("/phone/detections")
def phone_detections():

    with phone_lock:

        return {

            "frame_count":
                phone_frame_count,

            "processed_count":
                phone_processed_count,

            "last_update":
                phone_last_update,

            "last_processed":
                phone_last_processed,

            "objects":
                latest_phone_detections[
                    "objects"
                ],

            "fire_smoke":
                latest_phone_detections[
                    "fire_smoke"
                ],

            "road_hazards":
                latest_phone_detections[
                    "road_hazards"
                ],

            "stalled_vehicles":
                latest_phone_detections[
                    "stalled_vehicles"
                ]

        }


# ============================================================
# PHONE DASHBOARD
# ============================================================

@app.get("/phone/dashboard")
def phone_dashboard():

    return HTMLResponse(
        PHONE_DASHBOARD
    )


# ============================================================
# STARTUP
# ============================================================

print()
print("=" * 60)
print("VIGILCLOUD READY")
print("=" * 60)

print("Laptop camera:")
print("  http://localhost:8001/camera/stream")

print()

print("Phone:")
print("  http://localhost:8001/phone")

print()

print("Phone dashboard:")
print("  http://localhost:8001/phone/dashboard")

print("=" * 60)