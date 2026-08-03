import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Uuid
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id = Column(Uuid, ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Simulation(Base):
    __tablename__ = "simulations"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id = Column(Uuid, ForeignKey("projects.id"), nullable=False)
    status = Column(String, nullable=False)
    config = Column(JSON, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class AgentProfile(Base):
    __tablename__ = "agent_profiles"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    simulation_id = Column(Uuid, ForeignKey("simulations.id"), nullable=False)
    agent_name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    persona_data = Column(JSON, nullable=False)

class Attempt(Base):
    __tablename__ = "attempts"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    simulation_id = Column(Uuid, ForeignKey("simulations.id"), nullable=False)
    run_number = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime(timezone=True), nullable=True)

class Observation(Base):
    __tablename__ = "observations"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    attempt_id = Column(Uuid, ForeignKey("attempts.id"), nullable=False)
    round_num = Column(Integer, nullable=False)
    action_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
