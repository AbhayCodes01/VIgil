# VigilCloud — Roadmap & Build Tracker

Living document. Update the checkboxes as you go — this is the single source of truth for "where are we, and what's next," so there's no ambiguity mid-build.

**Deadline:** Far Away 2026 Round 2, Delhi, August 2026.
**Pace:** 2–3 hrs/day, solo build.

---

## Phase 1 — Software core (target: 4 days)

### Day 1 — Schema + synthetic data generator
- [x] `backend/database.py` extended: `FleetOperator`, `Truck`, `Shipment`, `ShockEvent` added; `Node` gets `node_type`. Verified against existing `HazardEvent`/`Node` code paths — no breakage.
- [ ] `backend/simulator.py` extended: emit synthetic `ShockEvent`s correlated with pothole `HazardEvent`s on the same segment/time window; log rolling sensor+hazard windows to CSV (this CSV becomes Day 2's LSTM training data)

### Day 2 — LSTM + risk endpoint
- [ ] `ml/train_lstm.py` — train on Day 1's CSV, save `lstm.pt`
- [ ] `backend/main.py` — `/shipments/{id}/risk` endpoint: combine route hazard density + shock count (+ LSTM output once available) into 0–100 Cargo Risk Score

### Day 3 — YOLOv8
- [ ] `ml/train_yolo.py` — fine-tune in Colab on the 665-image dataset
- [ ] `ml/evaluate.py` — mAP50/precision/recall, recorded honestly
- [ ] Export `best.pt` → ONNX, wire into `backend/main.py`'s `/detect` (replacing the mock response)

### Day 4 — Integration + buffer
- [ ] Simulator → backend → LSTM → risk score, all running together, provably live over `/ws/live`
- [ ] Buffer for whatever breaks (something always does)

## Phase 2 — MATLAB simulation (parallel track, no dependency on Phase 1)

- [ ] `matlab/quarter_car_sim.m` — quarter-car model, speed × pothole-depth sweep
- [ ] Export severity-threshold table → feed into `ShockEvent.severity` logic
- [ ] Export acceleration-vs-time CSV → optional LSTM training signal upgrade
- [ ] Disturbance visualization (plot/animation) for the pitch deck / demo

## Phase 3 — Frontend

- [ ] Fork `frontend/dashboard/` → `frontend/fleet-dashboard/`: reframe stat chips and panels around `Shipment`/`Truck`/Cargo Risk Score
- [ ] `frontend/driver-app/` — driver PWA, cargo-safety indicator added to existing hazard-alert UI

## Phase 4 — Hardware

- [ ] Wire the one physical Raspberry Pi as a truck-node prototype: ADXL345 over I2C, publish real shock events over MQTT into the same pipeline
- [ ] One real hardware node running live during the demo — worth more to judges than ten simulated ones

## Phase 5 — Demo prep

- [ ] Record/rehearse the scripted demo scenario (`simulator.py` option 1) end-to-end
- [ ] Confirm every claim in the R&D report and pitch deck is checkable live — no numbers that can't be shown
- [ ] Update this file's checkboxes to reflect final status before submission

---

## How to use this file

Before each work session: check this file, find the first unchecked box, start there. After each session: check off what actually got done and verified (not just written) — "written but untested" doesn't count as done, per the standard used throughout this build (see `backend/database.py`'s commit — it was extended *and* run against real inserts before being marked complete).