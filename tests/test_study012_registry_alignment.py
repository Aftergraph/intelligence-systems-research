import csv
from pathlib import Path


DATA = Path(__file__).resolve().parent.parent / "data"


def _rows(name: str):
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_study012_experiment_is_registered_without_result_claim():
    row = next(
        (r for r in _rows("experiment_registry.csv") if r["experiment_id"] == "ICT-EXP-0001"),
        None,
    )
    assert row is not None
    assert row["status"] == "IN_PROGRESS"
    assert "I6" in row["design"] and "I5" in row["design"]
    assert "3 domains" in row["design"] and "10 canonical scenarios" in row["design"]


def test_institution_layer_incremental_benefit_claim_remains_open_pre_results():
    row = next((r for r in _rows("claim_registry.csv") if r["claim_id"] == "C-019"), None)
    assert row is not None
    assert row["type"] == "Hypothesis"
    assert row["status"] == "OPEN"
    assert "STUDY-012" in row["notes"]
    assert "no confirmatory" in row["notes"].lower()


def test_study012_hypothesis_is_falsification_first_and_bound_to_open_claim():
    row = next(
        (r for r in _rows("hypothesis_registry.csv") if r["hypothesis_id"] == "H-008"),
        None,
    )
    assert row is not None
    assert row["claim_ref"] == "C-019"
    assert row["status"] == "OPEN"
    assert "I6" in row["alt_hypothesis"] and "I5" in row["alt_hypothesis"]
    assert "non-inferior" in row["falsification_condition"].lower()
    assert "cheaper" in row["falsification_condition"].lower()


def test_study012_registry_alignment_does_not_predeclare_support():
    claims = {r["claim_id"]: r for r in _rows("claim_registry.csv")}
    hypotheses = {r["hypothesis_id"]: r for r in _rows("hypothesis_registry.csv")}
    assert claims["C-019"]["status"] != "SUPPORTED"
    assert hypotheses["H-008"]["status"] != "SUPPORTED"
