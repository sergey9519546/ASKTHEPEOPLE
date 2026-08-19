# ASKTHEPEOPLE - Implementation Roadmap

## Status: 2026-08-18
## Baseline Commit: 8b616dc7fa02eeed5ada8c51998d8b197be28f8d

---

## ✅ COMPLETED WORK

### Phase 1: Frontend Upload Flow Fix (DONE)
**Date:** 2026-08-03  
**Status:** ✅ Complete (V2 with audit improvements)  
**Files Modified:** `frontend/src/views/Process.vue`

**What Was Fixed:**
- Broken upload flow where files never reached backend
- Race conditions from double-clicks
- Memory leaks from timer cleanup
- Generic error messages
- Missing loading states

**Documentation:**
- `FRONTEND_UPLOAD_FIX.md` - V1 implementation
- `FRONTEND_UPLOAD_FIX_V2.md` - Audited & improved version

**Grade:** A- (production-ready with minor polish missing)

**Next Step:** Manual end-to-end testing required

---

## 🔄 IN PROGRESS / PLANNED WORK

### Phase 2: Repository Archaeology (STARTING NOW)
**Priority:** P0  
**Estimated Time:** 4-8 hours  
**Owner:** TBD

**Objective:**
Perform complete forensic audit of repository for:
- Unfinished features in branches/PRs
- Partially merged work
- Abandoned implementations
- Valuable code that was started but never shipped
- Hidden incompleteness in `main`
- Regressions where functionality was removed

**Output:** Repository Recovery Ledger

---

## 📋 PLANNED PHASES (After Archaeology)

### Phase 3A: Quick Wins (1-2 days)
**Priority:** P0-P1  
**Prerequisites:** Upload fix tested, archaeology complete

**Tasks:**
1. **Eliminate P0 Daemon Threads** (Gate 0)
   - File: `backend/app/__init__.py:229` - `_task_cleanup_worker`
   - File: `backend/app/api/simulation.py` - preparation endpoint
   - Replace with Celery worker jobs
   - **Audit Finding:** P0 "Preparation runs in local daemon thread"

2. **Fix Contradictory Lifecycle Semantics** (Gate 1)
   - File: `backend/app/services/simulation_runner.py`
   - Stop → STOPPED (not PAUSED)
   - Close → COMPLETED only on success
   - Add state transition guards
   - **Audit Finding:** P1 "Contradictory lifecycle semantics"

3. **Add Basic Integration Tests**
   - Test: Upload → Ontology → Graph → Simulation → Report
   - Test: State machine transitions
   - Test: Error scenarios
   - **Current State:** Only 1 smoke test exists

**Expected Outcome:**
- P0 issues resolved
- System more reliable
- Test coverage baseline established

---

### Phase 3B: Architecture Refactoring (3-5 days)
**Priority:** P1  
**Prerequisites:** Phase 3A complete

**Tasks:**

#### 1. Refactor SimulationRunner (2 days)
**File:** `backend/app/services/simulation_runner.py` (2,034 lines)

**Current Issues:**
- Class-method singleton antipattern (lines 239-269)
- Process-local state: `_run_states`, `_processes`, `_monitor_threads`
- Can't scale horizontally
- Can't test properly

**Target Architecture:**
```python
class SimulationRunner:
    def __init__(self, config, logger, db_session):
        self.config = config
        self.logger = logger
        self.db_session = db_session
        # Instance state only
    
    def start_simulation(self, simulation_id, config):
        # Instance method
        pass
```

**Deliverables:**
- Instance-based SimulationRunner
- Dependency injection for config/logger/db
- Remove all class-level state
- Add unit tests

#### 2. Decompose simulation.py Monolith (2 days)
**File:** `backend/app/api/simulation.py` (3,526 lines, 54 functions, 41 routes)

**Current Issues:**
- Violates AGENTS.md rule #4
- Unmaintainable size
- Audit cluster

**Target Structure:**
```
backend/app/api/simulations/
  ├── __init__.py (route registration)
  ├── prepare.py (preparation routes)
  ├── start.py (start/resume routes)
  ├── stop.py (stop/pause routes)
  ├── status.py (status/progress routes)
  ├── actions.py (action logging routes)
  └── interviews.py (interview routes)
```

**Per-file limit:** 300 lines

