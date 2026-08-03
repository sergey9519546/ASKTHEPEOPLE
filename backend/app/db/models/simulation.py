"""
Simulation Model - Simulation runs and configurations
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Text, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base


class SimulationDB(Base):
    """Simulation database model"""
    __tablename__ = "simulations"
    
    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign Key
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Simulation identification
    simulation_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    
    # Configuration
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # Status
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    
    # Result data
    result_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Error information
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    project = relationship("ProjectDB", back_populates="simulations")
    reports = relationship("ReportDB", back_populates="simulation", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('ix_simulations_project_id', 'project_id'),
        Index('ix_simulations_status', 'status'),
        Index('ix_simulations_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<SimulationDB(simulation_id='{self.simulation_id}', status='{self.status}')>"
