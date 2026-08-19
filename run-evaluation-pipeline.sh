#!/bin/bash
# Production-Like Evaluation Pipeline for ASKTHEPEOPLE
# Based on Sequential Pipeline pattern from autonomous-loops

set -e

echo "=== ASKTHEPEOPLE Production Evaluation Pipeline ==="
echo "Date: $(date)"
echo "Baseline: cc97957"
echo ""

# Create evaluation workspace
mkdir -p .evaluation
cd .evaluation

# Phase 1: Frontend Upload Flow Testing
echo "Phase 1: Testing Frontend Upload Flow (recently fixed)..."
cat > phase1-test-upload-flow.md << 'EOF'
Test the frontend upload flow end-to-end:

1. Check that Process.vue changes are correct:
   - Read frontend/src/views/Process.vue
   - Verify clearPendingUpload() is called BEFORE upload starts (race condition fix)
   - Verify loading state is set and cleared properly
   - Verify stopOntologyPolling() helper exists and is used
   - Verify error categorization includes network/timeout/validation cases

2. Trace the data flow:
   - Home.vue → setPendingUpload() → Process.vue → getPendingUpload()
   - Verify files are actually POSTed to /api/graph/ontology/generate
   - Check API endpoint exists and returns task_id + project_id

3. Identify potential issues:
   - Race conditions not covered
   - Error cases not handled
   - Memory leaks
   - Missing validation

4. Document findings in .evaluation/phase1-results.md
EOF

echo "Phase 2: P0 Critical Issues Validation..."
cat > phase2-test-p0-issues.md << 'EOF'
Validate the 3 P0 critical issues from audit:

P0-1: Source Ingestion V1
- Read backend/app/config.py - find SOURCE_INGESTION_V1_ENABLED flag
- Read backend/app/api/routes/source_routes.py
- Test: Try to call POST /api/sources/v1/upload-intent
- Expected: Returns 503 "not production-ready"
- Document: What are "Task 4 §5 production blockers"?
- Recommendation: Remove endpoints or complete blockers

P0-2: Graph Deletion
- Read backend/app/api/graph.py:588-614
- Find delete_graph() implementation
- Test: Does builder.delete_graph() actually work?
- Check: Are there any error logs or issues?
- Recommendation: Fix or remove endpoint

P0-3: Graph Memory Update Parameter
- Read backend/app/api/graph.py:378-514
- Find enable_graph_memory_update parameter
- Trace: Is it used anywhere in the function?
- Test: Does passing true/false change behavior?
- Recommendation: Implement or remove parameter

Document findings in .evaluation/phase2-results.md
EOF

echo "Phase 3: Hidden Features Discovery..."
cat > phase3-test-hidden-features.md << 'EOF'
Test the 6 P1 hidden features from audit:

P1-1: Trait Inference
- Read backend/app/services/oasis_profile_generator.py:1142-1161
- Find ENABLE_TRAIT_INFERENCE config
- Test: Generate profiles with flag on vs off
- Measure: Time difference, quality difference
- Document: Why is it disabled? Cost? Latency?

P1-2: Archetype Mode
- Read backend/app/services/oasis_profile_generator.py:818-919
- Find generate_archetype_profiles() method
- Check: Is it called anywhere?
- Test: Can we call it via API?
- Document: How to expose in UI

P1-3: Counterfactual Branching
- Read backend/app/services/counterfactual_simulator.py
- Read backend/app/models/counterfactual.py
- Check: What API endpoints exist?
- Find: What's missing to make it work?
- Document: Implementation plan

P1-4: Dual Persistence
- Search for "USE_SUPABASE_PERSISTENCE" in codebase
- Count: How many files have dual paths?
- Test: Do both paths work?
- Document: Migration status

P1-5: Graph Memory Search
- Read backend/app/services/zep_graph_memory_search.py
- Check: Is module imported anywhere?
- Test: Can we use it directly?
- Document: Why wasn't it wired?

P1-6: Interview Timing
- Read backend/app/api/routes/interview_routes.py
- Read backend/app/services/simulation_ipc.py
- Find: When does OASIS env close?
- Test: Can interviews run after completion?
- Document: Fix approach

Document findings in .evaluation/phase3-results.md
EOF

echo "Phase 4: Integration Testing..."
cat > phase4-test-integration.md << 'EOF'
Test the complete end-to-end flow:

1. Upload files → Ontology generation
   - Can files be uploaded?
   - Does ontology generation start?
   - Does it complete successfully?

2. Ontology → Graph build
   - Does graph build trigger automatically?
   - Does it complete without errors?
   - Is graph data retrievable?

3. Graph → Simulation preparation
   - Can profiles be generated?
   - Are they valid OASIS profiles?
   - Is configuration created correctly?

4. Simulation → Execution
   - Does OASIS subprocess start?
   - Do actions get logged?
   - Does monitoring work?

5. Execution → Report generation
   - Does report generation trigger?
   - Is report data complete?
   - Can report be exported?

