from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def _rows(name: str) -> dict[str, dict[str, str]]:
    with (DATA / name).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    key = "claim_id" if name == "claim_registry.csv" else "hypothesis_id"
    return {row[key]: row for row in rows}


def test_claim_registry_exposes_evidence_scope_and_freshness() -> None:
    claims = _rows("claim_registry.csv")
    assert len(claims) == 18
    for row in claims.values():
        assert row["evidence_scope"]
        assert row["source_refs"]
        assert row["last_verified"] == "2026-09-11"


def test_human_ux_claim_cannot_be_supported_with_zero_humans() -> None:
    c004 = _rows("claim_registry.csv")["C-004"]
    h003 = _rows("hypothesis_registry.csv")["H-003"]
    assert c004["status"] == "OPEN"
    assert "HUMAN_UNTESTED" in c004["evidence_scope"]
    assert h003["status"] == "OPEN"
    assert "HUMAN_UNTESTED" in h003["evidence_scope"]


def test_live_confirmatory_h1_reversal_is_not_flattened_to_supported() -> None:
    c002 = _rows("claim_registry.csv")["C-002"]
    h001 = _rows("hypothesis_registry.csv")["H-001"]
    assert c002["status"] == "PARTIALLY_SUPPORTED"
    assert "LIVE_CONFIRMATORY_H1_REVERSED" in c002["evidence_scope"]
    assert h001["status"] == "REVERSED"
    assert "LIVE_CONFIRMATORY_REVERSED" in h001["evidence_scope"]


def test_simulated_economics_are_not_unconditionally_supported() -> None:
    claims = _rows("claim_registry.csv")
    for claim_id in ("C-005", "C-016"):
        assert claims[claim_id]["status"] == "PARTIALLY_SUPPORTED"
        assert "SIMULATION_SUPPORTED" in claims[claim_id]["evidence_scope"]


def test_in_tree_alternate_runtime_is_not_external_replication() -> None:
    c018 = _rows("claim_registry.csv")["C-018"]
    assert c018["status"] == "PARTIALLY_SUPPORTED"
    assert "EXTERNAL_REPLICATION_PENDING" in c018["evidence_scope"]


def test_executive_summary_names_frozen_study011_verdicts() -> None:
    summary = (ROOT / "00-EXECUTIVE-SUMMARY.md").read_text(encoding="utf-8")
    assert "470 `LIVE_VALID`" in summary
    assert "H1 REVERSED / H2 SUPPORTED / H3 REVERSED" in summary
    assert "STUDY-011 LIVE CONFIRMATORY RUN EXECUTED AND FROZEN" in summary
    assert "LIVE CONFIRMATORY" in summary
    assert "N=0 HUMANS" in summary