**Deliverables:**
- Decomposed routes into modules
- Each module < 300 lines
- Consistent route responsibility contract
- Route tests

#### 3. Extract run_parallel_simulation.py Modules (1 day)
**File:** `backend/app/services/run_parallel_simulation.py` (2,700+ lines)

**Target Structure:**
```
backend/app/services/oasis/
  ├── __init__.py
  ├── adapter.py (OASIS API wrapper)
  ├── encoding_utils.py (UTF-8 fixes)
  ├── ipc_handler.py (Command/response logic)
  ├── action_logger.py (JSONL parsing with schema)
  └── platform_orchestrator.py (Twitter/Reddit coordination)
```

**Deliverables:**
- Extracted modules with clear responsibilities
- Unit tests for each module
- Integration tests for OASIS flow

**Expected Outcome:**
- Maintainable codebase
- Testable components
- Foundation for durable workflows

---

### Phase 4: Durable Workflows (5-7 days)
**Priority:** P0-P1 (Gate 2)  
**Prerequisites:** Phase 3B complete

**Implements:** ADR-0003 Durable Run Orchestration

**Tasks:**

#### 1. Implement RunOrchestrator Interface (2 days)
```python
class RunOrchestrator(Protocol):
    def start_run(self, run_id: str, config: RunConfig) -> str
    def stop_run(self, run_id: str) -> None
    def get_status(self, run_id: str) -> RunStatus
    def add_stage(self, stage: StageDefinition) -> None
```

#### 2. Stage-Based Execution Model (2 days)
**Stages:**
- PREPARING (profile generation)
- EXTRACTING (source processing)
- GENERATING_PROFILES (LLM calls)
- CONSTRUCTING_SCENARIOS (OASIS config)
- SYNTHESIZING (OASIS execution)
- VALIDATING_OUTPUT (containment checks)
- GENERATING_BRIEF (report generation)

**State Machine:**
```
PENDING → READY → RUNNING → VALIDATING → SUCCEEDED
                           ↓
                         FAILED (retryable/terminal)
```

#### 3. Persistent Leases and Heartbeats (1 day)
- Workers acquire lease with fencing token
- Heartbeat every 30s
- Lease expires after 90s without heartbeat
- Ownership transfer on worker failure

#### 4. Push-Based Events (1 day)
**Replace polling with WebSocket push:**
- RunStarted
- StageCompleted
- ActionLogged
- RunCompleted
- RunFailed

**Remove:** 0.5s polling loops

#### 5. Idempotency and Retry (1 day)
- Accept `Idempotency-Key` header
- Store in task metadata
- Return 409 with Location if duplicate
- Retry creates new attempt number
- Classify errors: retryable vs terminal

**Expected Outcome:**
- Workers can be killed and work resumes
- No duplicate paths/artifacts
- Stop works at every stage
- Horizontal scaling possible

---

### Phase 5: Canonical Persistence (4-5 days)
**Priority:** P1 (Gate 3)  
**Prerequisites:** Phase 4 complete

**Tasks:**

#### 1. PostgreSQL Schema Migration (2 days)
**Implement:** `docs/architecture/data-model.md`

**Core Tables:**
- organizations (tenant)
- projects
- decisions, decision_versions
- sources, source_versions, source_segments
- runs, run_stages, run_events
- possible_paths
- considerations
- extraction_candidates

**All tables have:**
- id (UUIDv7)
- organization_id (tenant isolation)
- created_at, updated_at
- version (optimistic concurrency)

**Deliverables:**
- Alembic migrations
- Repository classes
- Tenant isolation at query layer

#### 2. Immutable Run Configuration (1 day)
- `run_configs` table with frozen inputs
- Configuration hash
- DB constraint: completed runs cannot mutate
- Reruns create new run_id with parent_run_id

#### 3. Append-Only Event Stream (1 day)
- `run_events` table for all state transitions
- Fields: actor, timestamp, reason, prior_version, resulting_version
- Events never deleted/modified

#### 4. Provenance Manifests (1 day)
**Record in every run:**
- Prompt versions
- Model identifiers
- Source hashes
- User edits
- Containment contract version

**Storage:** `run_manifests` table (JSONB)

**Include in exports:** Always

**Expected Outcome:**
- Filesystem JSON replaced with PostgreSQL
- Completed runs are immutable
- Full audit trail
- Provenance in every export

---

