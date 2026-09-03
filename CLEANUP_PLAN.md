# Repository Cleanup and Organization Plan

## Current State Analysis

### Root Directory: 47 Markdown Files
**Problem:** Excessive root-level documentation creates confusion. Many files are:
- Session summaries from past work
- Duplicate deployment guides
- Obsolete audit reports
- Temporary completion markers

### Directories Status
- ✅ `backend/` — Core application
- ✅ `frontend/` — Core application  
- ✅ `docs/` — Canonical documentation (77 files, validated)
- ⚠️ `log/` — Not in .gitignore (should be ignored)
- ⚠️ `scratch/` — Not in .gitignore (should be ignored)
- ✅ `output/` — Already gitignored
- ✅ `gui-test-screenshots/` — Already gitignored
- ❓ `static/` — Unknown purpose
- ✅ `supabase/` — Infrastructure config
- ✅ `tools/` — Build/validation scripts

---

## Cleanup Strategy

### Phase 1: Archive Session Documents

**Move to `docs/archive/sessions/`:**
- All `*_COMPLETE*.md`, `*_SUMMARY*.md`, `*_REPORT*.md`
- Session-specific delivery documents
- Historical audit reports

**Keep in Root (Essential):**
- `README.md` — Primary project documentation
- `README-EN.md` — English version
- `AGENTS.md` — Agent operational contract
- `INTEGRATION_GUIDE.md` — Referenced by AGENTS.md
- `MANIFEST.md` — Project manifest (if current)
- `PROVENANCE.md` — Provenance tracking
- `THIRD_PARTY_NOTICES.md` — Legal requirement

### Phase 2: Consolidate Deployment Guides

**Problem:** 8+ deployment guides
- `DEPLOYMENT_OPTIONS.md`
- `DEPLOYMENT_STATUS.md`
- `DEPLOY_CHECKLIST.md`
- `FREE_DEPLOYMENT_GUIDE.md`
- `RAILWAY_*.md` (4 files)
- `READY_TO_DEPLOY.md`
- `QUICK_REFERENCE.md`

**Solution:**
- Move all to `docs/deployment/`
- Create `docs/deployment/README.md` as single entry point
- Archive obsolete ones

### Phase 3: Consolidate Architecture Documents

**Move to `docs/architecture/`:**
- `ASKTHEPEOPLE_GODMODE_BUILDPLAN.md`
- `IMPLEMENTATION_ROADMAP.md`
- `THE_ARCHITECTURE_THAT_ACTUALLY_OPTIMIZES_THETA.md`
- `ULTRAPLAN.md`

### Phase 4: Update .gitignore

**Add:**
```
log/
scratch/
*.log
```

### Phase 5: Remove Unnecessary Directories

**Evaluate:**
- `log/` — Should be gitignored and cleared
- `scratch/` — Should be gitignored and cleared
- `static/` — Check if still needed

---

## Proposed Final Structure

```
ASKTHEPEOPLE/
├── README.md                    ✅ Keep
├── README-EN.md                 ✅ Keep
├── AGENTS.md                    ✅ Keep
├── INTEGRATION_GUIDE.md         ✅ Keep
├── MANIFEST.md                  ✅ Keep (if current)
├── PROVENANCE.md                ✅ Keep
├── THIRD_PARTY_NOTICES.md       ✅ Keep
│
├── backend/                     ✅ Core app
├── frontend/                    ✅ Core app
├── supabase/                    ✅ Infrastructure
├── tools/                       ✅ Build scripts
│
├── docs/                        ✅ Canonical documentation
│   ├── README.md
│   ├── product/
│   ├── architecture/
│   │   ├── GODMODE_BUILDPLAN.md      (moved)
│   │   ├── IMPLEMENTATION_ROADMAP.md (moved)
│   │   └── THETA_OPTIMIZATION.md     (moved)
│   ├── design/
│   ├── security/
│   ├── release/
│   ├── deployment/                    (new)
│   │   ├── README.md                  (consolidation)
│   │   ├── RAILWAY_SETUP.md
│   │   ├── FREE_TIER_GUIDE.md
│   │   └── CHECKLIST.md
│   └── archive/
│       ├── sessions/                  (new)
│       │   ├── 2026-09-03-intelligent-guidance/
│       │   ├── 2026-08-18-forensic-audit/
│       │   └── ...
│       └── legacy-2026-07-29/
│
└── node_modules/                ✅ Keep (gitignored)
```

---

## Execution Plan

1. **Create archive structure**
2. **Move session documents**
3. **Consolidate deployment guides**
4. **Move architecture documents**
5. **Update .gitignore**
6. **Clear log/scratch directories**
7. **Validate docs after moves**
8. **Commit with clear message**

---

## Files to Archive (31 files)

### Session Summaries/Completion Reports:
- COMPLETE_SESSION_SUMMARY.md
- DEPLOYMENT_STATUS.md
- FINAL_VERIFICATION_COMPLETE.md
- FIXES_COMPLETED.md
- IMPLEMENTATION_COMPLETE_2026-09-03.md
- IMPLEMENTATION_SUMMARY.md
- INTEGRATION_TEST_REPORT.md
- INTELLIGENT_GUIDANCE_DELIVERY.md
- MISSION_COMPLETE.md
- PRODUCTION_READY_SUMMARY.md
- REFACTOR_DELIVERY_SUMMARY.md
- SESSION_COMPLETE_2026-09-03.md
- TODOS_COMPLETE.md
- VALIDATION_REPORT.md

### Audit Reports:
- EVALUATION_REPORT_FINAL.md
- EVALUATION_REPORT_PRELIMINARY.md
- FORENSIC_AUDIT_2026-08-18.md
- PRE_DEPLOYMENT_AUDIT.md
- SKILLS_AND_REPOSITORY_AUDIT_2026-09-03.md
- STRIPPED_AUDIT.md
- STRIPPED_AUDIT_SOLUTIONS.md

### Deployment Guides (consolidate first):
- CELERY_WORKER_SETUP.md
- COMMIT_STAGING_GUIDE.md
- DEPLOYMENT_OPTIONS.md
- DEPLOY_CHECKLIST.md
- FREE_DEPLOYMENT_GUIDE.md
- QUICK_REFERENCE.md
- RAILWAY_DEPLOY.md
- RAILWAY_FREE_TRIAL_STRATEGY.md
- RAILWAY_QUICK_FIX.md
- RAILWAY_SETUP.md
- READY_TO_DEPLOY.md

### Architecture Docs (move to docs/architecture/):
- ASKTHEPEOPLE_GODMODE_BUILDPLAN.md
- IMPLEMENTATION_ROADMAP.md
- NEXT_STEPS_ROADMAP.md
- THE_ARCHITECTURE_THAT_ACTUALLY_OPTIMIZES_THETA.md
- ULTRAPLAN.md

### Miscellaneous:
- CLAUDE.md (agent-specific, archive)
- FRONTEND_UPLOAD_FIX.md
- FRONTEND_UPLOAD_FIX_V2.md
- REPOSITORY_RECOVERY_LEDGER.md
- REPO_SKILL_PLAYBOOK.md
- SECURITY_GATE0.md (move to docs/security/ or archive)

---

## Benefits

1. **Cleaner root directory** — 7 essential files instead of 47
2. **Better discoverability** — Clear location for each doc type
3. **Preserved history** — Nothing deleted, just organized
4. **Validated structure** — Follows the established docs/ system
5. **Easier navigation** — Contributors know where to look

---

**Ready to execute?**
