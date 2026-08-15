from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

DATABASE_URL = "sqlite:///./vigilcloud.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# ---------------------------------------------------------------------------
# Existing v1 tables — UNCHANGED from your working version
# ---------------------------------------------------------------------------

class HazardEvent(Base):
    __tablename__ = "hazard_events"

    id            = Column(Integer, primary_key=True, index=True)
    node_id       = Column(String)
    hazard_type   = Column(String)   # pothole / fog / fire / stalled_vehicle
    confidence    = Column(Float)
    latitude      = Column(Float)
    longitude     = Column(Float)
    confirmed     = Column(Integer, default=0)  # 1 = confirmed, 0 = pending
    timestamp     = Column(DateTime, default=datetime.utcnow)


class Node(Base):
    __tablename__ = "nodes"

    id          = Column(Integer, primary_key=True, index=True)
    node_id     = Column(String, unique=True, index=True)
    latitude    = Column(Float)
    longitude   = Column(Float)
    last_seen   = Column(DateTime, default=datetime.utcnow)
    # NEW — defaults to "infra_road" so every existing row still validates.
    # Valid values: "infra_road" (pole-mounted) / "truck_mounted" (on a cargo truck)
    node_type   = Column(String, default="infra_road")


# ---------------------------------------------------------------------------
# NEW v2 tables — fleet / cargo-protection pivot
# ---------------------------------------------------------------------------

class FleetOperator(Base):
    """A logistics company / tenant. Fleet dashboard scopes data to this."""
    __tablename__ = "fleet_operators"

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String)
    contact_email   = Column(String, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)


class Truck(Base):
    """A physical truck belonging to a fleet operator."""
    __tablename__ = "trucks"

    id                  = Column(Integer, primary_key=True, index=True)
    plate_no            = Column(String)
    fleet_operator_id   = Column(Integer, ForeignKey("fleet_operators.id"))
    created_at          = Column(DateTime, default=datetime.utcnow)

    fleet_operator = relationship("FleetOperator")


class Shipment(Base):
    """
    A single in-transit cargo run. Carries the live Cargo Risk Score.
    cargo_risk_score is 0-100, recomputed by the /shipments/{id}/risk endpoint.
    """
    __tablename__ = "shipments"

    id                  = Column(Integer, primary_key=True, index=True)
    fleet_operator_id   = Column(Integer, ForeignKey("fleet_operators.id"))
    truck_id            = Column(Integer, ForeignKey("trucks.id"))

    cargo_type          = Column(String, default="general")   # pharma / fmcg / electronics / general
    cargo_value_inr     = Column(Float, default=0.0)
    is_cold_chain       = Column(Integer, default=0)          # 1 = yes, 0 = no (matches `confirmed` style)
    temp_band_min       = Column(Float, nullable=True)
    temp_band_max       = Column(Float, nullable=True)

    route_start         = Column(String)
    route_end           = Column(String)
    status              = Column(String, default="in_transit")  # in_transit / delivered / delayed

    # Live-computed risk score + its three components, so the dashboard
    # can show a breakdown, not just a single opaque number.
    cargo_risk_score            = Column(Float, default=0.0)
    risk_route_component        = Column(Float, default=0.0)
    risk_prediction_component   = Column(Float, default=0.0)
    risk_shock_component        = Column(Float, default=0.0)

    created_at   = Column(DateTime, default=datetime.utcnow)
    eta          = Column(DateTime, nullable=True)

    fleet_operator = relationship("FleetOperator")
    truck          = relationship("Truck")


class ShockEvent(Base):
    """
    An ADXL345 reading above the g-force threshold on a truck-mounted node.
    truck_node_id references Node.node_id (the string business key),
    same pattern as HazardEvent.node_id — not Node.id.
    """
    __tablename__ = "shock_events"

    id                  = Column(Integer, primary_key=True, index=True)
    truck_node_id       = Column(String)                       # e.g. "TRK-Node-07" -> Node.node_id
    shipment_id         = Column(Integer, ForeignKey("shipments.id"))

    g_force             = Column(Float)
    severity            = Column(String)     # minor / moderate / severe

    latitude            = Column(Float)
    longitude           = Column(Float)

    # Nearest confirmed hazard within 200m/30s, if any — causal link.
    # References HazardEvent.id (its integer PK), nullable.
    nearby_hazard_id    = Column(Integer, ForeignKey("hazard_events.id"), nullable=True)

    timestamp           = Column(DateTime, default=datetime.utcnow)

    shipment = relationship("Shipment")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create tables on startup
Base.metadata.create_all(bind=engine)