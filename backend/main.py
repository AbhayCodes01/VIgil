from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import get_db, HazardEvent, Node, Base, engine, FleetOperator, Truck, Shipment, ShockEvent
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


def haversine_km(lat1, lng1, lat2, lng2):
    """Great-circle distance in km. Shared by /hazards/near and the new
    shock-event causal-link lookup — was previously defined inline only
    inside /hazards/near; factored out so both can use it."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.asin(math.sqrt(a))


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
    all_events = db.query(HazardEvent).filter(HazardEvent.confirmed == 1).all()
    nearby = [
        e for e in all_events
        if haversine_km(lat, lng, e.latitude, e.longitude) <= radius_km
    ]
    return [
        {
            "id":           e.id,
            "hazard_type":  e.hazard_type,
            "confidence":   e.confidence,
            "latitude":     e.latitude,
            "longitude":    e.longitude,
            "distance_km":  round(haversine_km(lat, lng, e.latitude, e.longitude), 2),
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


# ---------------------------------------------------------------------------
# NEW — v2 cargo-protection endpoints
# ---------------------------------------------------------------------------

@app.post("/shipments/demo")
def create_demo_shipment(db: Session = Depends(get_db)):
    """
    Creates (or reuses) one demo fleet/truck/shipment chain so the simulator
    has a real shipment_id to attach shock events to, without you having to
    manually build fleet/truck records first. Safe to call repeatedly —
    reuses the same demo fleet/truck if they already exist.
    """
    fleet = db.query(FleetOperator).filter(FleetOperator.name == "Demo Fleet").first()
    if not fleet:
        fleet = FleetOperator(name="Demo Fleet", contact_email="demo@vigilcloud.dev")
        db.add(fleet); db.commit(); db.refresh(fleet)

    truck = db.query(Truck).filter(Truck.plate_no == "DEMO-TRUCK-01").first()
    if not truck:
        truck = Truck(plate_no="DEMO-TRUCK-01", fleet_operator_id=fleet.id)
        db.add(truck); db.commit(); db.refresh(truck)

    shipment = Shipment(
        fleet_operator_id = fleet.id,
        truck_id          = truck.id,
        cargo_type        = "pharma",
        cargo_value_inr   = 850000,
        is_cold_chain     = 1,
        temp_band_min     = 2,
        temp_band_max     = 8,
        route_start       = "Delhi",
        route_end         = "Agra",
        status            = "in_transit",
    )
    db.add(shipment); db.commit(); db.refresh(shipment)

    return {"shipment_id": shipment.id, "truck_id": truck.id, "fleet_operator_id": fleet.id}


@app.post("/ingest/shock")
async def ingest_shock_event(payload: dict, db: Session = Depends(get_db)):
    """
    Receives an ADXL345 g-force reading from a truck-mounted node.

    Severity thresholds below are placeholders — Section 5.3 of the SRS /
    ml/README.md flags that these should come from the MATLAB quarter-car
    simulation, not be hand-picked. Swap them out once that's built.

    Also attempts to causally link the shock to the nearest confirmed
    HazardEvent within 200m / 30s, same idea as ShockEvent.nearby_hazard_id
    in the schema.
    """
    g_force = payload.get("g_force", 0.0)

    if g_force >= 4.0:
        severity = "severe"
    elif g_force >= 2.0:
        severity = "moderate"
    else:
        severity = "minor"

    lat = payload.get("latitude", 0.0)
    lng = payload.get("longitude", 0.0)
    now = datetime.utcnow()

    nearby_hazard_id = None
    recent_hazards = db.query(HazardEvent)\
                        .filter(HazardEvent.confirmed == 1)\
                        .order_by(HazardEvent.timestamp.desc())\
                        .limit(20)\
                        .all()
    for h in recent_hazards:
        dist_km = haversine_km(lat, lng, h.latitude, h.longitude)
        time_diff_s = abs((now - h.timestamp).total_seconds())
        if dist_km <= 0.2 and time_diff_s <= 30:
            nearby_hazard_id = h.id
            break

    shock = ShockEvent(
        truck_node_id     = payload.get("truck_node_id", "unknown"),
        shipment_id       = payload.get("shipment_id"),
        g_force           = g_force,
        severity          = severity,
        latitude          = lat,
        longitude         = lng,
        nearby_hazard_id  = nearby_hazard_id,
        timestamp         = now,
    )
    db.add(shock)
    db.commit()
    db.refresh(shock)

    return {
        "status": "saved",
        "shock_id": shock.id,
        "severity": severity,
        "linked_hazard_id": nearby_hazard_id,
    }


@app.get("/shipments/{shipment_id}/shocks")
def get_shipment_shocks(shipment_id: int, db: Session = Depends(get_db)):
    """Shock-event history for one shipment — used by the fleet dashboard's
    per-shipment panel (SRS FR-FLEET-2)."""
    shocks = db.query(ShockEvent)\
               .filter(ShockEvent.shipment_id == shipment_id)\
               .order_by(ShockEvent.timestamp.desc())\
               .all()
    return [
        {
            "id": s.id,
            "truck_node_id": s.truck_node_id,
            "g_force": s.g_force,
            "severity": s.severity,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "nearby_hazard_id": s.nearby_hazard_id,
            "timestamp": s.timestamp.isoformat(),
        }
        for s in shocks
    ]


@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    """Live WebSocket — dashboard connects here to get real-time hazard events."""
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)