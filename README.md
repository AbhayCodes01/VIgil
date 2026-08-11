# VigilCloud

**Edge-AI highway intelligence for road safety and cargo protection — NH-44 (Delhi–Agra) pilot.**

Built for Far Away 2026 (KIIT). Round 2 pivot: buyer expanded from highway authorities (NHAI) to include fleet operators and pharma/cold-chain logistics companies.

---

## What it does

A network of roadside sensor nodes (Raspberry Pi + camera + sensors) detects potholes, fog, fire, and stalled vehicles in real time, cross-verifies alerts across neighbouring nodes, and pushes warnings to drivers and fleet operators within 5 seconds. Truck-mounted nodes additionally log shock events (accelerometer) and feed a live **Cargo Risk Score** per shipment, so logistics companies can see road-condition risk to their freight, not just to driver safety.

**One-line pitch, problem statement, and full "what exactly happens" flow:** see `docs/OnePager_ConceptNote.md` (or the docx version in the project's shared drive).

## Architecture

```
Edge Hardware  →  On-device ML  →  Cloud Backend  →  Fleet Dashboard
(Pi + sensors)    (YOLOv8 + LSTM)   (FastAPI + WS)     (React + Leaflet)
                                          │
                                          └──→  Driver Alert PWA
```

| Layer | Tech | Status |
|---|---|---|
| Edge hardware | Raspberry Pi 4, Pi Camera, DHT22, MQ-2, HC-SR04, MAX9814, ADXL345 | 1 physical node borrowed, not yet wired |
| Computer vision | YOLOv8-nano → ONNX | Not yet fine-tuned (`ml/train_yolo.py` pending) |
| Sequence prediction | PyTorch LSTM | Not yet built |
| Physical simulation | MATLAB quarter-car model | Not yet built — derives shock severity thresholds |
| Backend | FastAPI + SQLAlchemy + WebSockets | **Core hazard pipeline working.** Schema extended for fleet/cargo (see below) |
| Fleet Dashboard | React + Vite + TS + Leaflet.js | Original NHAI dashboard built; fleet fork not started |
| Driver PWA | React + Vite + Workbox + FCM | Not started |

See `ROADMAP.md` for the day-by-day build order and current checkpoint.

## Current build status (source of truth — update as you go)

- [x] `backend/database.py` — HazardEvent + Node (v1), extended with FleetOperator, Truck, Shipment, ShockEvent (v2). Verified working against existing code paths.
- [x] `backend/main.py` — `/ingest`, `/hazards`, `/hazards/near`, `/detect` (mock until `best.pt` exists), `/stats`, `/ws/live`
- [x] `backend/simulator.py` — 10-node NH-44 demo scenario + continuous mode
- [ ] `backend/main.py` — `/shipments/{id}/risk` endpoint (Cargo Risk Score)
- [ ] `backend/simulator.py` — synthetic ShockEvent generator
- [ ] `ml/train_yolo.py`, `ml/evaluate.py` — YOLOv8 fine-tune
- [ ] `ml/train_lstm.py` — hazard prediction model
- [ ] `matlab/quarter_car_sim.m` — shock severity thresholds + disturbance visualization
- [ ] `frontend/fleet-dashboard/` — fork of NHAI dashboard, reframed around shipments
- [ ] `frontend/driver-app/` — driver PWA
- [ ] Physical Pi wired with ADXL345, publishing real MQTT events

## Quick start

```bash
# backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt   # if missing, see backend/README.md
uvicorn main:app --reload

# in a separate terminal — demo scenario
python simulator.py   # choose option 1

# frontend
cd frontend/dashboard
npm install && npm run dev
```

## Repo map

```
backend/     FastAPI app, DB models, simulator      → backend/README.md
ml/          YOLOv8, LSTM training + evaluation      → ml/README.md
matlab/      Quarter-car shock simulation            (pending)
frontend/
  dashboard/     original NHAI ops dashboard (built)
  fleet-dashboard/  fleet/cargo view (pending fork)
  driver-app/       driver PWA (pending)
edge/        Raspberry Pi sensor + inference scripts  (pending)
ROADMAP.md   Live day-by-day build tracker
```

## Team / links

- Author: Abhay · KIIT
- Repo: github.com/AbhayCodes01/VigilCloud
- Docs: PRD v1.0, SRS v2.0, R&D Report, One-Pager Concept Note (shared drive)