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
# read_routes carries the 17 read-only query handlers (list/history/profiles/
# config/observations/metrics/compare/status/actions/timeline/agent-stats/
# posts/comments/opinions) moved out of the simulation.py controller to finish
# the gate 1 decomposition (ADR-0011). The shared helpers they use stay in
# simulation.py because the write/lifecycle modules import them from there.
from . import read_routes
from . import workspace_routes
from . import decision_lens_routes
