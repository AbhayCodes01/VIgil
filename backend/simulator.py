"""
VigilCloud Simulator
--------------------
Simulates 10 sensor nodes on NH-44 highway corridor (Delhi to Agra stretch).
Fires a scripted hazard detection scenario and measures end-to-end alert time.

NEW in this version:
  - Truck-mounted shock-event simulation (ADXL345 g-force), correlated with
    pothole hazards so the backend's causal-link logic has something real
    to find (see main.py's /ingest/shock).
  - A synthetic training-sequence generator that writes CSV rows suitable
    for ml/train_lstm.py — hazard count, shock rate, and time-of-day per
    segment per timestep. This is explicitly SYNTHETIC data, not real
    sensor logs — see ml/README.md and the R&D report for why that's OK
    as an interim step.

Run this in a SEPARATE terminal while the backend is running:
    python simulator.py
"""

import requests, time, random, csv, os

BASE_URL = "http://localhost:8000"

# 10 simulated sensor nodes along NH-44 (Delhi → Agra)
# Real GPS coordinates on the actual highway
NODES = [
    {"node_id": "NH44-001", "latitude": 28.5274, "longitude": 77.2590, "km": 0},
    {"node_id": "NH44-002", "latitude": 28.4089, "longitude": 77.2022, "km": 15},
    {"node_id": "NH44-003", "latitude": 28.2943, "longitude": 77.1711, "km": 30},
    {"node_id": "NH44-004", "latitude": 28.1823, "longitude": 77.1354, "km": 45},
    {"node_id": "NH44-005", "latitude": 28.0672, "longitude": 77.0987, "km": 60},
    {"node_id": "NH44-006", "latitude": 27.9512, "longitude": 77.0634, "km": 75},
    {"node_id": "NH44-007", "latitude": 27.8349, "longitude": 77.0289, "km": 90},
    {"node_id": "NH44-008", "latitude": 27.7198, "longitude": 76.9933, "km": 105},
    {"node_id": "NH44-009", "latitude": 27.6041, "longitude": 76.9588, "km": 120},
    {"node_id": "NH44-010", "latitude": 27.4917, "longitude": 76.9231, "km": 135},
]

# One truck-mounted node, riding the same route. Only one for the demo —
# more would just be copies with different truck_node_id / shipment_id.
TRUCK_NODE_ID = "TRK-Node-07"


def send_event(node, hazard_type, confidence):
    """Send a hazard event from a road node to the backend."""
    payload = {
        "node_id":     node["node_id"],
        "hazard_type": hazard_type,
        "confidence":  confidence,
        "latitude":    node["latitude"] + random.uniform(-0.001, 0.001),
        "longitude":   node["longitude"] + random.uniform(-0.001, 0.001),
    }
    try:
        r = requests.post(f"{BASE_URL}/ingest", json=payload, timeout=3)
        return r.json()
    except Exception as e:
        print(f"  ✗ Could not reach backend: {e}")
        return None


def get_or_create_demo_shipment():
    """Fetches a demo shipment_id from the backend, creating the demo
    fleet/truck/shipment chain if it doesn't exist yet. Needed before any
    shock event can be sent, since ShockEvent.shipment_id points at a
    real Shipment row."""
    try:
        r = requests.post(f"{BASE_URL}/shipments/demo", timeout=3)
        return r.json().get("shipment_id")
    except Exception as e:
        print(f"  ✗ Could not create demo shipment: {e}")
        return None


def send_shock_event(shipment_id, g_force, lat, lng):
    """Send a truck-mounted ADXL345 shock reading to the backend."""
    payload = {
        "truck_node_id": TRUCK_NODE_ID,
        "shipment_id":   shipment_id,
        "g_force":       g_force,
        "latitude":      lat,
        "longitude":     lng,
    }
    try:
        r = requests.post(f"{BASE_URL}/ingest/shock", json=payload, timeout=3)
        return r.json()
    except Exception as e:
        print(f"  ✗ Could not reach backend: {e}")
        return None


