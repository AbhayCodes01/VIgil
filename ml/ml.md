# VigilCloud — ML & Simulation

Three independent pieces. Each can be built and tested on its own before wiring into the backend.

## 1. Computer Vision — YOLOv8 pothole detection

**Status: not started.** Dataset (665 labelled images) exists; training script does not yet.

| File | Purpose | Status |
|---|---|---|
| `train_yolo.py` | Fine-tune YOLOv8-nano in Colab (T4 GPU) | pending |
| `evaluate.py` | mAP50, precision, recall, confusion matrix | pending |
| `best.pt` → `best.onnx` | Exported weights, dropped into `backend/` and `edge/` | pending |

```bash
# in Colab
!pip install ultralytics
python train_yolo.py --data pothole_dataset.yaml --epochs 50 --imgsz 640
python evaluate.py --weights best.pt
```

Target: mAP50 reported honestly (no fixed number assumed pre-training). ≥4 FPS on Raspberry Pi 4 CPU once exported to ONNX.

## 2. LSTM — hazard prediction

**Status: not started.** Depends on synthetic sequence data (Section 3 below, or `simulator.py`'s planned extension).

| File | Purpose | Status |
|---|---|---|
| `train_lstm.py` | Feature engineering + LSTM training | pending |
| `lstm.pt` | Saved weights, loaded by `backend/main.py` at startup | pending |

**Feature vector per segment per timestep:** hazard count (rolling), shock-event rate, sensor-anomaly flags (fog-forming, gas-spike), time-of-day.

**Output:** hazard probability for the next 10 minutes (default horizon, configurable) per road segment.

**Evaluation:** validation loss + AUC against a naive moving-average baseline — the LSTM needs to actually beat the naive baseline, not just exist.

## 3. MATLAB — quarter-car shock simulation

**Status: not started.** This grounds `ShockEvent.severity` thresholds in physics instead of guessed g-force cutoffs, and doubles as synthetic training data for the LSTM until real hardware logs exist.

**Model:** sprung mass (cargo bed) + unsprung mass (wheel), spring-damper pair, driven by a parametrised pothole disturbance (depth, width) at a given truck speed. Solved via `ode45` (or Simulink block diagram — either is fine, same underlying physics).

**Outputs:**
1. Peak sprung-mass acceleration across a speed × pothole-depth sweep → severity thresholds for `minor` / `moderate` / `severe`
2. CSV of acceleration-vs-time curves → LSTM training signal
3. A plot/animation of an acceleration spike crossing a pothole — this is a demo/pitch-deck visual, not just internal validation

**Sanity check (no real data available pre-deadline):** peak acceleration should increase monotonically with both speed and pothole depth. If it doesn't, the model has a bug before it has an accuracy problem.

## Order to build these in

MATLAB doesn't block anything else — build it whenever you have MATLAB time free. YOLO and LSTM are backend-blocking (main.py's `/detect` and `/predict/segment/{id}` need them), so prioritize those first if you're choosing between the two on a given day.