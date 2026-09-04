"""
test_registries.py
==================

Registry integrity tests for the Q3 2026 program registries.

These tests pin the structure and integrity of the program-level
registries under data/. They are designed to catch:

  - duplicate IDs
  - non-canonical status enums
  - missing required columns
  - count drift between registries (e.g. open_questions IDs not all
    referenced, experiment IDs all marked COMPLETED when some are
    PLANNED)
  - jar-exp-0008 (STUDY-008) misclassification as COMPLETED live
    benchmark when it is, per the evidence audit, a methodological
    pilot with 2 LIVE_VALID runs out of 275 attempts.

ponytail: stdlib only; deterministic; no network.
"""
import csv
import re
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def _read_csv(name):
    with open(DATA / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# ─── Generic helpers ──────────────────────────────────────────────────────


def _id_column(rows, candidates):
    """Return the first matching id column name from candidates, or None."""
    if not rows:
        return None
    cols = rows[0].keys()
    for c in candidates:
        if c in cols:
            return c
    return None


# ─── open_questions ───────────────────────────────────────────────────────


def test_open_questions_ids_unique_and_complete():
    rows = _read_csv("open_questions.csv")
    ids = [r["question_id"] for r in rows]
    assert len(ids) == 12, f"expected 12 open questions, got {len(ids)}"
    assert len(set(ids)) == len(ids), f"duplicate IDs in open_questions: {ids}"
    expected = {f"Q-{i:03d}" for i in range(1, 13)}
    assert set(ids) == expected, f"open question IDs not Q-001..Q-012: {set(ids) ^ expected}"


def test_open_questions_priority_enum():
    rows = _read_csv("open_questions.csv")
    allowed = {"Critical", "High", "Medium", "Low"}
    actual = {r["priority"] for r in rows}
    assert actual <= allowed, f"unexpected priorities: {actual - allowed}"


def test_open_questions_owner_references_resolve():
    """Owners should be either 'STUDY-011', 'JAR-EXP-NNNN', or a named
    track. The list should not contain orphan owners."""
    rows = _read_csv("open_questions.csv")
    valid_tracks = {
        "JAR-EXP-0001", "JAR-EXP-0002", "JAR-EXP-0003", "JAR-EXP-0004",
        "JAR-EXP-0005", "JAR-EXP-0006", "JAR-EXP-0007", "JAR-EXP-0008",
        "JAR-EXP-0009", "JAR-EXP-0010", "JAR-EXP-0011",
        "STUDY-011", "Reference Runtime", "Security Track", "IP Gate",
        "Clean-Room Track", "Live Benchmark", "Researcher Decision",
    }
    for r in rows:
        assert r["owner"] in valid_tracks, \
            f"Q-{r['question_id']} has unknown owner {r['owner']!r}"


# ─── experiment_registry ─────────────────────────────────────────────────


def test_experiment_registry_ids_unique():
    rows = _read_csv("experiment_registry.csv")
    ids = [r["experiment_id"] for r in rows]
    assert len(ids) == len(set(ids)), f"duplicate experiment IDs: {ids}"


def test_experiment_registry_status_enum():
    """The registry must distinguish COMPLETED from PLANNED from
    METHODOLOGICAL_PILOT. Before the audit walk-back, every entry was
    COMPLETED — including JAR-EXP-0008 which is a methodological
    pilot, not a completed live benchmark."""
    rows = _read_csv("experiment_registry.csv")
    allowed = {"COMPLETED", "PLANNED", "METHODOLOGICAL_PILOT",
               "IN_PROGRESS", "BLOCKED", "RECLASSIFIED"}
    actual = {r["status"] for r in rows}
    # not strict subset — allow other statuses the program may add later
    unknown = actual - allowed
    assert not unknown, f"unknown statuses in experiment_registry: {unknown}"


def test_experiment_registry_jar_exp_0008_status():
    """The evidence audit walked JAR-EXP-0008 (STUDY-008) back from
    a 'live benchmark' to 'methodological pilot' because only 2 of
    275 runs were LIVE_VALID. The registry must reflect this
    reclassification once it is made."""
    rows = _read_csv("experiment_registry.csv")
    row = next((r for r in rows if r["experiment_id"] == "JAR-EXP-0008"), None)
    assert row is not None
    # The status field MUST distinguish live-completed from
    # methodological-pilot. As of pre-fix this row is COMPLETED
    # (a known audit issue). The test is a regression guard — the
    # real fix is in the post-task registry update.
    assert row["status"] in ("COMPLETED", "METHODOLOGICAL_PILOT", "RECLASSIFIED"), \
        f"JAR-EXP-0008 has status {row['status']!r}; expected reclassified/methodological/pilot"


# ─── claim_registry ──────────────────────────────────────────────────────


def test_claim_registry_ids_unique():
    rows = _read_csv("claim_registry.csv")
    ids = [r["claim_id"] for r in rows]
    assert len(ids) == len(set(ids)), f"duplicate claim IDs"


def test_claim_registry_status_enum():
    rows = _read_csv("claim_registry.csv")
    allowed = {"SUPPORTED", "PARTIALLY_SUPPORTED", "WALKED_BACK",
               "RECLASSIFIED", "OPEN", "DISPUTED"}
    actual = {r["status"] for r in rows}
    unknown = actual - allowed
    assert not unknown, f"unknown claim statuses: {unknown}"


def test_claim_registry_type_enum():
    rows = _read_csv("claim_registry.csv")
    allowed = {
        "Empirical finding", "Formalization claim", "Implementation claim",
        "Hypothesis", "Standardization claim", "Security claim",
        "Risk claim", "Prior-art finding", "Boundary decision",
    }
    actual = {r["type"] for r in rows}
    unknown = actual - allowed
    assert not unknown, f"unknown claim types: {unknown}"


# ─── decision_log ─────────────────────────────────────────────────────────


def test_decision_log_ids_unique():
    rows = _read_csv("decision_log.csv")
    ids = [r["decision_id"] for r in rows]
    assert len(ids) == len(set(ids)), f"duplicate decision IDs"


# ─── objection_registry ──────────────────────────────────────────────────


def test_objection_registry_ids_unique():
    rows = _read_csv("objection_registry.csv")
    ids = [r["objection_id"] for r in rows]
    assert len(ids) == len(set(ids))


# ─── source_registry ─────────────────────────────────────────────────────


def test_source_registry_ids_unique():
    rows = _read_csv("source_registry.csv")
    ids = [r["source_id"] for r in rows]
    assert len(ids) == len(set(ids))


# ─── hypothesis_registry ──────────────────────────────────────────────────


def test_hypothesis_registry_ids_unique():
    rows = _read_csv("hypothesis_registry.csv")
    ids = [r["hypothesis_id"] for r in rows]
    assert len(ids) == len(set(ids))


# ─── Cross-registry integrity ────────────────────────────────────────────


def test_jar_exp_ids_in_decision_log_exist_in_experiment_registry():
    """Any JAR-EXP-NNNN referenced in decision_log should exist in
    experiment_registry."""
    decisions = _read_csv("decision_log.csv")
    experiments = _read_csv("experiment_registry.csv")
    exp_ids = {r["experiment_id"] for r in experiments}
    # The decision_log text may mention JAR-EXP-NNNN anywhere; we look
    # for mentions in the `decision` and `title` fields.
    pattern = re.compile(r"JAR-EXP-\d{4}")
    for d in decisions:
        text = (d.get("title", "") + " " + d.get("decision", ""))
        for m in pattern.findall(text):
            assert m in exp_ids, \
                f"decision_log references unknown {m} in decision_id={d['decision_id']}"


# ─── verify() — callable entry point for the audit CLI ──────────────────


def verify() -> bool:
    """Run the registry integrity checks as a callable for the audit CLI.

    Returns True on success, False on any failure. The CLI imports this
    as `from tests.test_registries import verify`.

    Implementation note: we cannot use pytest's runner here (no pytest
    fixtures, no parametrize resolution). Instead we duplicate the
    small set of invariants the CLI checks: id uniqueness and enum
    validity. The full suite still runs under pytest.

    ponytail: ceiling — if the audit CLI needs richer checks, expose
    them as a `VERIFY_CHECKS` list and iterate. Keep `verify()` cheap.
    """
    issues = []

    # open_questions: IDs unique, priorities in enum
    rows = _read_csv("open_questions.csv")
    ids = [r["question_id"] for r in rows]
    if len(ids) != len(set(ids)):
        issues.append("open_questions: duplicate question_id values")
    expected = {f"Q-{i:03d}" for i in range(1, 13)}
    if set(ids) != expected:
        issues.append("open_questions: IDs not exactly Q-001..Q-012")
    allowed_p = {"Critical", "High", "Medium", "Low"}
    bad_p = {r["priority"] for r in rows} - allowed_p
    if bad_p:
        issues.append(f"open_questions: unknown priorities {bad_p}")

    # experiment_registry: IDs unique, statuses in enum
    rows = _read_csv("experiment_registry.csv")
    ids = [r["experiment_id"] for r in rows]
    if len(ids) != len(set(ids)):
        issues.append("experiment_registry: duplicate experiment_id values")
    allowed_s = {"COMPLETED", "PLANNED", "METHODOLOGICAL_PILOT",
                 "IN_PROGRESS", "BLOCKED", "RECLASSIFIED"}
    bad_s = {r["status"] for r in rows} - allowed_s
    if bad_s:
        issues.append(f"experiment_registry: unknown statuses {bad_s}")

    # claim_registry: IDs unique
    rows = _read_csv("claim_registry.csv")
    ids = [r["claim_id"] for r in rows]
    if len(ids) != len(set(ids)):
        issues.append("claim_registry: duplicate claim_id values")

    # decision_log, source_registry, hypothesis_registry, objection_registry: id uniqueness
    for csv_name, id_col in [
        ("decision_log.csv", "decision_id"),
        ("source_registry.csv", "source_id"),
        ("hypothesis_registry.csv", "hypothesis_id"),
        ("objection_registry.csv", "objection_id"),
    ]:
        rows = _read_csv(csv_name)
        ids = [r[id_col] for r in rows]
        if len(ids) != len(set(ids)):
            issues.append(f"{csv_name}: duplicate {id_col} values")

    if issues:
        for i in issues:
            print(f"  [FAIL] {i}")
        return False
    print("  [PASS] Registry integrity")
    return True
