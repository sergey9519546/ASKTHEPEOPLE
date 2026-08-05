"""
SQLAlchemy Database Schema - Aligned with Alembic Migrations

This schema matches the initial migration (384c98f88d53) to ensure
the ORM models can be used with the existing database structure.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Text, LargeBinary
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Project(Base):
    """Project model matching the initial migration schema."""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    decision_text = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    user_id = Column(String(64), nullable=True, index=True)
    total_text_length = Column(Integer, nullable=False, default=0)
    chunk_size = Column(Integer, nullable=False, default=512)
    chunk_overlap = Column(Integer, nullable=False, default=50)
    analysis_summary = Column(Text, nullable=True)
    simulation_requirement = Column(Text, nullable=True)
    graph_id = Column(String(64), nullable=True)
    graph_build_task_id = Column(String(64), nullable=True)
    error = Column(Text, nullable=True)


class Graph(Base):
    """Graph model matching the initial migration schema."""
    __tablename__ = "graphs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    graph_id = Column(String(64), nullable=False, unique=True, index=True)
    nodes = Column(JSON, nullable=True)
    edges = Column(JSON, nullable=True)
    graph_metadata = Column(JSON, nullable=True)  # Renamed from metadata to avoid reserved word conflict
    status = Column(String(50), nullable=False, index=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class Ontology(Base):
    """Ontology model matching the initial migration schema."""
    __tablename__ = "ontologies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(String(64), nullable=True, index=True)
    status = Column(String(50), nullable=False, index=True)
    result_data = Column(JSON, nullable=True)  # Renamed from result_json to avoid conflicts
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class Simulation(Base):
    """Simulation model matching the initial migration schema."""
    __tablename__ = "simulations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    simulation_id = Column(String(64), nullable=False, unique=True, index=True)
    config = Column(JSON, nullable=False)
    status = Column(String(50), nullable=False, index=True)
    result_json = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class Source(Base):
    """Source document model matching the initial migration schema."""
    __tablename__ = "sources"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False, default=0)
    content_hash = Column(String(64), nullable=True, index=True)
    upload_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    extracted_text = Column(Text, nullable=True)


class Report(Base):
    """Report model matching the initial migration schema."""
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False, index=True)
    report_id = Column(String(64), nullable=False, unique=True, index=True)
    export_format = Column(String(20), nullable=False, index=True)
    content = Column(LargeBinary, nullable=True)
    content_text = Column(Text, nullable=True)
    filename = Column(String(255), nullable=True)
    file_path = Column(String(512), nullable=True)
    generated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    error = Column(Text, nullable=True)
