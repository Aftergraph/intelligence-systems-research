"""Test-suite shared contract resolution.

Resolves the canonical mission-state/1.0.json contract without requiring a
side-by-side checkout of after-graph-governance. Resolution order:

1. AGC_CONTRACTS_DIR env var  -> $AGC_CONTRACTS_DIR/mission-state/1.0.json
2. side-by-side sibling       -> <parent-of-repo>/after-graph-governance/... (legacy layout)
3. vendored copy              -> <repo>/contracts/mission-state/1.0.json (always present)

The vendored copy is pinned by scripts/sync-mission-state-contract.sh, which
fails loudly when it diverges from GOV remote main.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VENDORED = REPO_ROOT / "contracts" / "mission-state" / "1.0.json"
LEGACY_SIBLING = REPO_ROOT.parent / "after-graph-governance" / "docs" / "contracts" / "mission-state" / "1.0.json"


def resolve_contract_path() -> Path:
    import os

    env_dir = os.environ.get("AGC_CONTRACTS_DIR")
    if env_dir:
        candidate = Path(env_dir) / "mission-state" / "1.0.json"
        if candidate.exists():
            return candidate

    if LEGACY_SIBLING.exists():
        return LEGACY_SIBLING

    if VENDORED.exists():
        return VENDORED

    raise FileNotFoundError(
        "mission-state/1.0.json not found. Set AGC_CONTRACTS_DIR, keep the "
        "side-by-side after-graph-governance checkout, or re-run "
        "scripts/sync-mission-state-contract.sh to restore the vendored copy."
    )