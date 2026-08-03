"""
Graph Model - Knowledge graphs built from projects
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Text, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base


class GraphDB(Base):
    """Graph database model"""
    __tablename__ = "graphs"
    
    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign Key
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # Graph identification
    graph_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    
    # Graph data
    nodes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    edges: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    graph_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="building")
    
    # Error information
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    project = relationship("ProjectDB", back_populates="graphs")
    
    # Indexes
    __table_args__ = (
        Index('ix_graphs_project_id', 'project_id'),
        Index('ix_graphs_status', 'status'),
    )
    
    def __repr__(self):
        return f"<GraphDB(graph_id='{self.graph_id}', project_id={self.project_id})>"
