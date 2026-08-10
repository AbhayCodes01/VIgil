from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import get_db, HazardEvent, Node, Base, engine
from datetime import datetime
from typing import List
import json, math, numpy as np, cv2, os

# --- Try to load YOLO model if best.pt exists ---
yolo_model = None
try:
    from ultralytics import YOLO
    if os.path.exists("best.pt"):
        yolo_model = YOLO("best.pt")
        print("✓ YOLO model loaded")
    else:
        print("⚠ best.pt not found — /detect will return mock data until you add the model")
except Exception as e:
    print(f"⚠ Could not load YOLO: {e}")

app = FastAPI(title="VigilCloud API", version="1.0")

# Allow frontend on any port to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

# --- WebSocket connection manager ---
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(json.dumps(data))
            except:
                dead.append(ws)
        for ws in dead:
            self.active.remove(ws)

manager = ConnectionManager()

# --- Routes ---

@app.get("/")
def root():
    return {"status": "VigilCloud API running", "model_loaded": yolo_model is not None}


@app.post("/ingest")
async def ingest_sensor_data(payload: dict, db: Session = Depends(get_db)):
    """Receives sensor data from a node. Saves it and broadcasts if confirmed."""
    event = HazardEvent(
        node_id     = payload.get("node_id", "unknown"),
        hazard_type = payload.get("hazard_type", "unknown"),
        confidence  = payload.get("confidence", 0.0),
        latitude    = payload.get("latitude", 0.0),
        longitude   = payload.get("longitude", 0.0),
        confirmed   = 1 if payload.get("confidence", 0) > 0.75 else 0,
        timestamp   = datetime.utcnow(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    # Broadcast to all connected dashboards in real time
    if event.confirmed:
        await manager.broadcast({
            "id":           event.id,
            "node_id":      event.node_id,
            "hazard_type":  event.hazard_type,
            "confidence":   event.confidence,
            "latitude":     event.latitude,
            "longitude":    event.longitude,
            "timestamp":    event.timestamp.isoformat(),
            "confirmed":    True,
        })

    return {"status": "saved", "event_id": event.id, "confirmed": bool(event.confirmed)}


@app.get("/hazards")
def get_hazards(db: Session = Depends(get_db)):
    """Returns all confirmed hazards, newest first."""
    events = db.query(HazardEvent)\
               .filter(HazardEvent.confirmed == 1)\
               .order_by(HazardEvent.timestamp.desc())\
               .limit(50)\
               .all()
    return [
        {
            "id":          e.id,
            "node_id":     e.node_id,
            "hazard_type": e.hazard_type,
            "confidence":  e.confidence,
            "latitude":    e.latitude,
            "longitude":   e.longitude,
            "timestamp":   e.timestamp.isoformat(),
        }
        for e in events
    ]


@app.get("/hazards/near")
def get_hazards_near(lat: float, lng: float, radius_km: float = 5.0, db: Session = Depends(get_db)):
    """Returns confirmed hazards within radius_km of a driver's location."""
    def haversine(lat1, lng1, lat2, lng2):
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
        return R * 2 * math.asin(math.sqrt(a))

    all_events = db.query(HazardEvent).filter(HazardEvent.confirmed == 1).all()
    nearby = [
        e for e in all_events
        if haversine(lat, lng, e.latitude, e.longitude) <= radius_km
    ]
    return [
        {
            "id":           e.id,
            "hazard_type":  e.hazard_type,
            "confidence":   e.confidence,
            "latitude":     e.latitude,
            "longitude":    e.longitude,
            "distance_km":  round(haversine(lat, lng, e.latitude, e.longitude), 2),
            "timestamp":    e.timestamp.isoformat(),
        }
        for e in nearby
    ]


@app.post("/detect")
async def detect_pothole(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Accepts an image, runs YOLO inference, returns detections."""
    contents = await file.read()
    np_arr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if yolo_model is None:
        # Mock response if model not loaded yet
        return {
            "detections": [{"confidence": 0.87, "bbox": [120, 80, 340, 220], "hazard_type": "pothole"}],
            "count": 1,
            "confirmed": True,
            "note": "mock response — add best.pt to backend/ to enable real inference"
        }

    results = yolo_model.predict(img, conf=0.4, iou=0.5, verbose=False)
    detections = []
    for box in results[0].boxes:
        detections.append({
            "confidence":  round(float(box.conf[0]), 3),
            "bbox":        [round(x) for x in box.xyxy[0].tolist()],
            "hazard_type": "pothole"
        })

    confirmed = len(detections) > 0 and detections[0]["confidence"] > 0.6
    return {"detections": detections, "count": len(detections), "confirmed": confirmed}


@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Dashboard stats: total alerts today, breakdown by type."""
    from sqlalchemy import func
    total = db.query(HazardEvent).filter(HazardEvent.confirmed == 1).count()
    by_type = db.query(HazardEvent.hazard_type, func.count(HazardEvent.id))\
                .filter(HazardEvent.confirmed == 1)\
                .group_by(HazardEvent.hazard_type)\
                .all()
    return {
        "total_confirmed": total,
        "by_type": {row[0]: row[1] for row in by_type}
    }


@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    """Live WebSocket — dashboard connects here to get real-time hazard events."""
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)