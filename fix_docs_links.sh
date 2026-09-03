#!/bin/bash

# Fix broken links from moved files

# Fix docs/README.md
sed -i 's|../ASKTHEPEOPLE_GODMODE_BUILDPLAN.md|architecture/ASKTHEPEOPLE_GODMODE_BUILDPLAN.md|g' docs/README.md

# Fix docs/architecture/index.md
sed -i 's|../../ASKTHEPEOPLE_GODMODE_BUILDPLAN.md|ASKTHEPEOPLE_GODMODE_BUILDPLAN.md|g' docs/architecture/index.md
sed -i 's|../..//ASKTHEPEOPLE_GODMODE_BUILDPLAN.md|ASKTHEPEOPLE_GODMODE_BUILDPLAN.md|g' docs/architecture/index.md

# Fix ADR links
sed -i 's|../../../ASKTHEPEOPLE_GODMODE_BUILDPLAN.md|../ASKTHEPEOPLE_GODMODE_BUILDPLAN.md|g' docs/architecture/adr/ADR-0001-product-category-and-truth-contract.md
sed -i 's|../../../ASKTHEPEOPLE_GODMODE_BUILDPLAN.md|../ASKTHEPEOPLE_GODMODE_BUILDPLAN.md|g' docs/architecture/adr/ADR-0011-incremental-modernization-over-rewrite.md

# Fix state-machines.md
sed -i 's|../../ASKTHEPEOPLE_GODMODE_BUILDPLAN.md|ASKTHEPEOPLE_GODMODE_BUILDPLAN.md|g' docs/architecture/state-machines.md

# Fix docs/release/GATE_0_RELEASE_NOTES.md
sed -i 's|../../ASKTHEPEOPLE_GODMODE_BUILDPLAN.md|../architecture/ASKTHEPEOPLE_GODMODE_BUILDPLAN.md|g' docs/release/GATE_0_RELEASE_NOTES.md

# Fix deployment guide links
sed -i 's|docs/release/RUNBOOK.md|../release/RUNBOOK.md|g' docs/deployment/*.md
sed -i 's|TODOS_COMPLETE.md|../archive/sessions/2026-09-03-intelligent-guidance/TODOS_COMPLETE.md|g' docs/deployment/QUICK_REFERENCE.md
sed -i 's|TODOS_COMPLETE.md|../archive/sessions/2026-09-03-intelligent-guidance/TODOS_COMPLETE.md|g' docs/deployment/READY_TO_DEPLOY.md

# Fix SECURITY_GATE0.md
sed -i 's|docs/release/RUNBOOK.md|../release/RUNBOOK.md|g' docs/security/SECURITY_GATE0.md

echo "Link fixes applied"
