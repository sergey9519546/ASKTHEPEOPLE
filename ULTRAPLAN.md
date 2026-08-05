# ULTRAPLAN: ASKTHEPEOPLE Backend Improvements

## Priority P0 - Critical Fixes

### 1. Fix FIXME: generation_lease=None in report_tasks.py
**Location**: `/workspace/backend/app/tasks/report_tasks.py:59`
**Issue**: Report agent called with `generation_lease=None` instead of getting lease from coordinator
**Impact**: No cancellation support, no cooperative locking for report generation
**Fix**: Import and use `report_generation_coordinator` to acquire lease before calling agent

### 2. Database Layer - Make it Actually Usable
**Location**: `/workspace/backend/app/db/schema.py`, `/workspace/backend/app/models/__init__.py`
**Issue**: SQLAlchemy configured but models not registered with Alembic, schema mismatch
**Impact**: Database is dead code - migrations exist but don't match current schema
**Decision**: Either fully activate DB layer OR remove it cleanly (recommending activation)
**Fix**: 
- Update schema.py to match migration file (projects, graphs, simulations, etc.)
- Register models properly so they can be used
- Add session management to app factory

### 3. Task State Scalability Warning
**Location**: `/workspace/backend/app/models/task.py`
**Issue**: In-memory task state breaks with multiple workers
**Current Mitigation**: Redis fallback exists but needs explicit configuration
**Action**: Add runtime warning when multiple workers detected without Redis

## Priority P1 - Production Hardening

### 4. Upload Folder Persistence
**Location**: Config, deployment docs
**Issue**: Railway deploys wipe `/app/backend/uploads` without volume mount
**Fix**: Add explicit check + warning in config if UPLOAD_FOLDER is under /app and no volume detected

### 5. Explicit CORS_ORIGINS Enforcement
**Location**: Already enforced in config.py
**Status**: ✅ Already implemented correctly
**Action**: Document this requirement clearly

### 6. Remove Dead Code or Activate It
**Location**: Various
**Candidates**:
- Old schema in db/schema.py (mismatched with migrations)
- Any unused service classes

## Priority P2 - Developer Experience

### 7. Clearer Error Messages
**Location**: Multiple locations
**Improvement**: Add actionable hints to common errors

### 8. Better Logging for State Transitions
**Location**: Task manager, simulation runner
**Improvement**: Log when falling back to in-memory vs Redis

---

## Execution Order
1. Fix generation_lease FIXME (P0, 15 min)
2. Fix database schema mismatch (P0, 30 min)  
3. Add upload folder persistence check (P1, 20 min)
4. Add scalability warnings (P1, 15 min)
5. Clean up dead code (P2, 30 min)
