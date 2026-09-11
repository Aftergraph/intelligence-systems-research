from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "publication_artifact_registry.csv"
SHA40 = re.compile(r"^[0-9a-f]{40}$")

ALLOWED_STATUS = {
    "CURRENT_WORKING_MANUSCRIPT",
    "CANDIDATE_REAUDIT_REQUIRED",
    "SUPERSEDED_PENDING_RECONCILIATION",
    "WITHDRAWN",
    "PUBLICATION_READY",
}
ALLOWED_EXTERNAL_USE = {
    "DO_NOT_CITE",
    "HOLD_PENDING_REAUDIT",
    "WORKING_PAPER_WITH_DISCLOSURES",
    "EXTERNAL_USE_ALLOWED",
}


def _rows() -> list[dict[str, str]]:
    with REGISTRY.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_registry_has_required_fields_and_unique_ids() -> None:
    rows = _rows()
    assert rows
    assert len({row["artifact_id"] for row in rows}) == len(rows)
    for row in rows:
        assert row["artifact_id"]
        assert row["title"]
        assert row["source_path"].startswith("PAPERS/")
        assert SHA40.fullmatch(row["source_blob_sha"])
        assert row["evidence_cut"]
        assert row["status"] in ALLOWED_STATUS
        assert row["external_use"] in ALLOWED_EXTERNAL_USE
        assert row["last_verified"]
        assert (ROOT / row["source_path"]).is_file()


def test_paper01_cannot_be_externally_citable_while_reconciliation_is_open() -> None:
    paper = next(row for row in _rows() if row["artifact_id"] == "PAPER-01")
    assert paper["status"] == "SUPERSEDED_PENDING_RECONCILIATION"
    assert paper["external_use"] == "DO_NOT_CITE"


def test_reaudit_candidates_are_not_marked_external_use_allowed() -> None:
    for paper in _rows():
        if paper["status"] == "CANDIDATE_REAUDIT_REQUIRED":
            assert paper["external_use"] == "HOLD_PENDING_REAUDIT"


def test_working_paper_disclosure_is_not_equivalent_to_publication_ready() -> None:
    paper = next(row for row in _rows() if row["artifact_id"] == "PAPER-05")
    assert paper["status"] == "CURRENT_WORKING_MANUSCRIPT"
    assert paper["external_use"] == "WORKING_PAPER_WITH_DISCLOSURES"
