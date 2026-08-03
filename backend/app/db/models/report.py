"""
Report Model - Generated reports from simulations
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Text, ForeignKey, Index, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base


class ReportDB(Base):
    """Report database model"""
    __tablename__ = "reports"
    
    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign Key
    simulation_id: Mapped[int] = mapped_column(ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False)
    
    # Report identification
    report_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    
    # Report content
    export_format: Mapped[str] = mapped_column(String(20), nullable=False)  # pdf, markdown, etc.
    content: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # For markdown/text formats
    
    # File information
    filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    # Timestamps
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Error information
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationship
    simulation = relationship("SimulationDB", back_populates="reports")
    
    # Indexes
    __table_args__ = (
        Index('ix_reports_simulation_id', 'simulation_id'),
        Index('ix_reports_generated_at', 'generated_at'),
        Index('ix_reports_format', 'export_format'),
    )
    
    def __repr__(self):
        return f"<ReportDB(report_id='{self.report_id}', format='{self.export_format}')>"