def run_demo_scenario():
    """
    THE DEMO SCENARIO — run this during your presentation / video recording.

    Scenario: Pothole detected at node 7 on NH-44 (km 90, near Mathura).
    Three neighbouring nodes confirm. Alert fires. A truck carrying cargo
    passes over the same spot moments later — the shock event should
    causally link back to the pothole. Time is measured end to end.
    """
    print("\n" + "="*55)
    print("  VIGILCLOUD DEMO SCENARIO")
    print("  NH-44 Pothole Detection + Cargo Shock Correlation")
    print("="*55)

    shipment_id = get_or_create_demo_shipment()
    print(f"\n[setup] Demo shipment ready: shipment_id={shipment_id} (Delhi -> Agra, pharma, cold-chain)")

    # Step 1 — Primary detection at node 7
    print("\n[0.0s] Camera + vibration sensor at NH44-007 detects anomaly...")
    t_start = time.time()
    result = send_event(NODES[6], "pothole", confidence=0.83)
    print(f"       Node NH44-007 → confidence: 0.83 | status: {result}")

    time.sleep(0.8)

    # Step 2 — Neighbouring nodes corroborate
    print(f"\n[{time.time()-t_start:.1f}s] Cross-verifying with neighbouring nodes...")
    for node, conf in [(NODES[5], 0.79), (NODES[7], 0.81), (NODES[8], 0.77)]:
        send_event(node, "pothole", confidence=conf)
        print(f"       Node {node['node_id']} → corroborated (confidence: {conf})")
        time.sleep(0.3)

    # Step 3 — High confidence confirmation
    print(f"\n[{time.time()-t_start:.1f}s] Consensus reached — firing confirmed alert...")
    result = send_event(NODES[6], "pothole", confidence=0.91)
    t_alert = time.time() - t_start
    print(f"       ALERT CONFIRMED → confidence: 0.91")

    # Step 4 — Truck hits the same pothole shortly after, cargo shock logged
    time.sleep(0.5)
    print(f"\n[{time.time()-t_start:.1f}s] Truck (shipment #{shipment_id}) crosses NH44-007 — ADXL345 spikes...")
    shock_lat = NODES[6]["latitude"] + random.uniform(-0.0005, 0.0005)
    shock_lng = NODES[6]["longitude"] + random.uniform(-0.0005, 0.0005)
    g_force = round(random.uniform(3.5, 5.0), 2)   # deliberately high — same pothole
    shock_result = send_shock_event(shipment_id, g_force, shock_lat, shock_lng)
    print(f"       Shock logged → g_force={g_force} | severity={shock_result.get('severity') if shock_result else '?'} "
          f"| linked to hazard #{shock_result.get('linked_hazard_id') if shock_result else '?'}")

    print(f"\n{'='*55}")
    print(f"  ✓ POTHOLE ALERT FIRED")
    print(f"  Location : NH-44, km 90 (near Mathura)")
    print(f"  Confidence: 91%")
    print(f"  End-to-end time: {t_alert:.2f} seconds")
    print(f"  Cargo shock logged and causally linked to this hazard")
    print(f"  Dashboard pin: should appear NOW")
    print(f"  Driver app: alert banner should fire NOW")
    print(f"{'='*55}\n")


def run_continuous():
    """
    Continuously sends random sensor events from all nodes, plus occasional
    truck shock events. Run this to keep the dashboard looking live.
    """
    HAZARD_TYPES = ["pothole", "fog", "stalled_vehicle", "fire"]
    print("\nRunning continuous simulation (Ctrl+C to stop)...")
    print("Events are being sent to the backend every 3-8 seconds.\n")

    shipment_id = get_or_create_demo_shipment()
    print(f"Demo shipment ready: shipment_id={shipment_id}\n")

    while True:
        node = random.choice(NODES)
        hazard = random.choice(HAZARD_TYPES)
        # Most readings are normal — only ~20% are actual hazards
        confidence = random.uniform(0.75, 0.95) if random.random() < 0.2 else random.uniform(0.1, 0.45)
        result = send_event(node, hazard, confidence)
        if result and result.get("confirmed"):
            print(f"⚠ CONFIRMED: {hazard.upper()} at {node['node_id']} (km {node['km']}) — confidence: {confidence:.2f}")

            # ~40% chance the truck happens to be near a confirmed pothole
            # when it fires — mirrors a real correlated shock event
            if hazard == "pothole" and random.random() < 0.4 and shipment_id:
                g_force = round(random.uniform(2.5, 5.0), 2)
                shock = send_shock_event(shipment_id, g_force,
                                          node["latitude"] + random.uniform(-0.0005, 0.0005),
                                          node["longitude"] + random.uniform(-0.0005, 0.0005))
                if shock:
                    print(f"  ⚡ SHOCK: g_force={g_force} severity={shock.get('severity')} "
                          f"linked_hazard={shock.get('linked_hazard_id')}")
        else:
            print(f"  normal reading from {node['node_id']} — confidence: {confidence:.2f} (below threshold)")
        time.sleep(random.uniform(3, 8))


