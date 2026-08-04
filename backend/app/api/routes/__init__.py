"""
Decomposed Simulation API Route Modules (Gate 1 Refactor)
"""

from . import prep_routes
from . import execution_routes
from . import interview_routes
from . import export_routes
# entity_routes was written during the decomposition but never imported here,
# while the decorators it replaced were commented out in api/simulation.py.
# GET /api/simulation/entities/... therefore answered 404 from that commit
# until this import was added. Every module in this package must be listed.
from . import entity_routes