### Phase 6: Scale and Operations (3-4 days)
**Priority:** P1-P2 (Gate 4)  
**Prerequisites:** Phase 5 complete

**Tasks:**

#### 1. Observability (2 days)
- OpenTelemetry traces for every run
- Span per stage with safe metadata (no PII)
- Correlation IDs across services
- Structured logging

#### 2. Budgets and Limits (1 day)
- Per-run token budgets
- Per-org concurrency limits
- Retry budgets per stage
- Cost tracking per run

#### 3. Chaos Tests (1 day)
- Kill worker during each stage
- Provider timeout simulation
- Rate limit simulation
- Malformed OASIS output
- Database transient failure

#### 4. Runbook (Half day)
- OASIS failure diagnostics
- Worker recovery procedures
- Incident response triggers
- Rollback procedures

**Expected Outcome:**
- Production-ready operations
- Clear runbooks
- Graceful degradation
- Cost controls

---

### Phase 7: Advanced Methodology (4-5 days)
**Priority:** P1 (Gate 5)  
**Prerequisites:** Phase 6 complete

**Tasks:**

#### 1. OASIS Containment Contract Enforcement (2 days)
**File:** `docs/product/METHODOLOGY.md`

**Rules:**
- Profile generation: "decision lenses" not "respondents"
- Action logs: "synthetic path material" not "observed posts"
- Reports: transform to canonical schema
- No "most likely" or "majority" rankings
- Add "SYNTHETIC" markers to all OASIS outputs

**Implementation:**
- Output validators
- Schema transformations
- Terminology linter

#### 2. Prompt Registry (1 day)
- External prompt templates (not inlined)
- Version controlled
- Schema-constrained outputs
- Evaluation results required before promotion

#### 3. Coverage Ledger (1 day)
- Track which assumptions/uncertainties are represented
- Flag incomplete coverage
- Block brief generation on gaps

#### 4. Evaluation Framework (1 day)
- Offline test datasets
- Metrics: validity, distinctness, coverage, truth compliance, provenance
- Regression tests on prompt/model changes
- Manual review sampling

**Expected Outcome:**
- Methodology compliance
- Quality assurance
- Audit-ready outputs

---

### Phase 8: Frontend and Export Compliance (2-3 days)
**Priority:** P1 (Gate 6)  
**Prerequisites:** Phase 7 complete

**Tasks:**

#### 1. Truth Disclosure in Exports (1 day)
- PDF: visible header/footer with "SYNTHETIC DECISION EXPLORER"
- Machine-readable manifest in metadata
- Copy/share includes disclaimer
- Social preview cards include descriptor

#### 2. Semantic Route List (1 day)
- Keyboard-accessible alternative to SVG map
- Screen-reader friendly
- WCAG 2.2 Level AA compliance

#### 3. Prohibited Terminology Linter (Half day)
**Prohibited:**
- "predict"
- "know what people think"
- "representative"
- "digital twin"
- "bias-free personas"

**Check:**
- User-facing copy
- Exports
- UI text
- Error messages

**Add:** CI check

**Expected Outcome:**
- All exports compliant with truth contract
- Accessibility standards met
- Prohibited language blocked

---

## 🎯 RELEASE GATES SUMMARY

| Gate | Theme | Status | Owner | Estimate |
|------|-------|--------|-------|----------|
| 0 | Immediate correctness and security | 🟡 PARTIAL | Security Reviewer | 2-3 days |
| 1 | Typed API boundary | 🟡 PARTIAL | Architect | 3-4 days |
| 2 | Durable workflows | 🔴 NOT STARTED | Orchestration Engineer | 5-7 days |
| 3 | Canonical persistence and provenance | 🔴 NOT STARTED | Persistence Engineer | 4-5 days |
| 4 | Scale and operations | 🔴 NOT STARTED | Release Operator | 3-4 days |
| 5 | Advanced simulation methodology | 🔴 NOT STARTED | AI Eval Steward | 4-5 days |
| 6 | Frontend and export compliance | 🟡 PARTIAL | Frontend Steward | 2-3 days |

**Total Estimate:** 23-31 days (4-6 weeks)

---

## 🚦 DECISION POINTS

### After Phase 2 (Archaeology)
**Decision:** What unfinished work should be prioritized?
**Options:**
- A) Continue with planned roadmap (Phases 3-8)
- B) Pivot to finish valuable discovered work first
- C) Merge: Integrate discoveries into planned phases

