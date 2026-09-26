#!/usr/bin/env bash
set -euo pipefail

repo="${1:-}"
environment="${2:-provider-smoke}"
if [[ -z "$repo" ]]; then
  echo "usage: $0 OWNER/REPO [ENVIRONMENT]" >&2
  exit 2
fi
command -v gh >/dev/null 2>&1 || { echo "gh CLI is required" >&2; exit 3; }
: "${TYPESAFE_API_KEY:?TYPESAFE_API_KEY must already be present in the process environment}"
: "${DIALAGRAM_API_KEY:?DIALAGRAM_API_KEY must already be present in the process environment}"

gh api --method PUT "repos/${repo}/environments/${environment}" >/dev/null
printf '%s' "$TYPESAFE_API_KEY" | gh secret set TYPESAFE_API_KEY --repo "$repo" --env "$environment"
printf '%s' "$DIALAGRAM_API_KEY" | gh secret set DIALAGRAM_API_KEY --repo "$repo" --env "$environment"

echo "GitHub environment secrets installed: ${repo} / ${environment}"
# Do not print, fingerprint, or persist secret values here.
