"""
Project Model
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base


class ProjectDB(Base):
    """Project database model"""
    __tablename__ = "projects"
    
    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Core Fields
    project_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    decision_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="created")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Optional user tracking (for multi-user setups)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    
    # File and text information
    total_text_length: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Configuration
    chunk_size: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    chunk_overlap: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    
    # Analysis data (stored as text, parsed as needed)
    analysis_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    simulation_requirement: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Task and graph references
    graph_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    graph_build_task_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # Error information
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    sources = relationship("SourceDB", back_populates="project", cascade="all, delete-orphan")
    ontologies = relationship("OntologyDB", back_populates="project", cascade="all, delete-orphan")
    graphs = relationship("GraphDB", back_populates="project", cascade="all, delete-orphan")
    simulations = relationship("SimulationDB", back_populates="project", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_projects_status', 'status'),
        Index('ix_projects_created_at', 'created_at'),
        Index('ix_projects_user_status', 'user_id', 'status'),
    )
    
    def __repr__(self):
        return f"<ProjectDB(project_id='{self.project_id}', name='{self.name}', status='{self.status}')>"
