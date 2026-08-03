"""
Source Model - Uploaded source files for a project
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base


class SourceDB(Base):
    """Source file database model"""
    __tablename__ = "sources"
    
    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign Key
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    # File Information
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    
    # Timestamps
    upload_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Optional extracted text (or stored separately)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationship
    project = relationship("ProjectDB", back_populates="sources")
    
    # Indexes
    __table_args__ = (
        Index('ix_sources_project_id', 'project_id'),
        Index('ix_sources_upload_date', 'upload_date'),
    )
    
    def __repr__(self):
        return f"<SourceDB(filename='{self.filename}', project_id={self.project_id})>"
