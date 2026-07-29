#!/usr/bin/env bash
set -u

if [ "$#" -ne 1 ]; then
  echo "::error::inspect-image-digest requires exactly one registry reference." >&2
  exit 2
fi

reference="$1"
error_file="$(mktemp)"
trap 'rm -f "$error_file"' EXIT

if output="$(
  docker buildx imagetools inspect "$reference" 2>"$error_file"
)"; then
  digest="$(
    printf '%s' "$output" |
      awk '$1 == "Digest:" { print $2; exit }'
  )"
  if ! printf '%s' "$digest" |
    grep -Eq '^sha256:[0-9a-f]{64}$'; then
    echo "::error::Registry inspection returned no valid digest for ${reference}." >&2
    exit 2
  fi
  printf '%s' "$digest"
  exit 0
fi

# OCI registries distinguish a missing manifest from transport, authorization,
# and server failures. Only the known manifest-absent forms return 1; every
# other inspection failure is fail-closed with status 2.
if grep -Eqi \
  'manifest unknown|MANIFEST_UNKNOWN|not found: manifest|: not found$' \
  "$error_file"; then
  exit 1
fi

echo "::error::Registry inspection failed for ${reference}; refusing to treat it as absent." >&2
exit 2