### After Phase 3A (Quick Wins)
**Decision:** Architecture refactoring or production push?
**Options:**
- A) Continue to Phase 3B (refactoring foundation)
- B) Skip to Phase 4 (durable workflows with current code)
- C) Stop and stabilize for production with quick wins only

### After Phase 4 (Durable Workflows)
**Decision:** Continue to full production or deploy incremental?
**Options:**
- A) Continue to Phases 5-8 (full production-ready)
- B) Deploy what we have and iterate
- C) Pause for user feedback

---

## 📊 RISK ASSESSMENT

### High Risk Areas

#### 1. Durable Workflows (Phase 4)
**Risk:** Complex state machine, many edge cases  
**Mitigation:** Comprehensive testing, gradual rollout, feature flag

#### 2. PostgreSQL Migration (Phase 5)
**Risk:** Data migration, backward compatibility  
**Mitigation:** Keep filesystem as fallback, dual-write period, rollback plan

#### 3. OASIS Refactoring (Phase 3B)
**Risk:** Breaking existing simulations  
**Mitigation:** Extensive integration tests, canary deployment

### Medium Risk Areas

#### 4. API Decomposition (Phase 3B)
**Risk:** Route conflicts, broken imports  
**Mitigation:** Gradual extraction, route tests

#### 5. Event-Based Architecture (Phase 4)
**Risk:** Event ordering, duplicate delivery  
**Mitigation:** Idempotency keys, sequence numbers

---

## 📈 SUCCESS METRICS

### Technical Metrics
- ✅ All 6 gates pass acceptance criteria
- ✅ Test coverage > 80%
- ✅ Zero P0/P1 audit findings remain
- ✅ Worker restarts don't lose work
- ✅ Runs are reproducible

### Methodological Metrics
- ✅ OASIS outputs pass containment contract
- ✅ No prohibited terminology in exports
- ✅ Provenance complete on all paths
- ✅ Coverage Ledger identifies gaps

### Operational Metrics
- ✅ Observability traces available
- ✅ Incident runbook exercises pass
- ✅ Cost budgets enforced
- ✅ Multi-tenant isolation verified

---

## 🔗 REFERENCES

### Authoritative Documentation
- `docs/README.md` - Documentation system entry point
- `docs/architecture/index.md` - Current state authority
- `docs/architecture/adr/ADR-0003-durable-run-orchestration.md` - Workflow requirements
- `docs/architecture/state-machines.md` - State transition rules
- `docs/architecture/data-model.md` - PostgreSQL schema
- `docs/product/METHODOLOGY.md` - OASIS containment contract
- `docs/exec-plans/04-durable-orchestration-and-path-engine.md` - Implementation plan

### Agent Contracts
- `AGENTS.md` - Agent team structure and rules
- `INTEGRATION_GUIDE.md` - Integration procedures

### Build Synthesis
- `ASKTHEPEOPLE_GODMODE_BUILDPLAN.md` - Master build plan (supporting, not authoritative)

---

## 📝 CHANGE LOG

### 2026-08-03
- **Added:** Frontend upload flow fix (V1)
- **Added:** Audit and improvements (V2)
- **Created:** `FRONTEND_UPLOAD_FIX.md`
- **Created:** `FRONTEND_UPLOAD_FIX_V2.md`

### 2026-08-18
- **Created:** This roadmap document
- **Status:** Starting repository archaeology audit
- **Next:** Repository Recovery Ledger

---

## 🎯 IMMEDIATE NEXT STEPS

1. **Complete repository archaeology audit** (4-8 hours)
2. **Create Repository Recovery Ledger**
3. **Test frontend upload fix end-to-end**
4. **Decision point:** Quick wins vs architecture refactoring
5. **Begin Phase 3A or integrate archaeology findings**

---

## ✅ APPROVAL CHECKLIST

Before proceeding with each phase:

- [ ] Previous phase complete and tested
- [ ] Documentation updated
- [ ] Tests passing
- [ ] Security review (for P0 changes)
- [ ] User decision (for scope changes)
- [ ] Baseline commit recorded
- [ ] Rollback plan documented

---

**Document Owner:** AI Agent Team  
**Last Updated:** 2026-08-18  
**Next Review:** After archaeology complete
