from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./vigilcloud.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

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

    id        = Column(Integer, primary_key=True, index=True)
    node_id   = Column(String, unique=True, index=True)
    latitude  = Column(Float)
    longitude = Column(Float)
    last_seen = Column(DateTime, default=datetime.utcnow)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create tables on startup
Base.metadata.create_all(bind=engine)