For each step, document:
- Pass/Fail status
- Error messages if any
- Performance metrics (time, memory)
- Data validation results

Document findings in .evaluation/phase4-results.md
EOF

echo "Phase 5: Security Validation..."
cat > phase5-test-security.md << 'EOF'
Validate security controls from audit:

1. Path Traversal Protection
   - Read backend/app/utils/safe_path.py
   - Test: Try to upload file with path traversal (../../etc/passwd)
   - Expected: Blocked by safe_join()
   - Verify: All file operations use safe_path utilities

2. SSRF Protection
   - Read backend/app/utils/safe_url.py
   - Test: Try to provide internal URL (http://localhost)
   - Expected: Blocked by URL validation
   - Verify: All URL fetches use safe_url utilities

3. Prompt Injection Hardening
   - Check: Are user inputs separated from instructions?
   - Look for: XML/structured delimiters
   - Test: Try adversarial prompt in file content
   - Expected: Instructions remain isolated

4. Authentication
   - Read backend/app/__init__.py (bearer auth)
   - Read backend/app/api/ws.py (signed tickets)
   - Test: Can unauthenticated requests reach /api/*?
   - Expected: 401 Unauthorized

5. Fail-Closed Configuration
   - Read backend/app/config.py
   - Verify: SECRET_KEY required
   - Verify: APP_TOKEN required in production
   - Verify: CORS refuses * in production

Document findings in .evaluation/phase5-results.md
EOF

echo "Phase 6: Performance Baseline..."
cat > phase6-test-performance.md << 'EOF'
Establish performance baselines:

1. Ontology Generation
   - Input: 3 PDFs, 50 pages total
   - Measure: Time to complete
   - Measure: LLM tokens used
   - Baseline: < 2 minutes

2. Graph Building
   - Input: Ontology with 20 entities
   - Measure: Time to complete
   - Measure: API calls to Zep
   - Baseline: < 1 minute

3. Profile Generation
   - Input: 20 entities
   - Output: 50 profiles
   - Measure: Time, LLM tokens
   - Baseline: < 3 minutes

4. Simulation Execution
   - Input: 50 agents, 10 rounds
   - Measure: Time to complete
   - Measure: Actions logged
   - Baseline: < 5 minutes

5. Report Generation
   - Input: Completed simulation
   - Measure: Time to generate
   - Measure: Report quality
   - Baseline: < 2 minutes

Document findings in .evaluation/phase6-results.md
EOF

echo "Phase 7: Error Handling..."
cat > phase7-test-errors.md << 'EOF'
Test error handling and recovery:

1. Network Failures
   - Simulate: Disconnect during upload
   - Expected: Timeout error with clear message
   - Verify: No orphaned state

2. Invalid Files
   - Test: Upload .exe file
   - Expected: Validation error
   - Verify: No security issues

3. File Too Large
   - Test: Upload 100MB file
   - Expected: Size limit error
   - Verify: Server doesn't crash

4. LLM API Failures
   - Simulate: Provider returns 500
   - Expected: Retry with backoff
   - Verify: User sees actionable error

5. Database Failures
   - Simulate: PostgreSQL connection lost
   - Expected: Transaction rollback
   - Verify: Data consistency maintained

6. Worker Crashes
   - Simulate: Kill Celery worker mid-task
   - Expected: Task marked as failed
   - Verify: Resumable on restart

Document findings in .evaluation/phase7-results.md
EOF

echo "Phase 8: State Machine Validation..."
cat > phase8-test-state-machine.md << 'EOF'
Validate state machine transitions:

1. Simulation Lifecycle
   - Test: IDLE → STARTING → RUNNING → COMPLETED
   - Test: RUNNING → PAUSED → RUNNING
   - Test: RUNNING → STOPPING → STOPPED
   - Verify: Invalid transitions rejected

2. Project Status
   - Test: CREATED → ONTOLOGY_GENERATING → ONTOLOGY_GENERATED
   - Test: ONTOLOGY_GENERATED → GRAPH_BUILDING → GRAPH_COMPLETED
   - Verify: Can't skip states

3. Task Status
   - Test: pending → running → completed
   - Test: pending → running → failed
   - Verify: Terminal states are immutable

4. Run Stages (from ADR-0003)
   - Test: PENDING → READY → RUNNING → VALIDATING → SUCCEEDED
   - Test: RUNNING → FAILED (retryable)
   - Verify: Audit trail recorded

Document findings in .evaluation/phase8-results.md
EOF

echo ""
echo "=== Evaluation Pipeline Created ==="
echo "Run each phase with: claude -p < phase{N}-test-*.md"
echo ""
echo "Sequential execution:"
echo "  claude -p < phase1-test-upload-flow.md"
echo "  claude -p < phase2-test-p0-issues.md"
echo "  ... etc"
echo ""
echo "Parallel execution (independent phases):"
echo "  claude -p < phase2-test-p0-issues.md &"
echo "  claude -p < phase3-test-hidden-features.md &"
echo "  wait"