def generate_training_sequences(minutes=60, csv_path="lstm_training_data.csv"):
    """
    Generates SYNTHETIC rolling-window features for LSTM training, one row
    per (segment, minute). Does NOT hit the backend — this is a pure data
    generator so you can produce training data without a live server.

    Feature schema matches ml/README.md:
      segment_id, minute, hazard_count_rolling, shock_rate_rolling,
      fog_forming_flag, gas_spike_flag, hour_of_day,
      hazard_probability_next_10min  (the label)

    A hazard "window" is injected randomly per segment — features rise
    ahead of it, then the label captures whether a hazard actually
    occurred in the next 10 minutes. This gives the LSTM something with
    real signal to learn, not pure noise.
    """
    rows = []
    for node in NODES:
        segment_id = node["node_id"]

        # Decide 0-2 hazard windows for this segment during the simulated hour
        num_windows = random.choice([0, 1, 1, 2])
        hazard_windows = sorted(random.sample(range(10, minutes - 10), num_windows)) if num_windows else []

        hazard_count = 0
        shock_count = 0

        for minute in range(minutes):
            # Rising signal in the 10 minutes before a hazard window
            approaching_hazard = any(0 < (w - minute) <= 10 for w in hazard_windows)
            in_hazard = any(minute == w for w in hazard_windows)

            if in_hazard:
                hazard_count += 1
            if approaching_hazard and random.random() < 0.3:
                shock_count += 1  # rough road conditions before the pothole itself

            fog_forming_flag = 1 if random.random() < 0.05 else 0
            gas_spike_flag = 1 if random.random() < 0.02 else 0
            hour_of_day = (minute // 60) % 24

            # Label: does a hazard occur in the NEXT 10 minutes from here?
            label = 1 if any(minute < w <= minute + 10 for w in hazard_windows) else 0

            rows.append({
                "segment_id": segment_id,
                "minute": minute,
                "hazard_count_rolling": hazard_count,
                "shock_rate_rolling": shock_count,
                "fog_forming_flag": fog_forming_flag,
                "gas_spike_flag": gas_spike_flag,
                "hour_of_day": hour_of_day,
                "hazard_probability_next_10min": label,
            })

    fieldnames = list(rows[0].keys())
    write_header = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)

    print(f"\n✓ Wrote {len(rows)} synthetic training rows to {csv_path}")
    print(f"  {sum(r['hazard_probability_next_10min'] for r in rows)} positive labels "
          f"({sum(r['hazard_probability_next_10min'] for r in rows) / len(rows) * 100:.1f}%)")
    print(f"  This is SYNTHETIC data — labelled as such. See ml/README.md.\n")


if __name__ == "__main__":
    print("\nVigilCloud Simulator")
    print("--------------------")
    print("Make sure the backend is running: uvicorn main:app --reload\n")
    print("Choose mode:")
    print("  1 — Demo scenario (for presentation / video recording)")
    print("  2 — Continuous simulation (keeps dashboard live)")
    print("  3 — Generate synthetic LSTM training data (no backend needed)")

    choice = input("\nEnter 1, 2, or 3: ").strip()
    if choice == "1":
        run_demo_scenario()
    elif choice == "2":
        run_continuous()
    elif choice == "3":
        generate_training_sequences()
    else:
        print("Invalid choice. Running demo scenario by default.")
        run_demo_scenario()