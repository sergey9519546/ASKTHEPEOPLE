#!/usr/bin/env bash
# Self-test for the two grep gates in .github/workflows/docs.yml.
#
# Why this exists: both gates previously used a MULTI-LINE parenthesised ERE.
# GNU grep cannot compile that ("Unmatched ( or \("), and because the pipeline
# ends in `|| true` the error was swallowed, HITS came back empty, and the
# naked-wordmark gate reported PASS on every run in the repository's history.
# It had never caught a single violation.
#
# This script asserts three things:
#   1. every ERE compiles (grep exits 2 on a regex error, 1 on clean no-match)
#   2. each gate FAILS on a deliberately planted violation
#   3. each gate's result on the clean tree
#
# Run: bash scripts/release/check-docs-gates.sh
# Add to scripts/release/verify as a gate so this cannot regress silently.
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 1

PRODUCT_NAME="ASKTHEPEOPLE"
ALLOWLIST_REGEX='(^docs/archive/|/archive/|LICENSE|/LICENSES/|README\.md|INTEGRATION_GUIDE\.md|ASKTHEPEOPLE_GODMODE_BUILDPLAN\.md|THIRD_PARTY_NOTICES\.md|PROVENANCE\.md|docs/release/ACCEPTANCE\.md|docs/privacy/DATA_MAP\.md|docs/privacy/SUBPROCESSORS\.md)'
NON_PROSE_REGEX='(https?://|assets/|C:/Users|/c/Users|"service":|"repo":|github\.com)'
DESCRIPTOR_REGEX='(generated decision explorer|generated scenario exploration|synthetic decision explorer|synthetic scenario exploration|research-planning handoff)'
PROHIBITED="predict what people will do|predict public response|ask thousands of people instantly|know what people think|human-level accuracy|digital twin of (your|the) (audience|users|customers|people)|bias-free personas|scientifically proven (people |)simulation|representative synthetic sample|validate the decision (with|using) ASKTHEPEOPLE"
DEFINING_DOCS='^(docs/architecture/adr/ADR-0001-product-category-and-truth-contract\.md|docs/architecture/ASKTHEPEOPLE_GODMODE_BUILDPLAN\.md|docs/architecture/ULTRAPLAN\.md):'
WORDMARK_PATHS=("README.md" "docs/release/" "docs/privacy/")
SCAN_PATHS=("README.md" "docs/design/" "docs/release/" "docs/architecture/" "docs/ai/" "docs/privacy/")

fails=0

echo "== step 1: every ERE must compile =="
# grep: 0 = matched, 1 = compiled but no match, 2 = regex error
while IFS= read -r re; do
  [ -z "$re" ] && continue
  printf 'x\n' | grep -E "$re" >/dev/null 2>&1
  rc=$?
  if [ "$rc" -eq 2 ]; then
    echo "  FAIL  does not compile: $re"
    fails=$((fails+1))
  else
    echo "  OK    compiles (grep exit $rc)"
  fi
done <<EOF
${ALLOWLIST_REGEX}
${NON_PROSE_REGEX}
${PROHIBITED}
${DEFINING_DOCS}
EOF

echo
echo "== step 2: gates must catch a planted violation =="
PLANT="docs/release/__gate_self_test__.md"
cleanup() { rm -f "$PLANT"; }
trap cleanup EXIT
printf '# Gate self-test\n\nASKTHEPEOPLE and predict what people will do.\n' > "$PLANT"

wm=$(grep -RIn --include="*.md" -E "\b${PRODUCT_NAME}\b" "${WORDMARK_PATHS[@]}" 2>/dev/null | grep -vE "${ALLOWLIST_REGEX}" | grep -vE "${NON_PROSE_REGEX}" | grep -vEi "${DESCRIPTOR_REGEX}" || true)
pl=$(grep -RInE "${PROHIBITED}" "${SCAN_PATHS[@]}" 2>/dev/null | grep -vE "${DEFINING_DOCS}" || true)
if printf '%s' "$wm" | grep -q '__gate_self_test__'; then
  echo "  OK    wordmark gate caught the planted file"
else
  echo "  FAIL  wordmark gate MISSED the planted file (gate is inert)"
  fails=$((fails+1))
fi
if printf '%s' "$pl" | grep -q '__gate_self_test__'; then
  echo "  OK    prohibited-language gate caught the planted file"
else
  echo "  FAIL  prohibited-language gate MISSED the planted file (gate is inert)"
  fails=$((fails+1))
fi
cleanup

echo
echo "== step 3: clean-tree result =="
wm2=$(grep -RIn --include="*.md" -E "\b${PRODUCT_NAME}\b" "${WORDMARK_PATHS[@]}" 2>/dev/null | grep -vE "${ALLOWLIST_REGEX}" | grep -vE "${NON_PROSE_REGEX}" | grep -vEi "${DESCRIPTOR_REGEX}" || true)
pl2=$(grep -RInE "${PROHIBITED}" "${SCAN_PATHS[@]}" 2>/dev/null | grep -vE "${DEFINING_DOCS}" || true)
n_wm=$(printf '%s\n' "$wm2" | grep -c . || true)
n_pl=$(printf '%s\n' "$pl2" | grep -c . || true)
echo "  naked-wordmark violations: $n_wm"
echo "  prohibited-language hits:  $n_pl"
if [ "$n_wm" -gt 0 ] || [ "$n_pl" -gt 0 ]; then
  printf '%s\n' "$wm2" | sed 's/^/    WM /' | head -15
  printf '%s\n' "$pl2" | sed 's/^/    PL /' | head -15
  fails=$((fails+1))
fi

echo
if [ "$fails" -gt 0 ]; then
  echo "RESULT: FAIL ($fails problem(s))"
  exit 1
fi
echo "RESULT: PASS (gates compile and are armed)"
exit 0