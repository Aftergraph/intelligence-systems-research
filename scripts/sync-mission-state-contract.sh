#!/usr/bin/env bash
# sync-mission-state-contract.sh — pin the vendored mission-state/1.0.json to GOV remote truth.
#
# The conformance suite (tests/conftest.py) falls back to the vendored copy when
# after-graph-governance is not checked out side-by-side. THIS script is how that
# copy stays exact-head: it fetches the contract from GOV remote main via the
# GitHub API and refuses to update (or restore) the vendored copy when the fetch
# fails or the schema does not validate.
#
# Usage:
#   bash scripts/sync-mission-state-contract.sh             # fetch + replace vendored copy
#   bash scripts/sync-mission-state-contract.sh --check     # verify only; exit 1 on drift/failure
#
# Exit codes: 0 = vendored copy matches GOV remote main (or was updated)
#             1 = drift or unreachable GOV (no mutation performed)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST_DIR="$REPO_ROOT/contracts/mission-state"
DEST="$DEST_DIR/1.0.json"
CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI required (GitHub API fetch)." >&2
  exit 1
fi

GOV_REPO="Aftergraph/after-graph-governance"
PATH_IN_REPO="docs/contracts/mission-state/1.0.json"

# NOTE: JSON content is never held in a shell variable — command substitution
# strips trailing newlines, which corrupted byte-identity twice. Stream raw.
remote_sha=$(gh api "repos/$GOV_REPO/contents/$PATH_IN_REPO?ref=main" --jq '.sha')
remote_content_b64=$(gh api "repos/$GOV_REPO/contents/$PATH_IN_REPO?ref=main" --jq '.content') || true

if [ -z "$remote_sha" ] || [ -z "$remote_content_b64" ]; then
  echo "ERROR: could not fetch mission-state/1.0.json from $GOV_REPO main." >&2
  echo "       (network blocked or API rate-limited) — vendored copy left untouched." >&2
  exit 1
fi

# Structural sanity before any mutation (12-state enum expected)
if ! printf '%s' "$remote_content_b64" | tr -d '\n' | base64 -d 2>/dev/null | jq -e '.properties.state.enum | length == 12' >/dev/null 2>&1; then
  echo "ERROR: fetched contract failed structural sanity (12-state enum expected). Not updating." >&2
  exit 1
fi

byte_match=0
if [ -f "$DEST" ]; then
  # raw stream comparison preserves exact bytes on both sides
  if printf '%s' "$remote_content_b64" | tr -d '\n' | base64 -d 2>/dev/null | cmp -s - "$DEST"; then
    byte_match=1
  fi
fi

if [ "$CHECK_ONLY" = 1 ]; then
  if [ "$byte_match" = 1 ]; then
    echo "OK: vendored mission-state/1.0.json matches $GOV_REPO main ($remote_sha)"
    exit 0
  fi
  echo "DRIFT: vendored != GOV main $remote_sha — run sync-mission-state-contract.sh to re-pin." >&2
  exit 1
fi

mkdir -p "$DEST_DIR"
printf '%s' "$remote_content_b64" | tr -d '\n' | base64 -d > "$DEST"
echo "Vendored mission-state/1.0.json updated (GOV main $remote_sha)"