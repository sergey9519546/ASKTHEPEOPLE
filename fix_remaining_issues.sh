#!/bin/bash

# Fix multiple H1 headers - convert second H1 to H2
for file in docs/deployment/CELERY_WORKER_SETUP.md docs/deployment/DEPLOYMENT_OPTIONS.md docs/deployment/RAILWAY_FREE_TRIAL_STRATEGY.md docs/deployment/RAILWAY_SETUP.md docs/security/SECURITY_GATE0.md; do
  if [ -f "$file" ]; then
    # After first H1, convert subsequent # to ##
    awk 'BEGIN {h1_count=0} /^# [^#]/ {h1_count++; if(h1_count==1) print; else print "#" $0; next} {print}' "$file" > "${file}.tmp"
    mv "${file}.tmp" "$file"
    echo "Fixed H1 headers in $file"
  fi
done

# Fix deployment guide links to design docs
sed -i 's|docs/design/|../design/|g' docs/deployment/QUICK_REFERENCE.md
sed -i 's|docs/design/|../design/|g' docs/deployment/READY_TO_DEPLOY.md

# Fix README observability link
sed -i 's|../release/OBSERVABILITY.md|../release/RUNBOOK.md|g' docs/deployment/README.md

# Comment out placeholder tokens in RAILWAY_SETUP.md
sed -i 's|<your-openai-key>|# <your-openai-key> (replace with actual key)|g' docs/deployment/RAILWAY_SETUP.md
sed -i 's|<your-zep-cloud-key>|# <your-zep-cloud-key> (replace with actual key)|g' docs/deployment/RAILWAY_SETUP.md
sed -i 's|<your-brave-key>|# <your-brave-key> (replace with actual key)|g' docs/deployment/RAILWAY_SETUP.md
sed -i 's|<your-sentry-dsn>|# <your-sentry-dsn> (replace with actual DSN)|g' docs/deployment/RAILWAY_SETUP.md

echo "All fixes applied"
