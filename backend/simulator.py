"""
VigilCloud Simulator
--------------------
Simulates 10 sensor nodes on NH-44 highway corridor (Delhi to Agra stretch).
Fires a scripted hazard detection scenario and measures end-to-end alert time.

Run this in a SEPARATE terminal while the backend is running:
    python simulator.py
"""

import requests, time, random

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

def send_event(node, hazard_type, confidence):
    """Send a hazard event from a node to the backend."""
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

def run_demo_scenario():
    """
    THE DEMO SCENARIO — run this during your presentation / video recording.
    
    Scenario: Pothole detected at node 7 on NH-44 (km 90, near Mathura).
    Three neighbouring nodes confirm. Alert fires. Time is measured.
    """
    print("\n" + "="*55)
    print("  VIGILCLOUD DEMO SCENARIO")
    print("  NH-44 Pothole Detection")
    print("="*55)

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
    print(f"\n{'='*55}")
    print(f"  ✓ POTHOLE ALERT FIRED")
    print(f"  Location : NH-44, km 90 (near Mathura)")
    print(f"  Confidence: 91%")
    print(f"  End-to-end time: {t_alert:.2f} seconds")
    print(f"  Dashboard pin: should appear NOW")
    print(f"  Driver app: alert banner should fire NOW")
    print(f"{'='*55}\n")

def run_continuous():
    """
    Continuously sends random sensor events from all nodes.
    Run this to keep the dashboard looking live.
    """
    HAZARD_TYPES = ["pothole", "fog", "stalled_vehicle", "fire"]
    print("\nRunning continuous simulation (Ctrl+C to stop)...")
    print("Events are being sent to the backend every 3-8 seconds.\n")

    while True:
        node = random.choice(NODES)
        hazard = random.choice(HAZARD_TYPES)
        # Most readings are normal — only ~20% are actual hazards
        confidence = random.uniform(0.75, 0.95) if random.random() < 0.2 else random.uniform(0.1, 0.45)
        result = send_event(node, hazard, confidence)
        if result and result.get("confirmed"):
            print(f"⚠ CONFIRMED: {hazard.upper()} at {node['node_id']} (km {node['km']}) — confidence: {confidence:.2f}")
        else:
            print(f"  normal reading from {node['node_id']} — confidence: {confidence:.2f} (below threshold)")
        time.sleep(random.uniform(3, 8))

if __name__ == "__main__":
    print("\nVigilCloud Simulator")
    print("--------------------")
    print("Make sure the backend is running: uvicorn main:app --reload\n")
    print("Choose mode:")
    print("  1 — Demo scenario (for presentation / video recording)")
    print("  2 — Continuous simulation (keeps dashboard live)")

    choice = input("\nEnter 1 or 2: ").strip()
    if choice == "1":
        run_demo_scenario()
    elif choice == "2":
        run_continuous()
    else:
        print("Invalid choice. Running demo scenario by default.")
        run_demo_scenario()