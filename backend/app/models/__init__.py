"""
Data Models Module

This module provides SQLAlchemy ORM models aligned with the database migrations.
Models are registered here for easy import throughout the application.
"""

from .task import TaskManager, TaskStatus
from .project import Project, ProjectStatus, ProjectManager

# Import database schema models for registration with Alembic
from ..db.schema import (
    Base,
    Project as DBProject,
    Graph,
    Ontology,
    Simulation,
    Source,
    Report
)

__all__ = [
    'TaskManager',
    'TaskStatus',
    'Project',
    'ProjectStatus',
    'ProjectManager',
    'Base',
    'DBProject',
    'Graph',
    'Ontology',
    'Simulation',
    'Source',
    'Report'
]

