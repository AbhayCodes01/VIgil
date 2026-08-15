import cv2
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from ultralytics import YOLO

MODEL_PATH = "best.pt"
CAMERA_INDEX = 0
CONFIDENCE = 0.40
IOU = 0.50

app = FastAPI(title="VigilCloud Edge Camera")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print(f"Loading YOLO model: {MODEL_PATH}")

model = YOLO(MODEL_PATH)

print("YOLO model loaded")
print("Classes:", model.names)

camera = cv2.VideoCapture(CAMERA_INDEX)

if not camera.isOpened():
    print("WARNING: Camera could not be opened")


def generate_frames():
    while True:
        success, frame = camera.read()

        if not success:
            continue

        results = model.predict(
            source=frame,
            conf=CONFIDENCE,
            iou=IOU,
            verbose=False
        )

        annotated_frame = results[0].plot()

        success, buffer = cv2.imencode(".jpg", annotated_frame)

        if not success:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + buffer.tobytes()
            + b"\r\n"
        )


@app.get("/")
def root():
    return {
        "service": "VigilCloud Edge Camera",
        "status": "online",
        "model": MODEL_PATH,
        "classes": model.names
    }


@app.get("/camera/status")
def camera_status():
    return {
        "camera": camera.isOpened(),
        "model": MODEL_PATH,
        "classes": model.names
    }


@app.get("/camera/stream")
def camera_stream():
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )