import { useState } from "react";
import {
  Activity,
  AlertTriangle,
  Bell,
  Car,
  ChevronRight,
  Circle,
  Cpu,
  Gauge,
  Navigation,
  Radio,
  ShieldAlert,
  Siren,
  Truck,
  Wrench,
  Zap,
} from "lucide-react";

import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  Polyline,
} from "react-leaflet";

import "leaflet/dist/leaflet.css";
import "./App.css";

const hazards = [
  {
    type: "Pothole",
    severity: "CRITICAL",
    confidence: 94,
    location: "NH-44, Delhi",
    vehicle: "VH-042",
    time: "2 min ago",
    color: "red",
  },
  {
    type: "Alligator Crack",
    severity: "HIGH",
    confidence: 88,
    location: "NH-48, Gurugram",
    vehicle: "VH-018",
    time: "8 min ago",
    color: "orange",
  },
  {
    type: "Transverse Crack",
    severity: "MEDIUM",
    confidence: 81,
    location: "Yamuna Expressway",
    vehicle: "VH-031",
    time: "14 min ago",
    color: "yellow",
  },
];

const fleet = [
  {
    id: "VH-042",
    route: "Delhi → Agra",
    status: "Critical",
    speed: "62 km/h",
  },
  {
    id: "VH-018",
    route: "Gurugram → Jaipur",
    status: "Warning",
    speed: "71 km/h",
  },
  {
    id: "VH-031",
    route: "Noida → Agra",
    status: "Normal",
    speed: "68 km/h",
  },
  {
    id: "VH-017",
    route: "Delhi → Panipat",
    status: "Normal",
    speed: "74 km/h",
  },
];

function StatCard({ icon: Icon, label, value, sub, danger }) {
  return (
    <div className={`stat-card ${danger ? "danger-card" : ""}`}>
      <div className="stat-icon">
        <Icon size={19} />
      </div>

      <div className="stat-content">
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{sub}</small>
      </div>
    </div>
  );
}

function SeverityBadge({ severity }) {
  return (
    <span className={`severity ${severity.toLowerCase()}`}>
      <Circle size={7} fill="currentColor" />
      {severity}
    </span>
  );
}

function App() {
  const [activeTab, setActiveTab] = useState("overview");
  const [selectedHazard, setSelectedHazard] = useState(null);

  const mapCenter = [28.6139, 77.209];

  const route = [
    [28.6139, 77.209],
    [28.4595, 77.0266],
    [28.4089, 77.3178],
    [27.8974, 78.088],
    [27.1767, 78.0081],
  ];

  const mapHazards = [
    {
      position: [28.6139, 77.209],
      type: "Pothole",
      severity: "CRITICAL",
    },
    {
      position: [28.4595, 77.0266],
      type: "Alligator Crack",
      severity: "HIGH",
    },
    {
      position: [28.4089, 77.3178],
      type: "Transverse Crack",
      severity: "MEDIUM",
    },
    {
      position: [27.8974, 78.088],
      type: "Pothole",
      severity: "CRITICAL",
    },
  ];

  return (
    <div className="app-shell">
      {/* TOP BAR */}
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <Zap size={20} fill="currentColor" />
          </div>

          <div>
            <h1>
              VIGIL<span>CLOUD</span>
            </h1>
            <p>ROAD INTELLIGENCE NETWORK</p>
          </div>
        </div>

        <div className="top-status">
          <div className="route-chip">
            <Navigation size={14} />
            <div>
              <strong>NH-44</strong>
              <span>DELHI → AGRA</span>
            </div>
          </div>

          <div className="system-time">
            <span>SYSTEM TIME</span>
            <strong>00:06:13</strong>
          </div>

          <div className="live-chip">
            <span />
            LIVE
          </div>
        </div>
      </header>

      {/* NAVIGATION */}
      <nav className="navigation">
        {[
          ["overview", "Command Center"],
          ["map", "Hazard Map"],
          ["fleet", "Fleet"],
          ["incidents", "Incidents"],
          ["maintenance", "Maintenance"],
        ].map(([id, label]) => (
          <button
            key={id}
            className={activeTab === id ? "nav-active" : ""}
            onClick={() => setActiveTab(id)}
          >
            {label}
          </button>
        ))}

        <div className="nav-system">
          <span className="online-dot" />
          ALL SYSTEMS OPERATIONAL
        </div>
      </nav>

      <main>
        {/* KPI ROW */}
        <section className="stats-grid">
          <StatCard
            icon={ShieldAlert}
            label="ACTIVE HAZARDS"
            value="07"
            sub="3 critical"
            danger
          />

          <StatCard
            icon={Truck}
            label="FLEET ACTIVE"
            value="118"
            sub="92% connected"
          />

          <StatCard
            icon={Activity}
            label="DETECTIONS / HR"
            value="42"
            sub="+18% vs previous hour"
          />

          <StatCard
            icon={Gauge}
            label="FLEET RISK INDEX"
            value="72"
            sub="Elevated"
            danger
          />

          <StatCard
            icon={Cpu}
            label="EDGE NODES"
            value="10 / 10"
            sub="All reporting"
          />
        </section>

        {/* MAIN WORKSPACE */}
        <section className="workspace">
          {/* MAP */}
          <div className="map-card">
            <div className="card-header">
              <div>
                <span className="eyebrow">
                  LIVE GEOSPATIAL MONITORING
                </span>
                <h2>National Hazard Map</h2>
              </div>

              <div className="map-controls">
                <span className="map-legend">
                  <i className="legend-critical" />
                  Critical
                </span>

                <span className="map-legend">
                  <i className="legend-warning" />
                  Warning
                </span>

                <span className="map-legend">
                  <i className="legend-medium" />
                  Medium
                </span>
              </div>
            </div>

            <div className="map-wrapper">
              <MapContainer
                center={mapCenter}
                zoom={7}
                scrollWheelZoom
                className="leaflet-map"
              >
                <TileLayer
                  attribution="&copy; OpenStreetMap contributors"
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />

                <Polyline
                  positions={route}
                  pathOptions={{
                    color: "#f5a623",
                    weight: 4,
                    opacity: 0.85,
                  }}
                />

                {mapHazards.map((hazard, index) => (
                  <CircleMarker
                    key={index}
                    center={hazard.position}
                    radius={10}
                    pathOptions={{
                      color:
                        hazard.severity === "CRITICAL"
                          ? "#ff3b30"
                          : hazard.severity === "HIGH"
                            ? "#ff8a00"
                            : "#f5c542",
                      fillOpacity: 0.8,
                    }}
                    eventHandlers={{
                      click: () => setSelectedHazard(hazard),
                    }}
                  >
                    <Popup>
                      <strong>{hazard.type}</strong>
                      <br />
                      Severity: {hazard.severity}
                    </Popup>
                  </CircleMarker>
                ))}
              </MapContainer>

              <div className="map-overlay">
                <div className="overlay-title">
                  <Radio size={14} />
                  LIVE EDGE NETWORK
                </div>

                <div className="overlay-value">
                  10 <span>NODES</span>
                </div>

                <div className="overlay-status">
                  <span />
                  STREAMING
                </div>
              </div>
            </div>
          </div>

          {/* INTELLIGENCE PANEL */}
          <aside className="intelligence-panel">
            <div className="panel-heading">
              <div>
                <span className="eyebrow">EDGE INTELLIGENCE</span>
                <h2>Live Detection Feed</h2>
              </div>

              <div className="event-count">
                <Bell size={15} />
                07
              </div>
            </div>

            <div className="camera-box">
              <div className="camera-top">
                <span>CAM-042</span>

                <span className="recording">
                  <i />
                  RECORDING
                </span>
              </div>

              <div className="camera-placeholder">
                <Car size={42} />

                <strong>LIVE CAMERA STREAM</strong>

                <span>VH-042 · NH-44</span>

                <div className="scan-line" />
              </div>

              <div className="camera-bottom">
                <span>YOLO EDGE</span>
                <strong>17.5 ms</strong>
              </div>
            </div>

            <div className="panel-section">
              <div className="section-title">
                <span>RECENT DETECTIONS</span>
                <button>VIEW ALL</button>
              </div>

              <div className="detection-list">
                {hazards.map((hazard, index) => (
                  <button
                    className="detection"
                    key={index}
                    onClick={() => setSelectedHazard(hazard)}
                  >
                    <div className={`hazard-icon ${hazard.color}`}>
                      <AlertTriangle size={17} />
                    </div>

                    <div className="detection-info">
                      <strong>{hazard.type}</strong>
                      <span>
                        {hazard.location} · {hazard.time}
                      </span>
                    </div>

                    <div className="detection-confidence">
                      <b>{hazard.confidence}%</b>
                      <small>CONF.</small>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </aside>
        </section>

        {/* LOWER SECTION */}
        <section className="lower-grid">
          {/* FLEET */}
          <div className="content-card">
            <div className="card-header compact">
              <div>
                <span className="eyebrow">FLEET OPERATIONS</span>
                <h2>Vehicle Status</h2>
              </div>

              <button className="outline-button">
                Fleet Overview
                <ChevronRight size={15} />
              </button>
            </div>

            <div className="fleet-table">
              <div className="table-head">
                <span>VEHICLE</span>
                <span>ROUTE</span>
                <span>SPEED</span>
                <span>STATUS</span>
              </div>

              {fleet.map((vehicle) => (
                <div className="fleet-row" key={vehicle.id}>
                  <div className="vehicle">
                    <div className="vehicle-icon">
                      <Truck size={16} />
                    </div>

                    <strong>{vehicle.id}</strong>
                  </div>

                  <span>{vehicle.route}</span>
                  <span>{vehicle.speed}</span>

                  <span
                    className={`vehicle-status ${vehicle.status.toLowerCase()}`}
                  >
                    <i />
                    {vehicle.status}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* INCIDENTS */}
          <div className="content-card">
            <div className="card-header compact">
              <div>
                <span className="eyebrow">INCIDENT MANAGEMENT</span>
                <h2>Response Queue</h2>
              </div>

              <Siren size={20} />
            </div>

            <div className="incident-summary">
              <div className="incident-number critical">
                <strong>03</strong>
                <span>Critical</span>
              </div>

              <div className="incident-number warning">
                <strong>02</strong>
                <span>Warning</span>
              </div>

              <div className="incident-number normal">
                <strong>02</strong>
                <span>Monitoring</span>
              </div>
            </div>

            <div className="maintenance-alert">
              <div>
                <Wrench size={18} />
              </div>

              <section>
                <strong>Maintenance action required</strong>
                <span>
                  VH-042 · Pothole detected on active route
                </span>
              </section>

              <button>OPEN</button>
            </div>
          </div>
        </section>

        {/* SYSTEM STATUS */}
        <section className="system-bar">
          <div className="system-item">
            <span className="status-green" />
            <div>
              <small>BACKEND</small>
              <strong>ONLINE</strong>
            </div>
          </div>

          <div className="system-item">
            <span className="status-green" />
            <div>
              <small>WEBSOCKET</small>
              <strong>CONNECTED</strong>
            </div>
          </div>

          <div className="system-item">
            <span className="status-yellow" />
            <div>
              <small>ML ENGINE</small>
              <strong>YOLO11 EDGE</strong>
            </div>
          </div>

          <div className="system-item">
            <span className="status-green" />
            <div>
              <small>DATABASE</small>
              <strong>HEALTHY</strong>
            </div>
          </div>

          <div className="system-version">
            VIGILCLOUD v0.1 · COMMAND CENTER
          </div>
        </section>
      </main>

      {/* HAZARD MODAL */}
      {selectedHazard && (
        <div
          className="modal-backdrop"
          onClick={() => setSelectedHazard(null)}
        >
          <div
            className="hazard-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-header">
              <div>
                <span className="eyebrow">HAZARD INCIDENT</span>
                <h2>{selectedHazard.type}</h2>
              </div>

              <button onClick={() => setSelectedHazard(null)}>
                ×
              </button>
            </div>

            <SeverityBadge severity={selectedHazard.severity} />

            <div className="modal-grid">
              <div>
                <span>CONFIDENCE</span>
                <strong>
                  {selectedHazard.confidence || "—"}%
                </strong>
              </div>

              <div>
                <span>LOCATION</span>
                <strong>
                  {selectedHazard.location || "India"}
                </strong>
              </div>

              <div>
                <span>VEHICLE</span>
                <strong>
                  {selectedHazard.vehicle || "VH-042"}
                </strong>
              </div>

              <div>
                <span>DETECTED</span>
                <strong>
                  {selectedHazard.time || "Just now"}
                </strong>
              </div>
            </div>

            <button className="maintenance-button">
              <Wrench size={17} />
              Create Maintenance Request
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;