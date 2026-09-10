"""Tests for SDC-B0 Task #75: independent green-branch verifier."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from sdc_b0.green_verifier import IndependentVerifier, VerificationVerdict, Verdict
from sdc_b0.telemetry import TelemetryCollector
from sdc_b0.semantic_progress import UnmergedBranch

BASE_SHA = "a5dccc8a4825118a85471d210d832ed479b79b72"

@pytest.fixture
def tmp_log(tmp_path):
    return tmp_path / "test.jsonl"

class TestIndependentVerifier:
    def test_verify_returns_verification_verdict(self, tmp_log):
        tmp_log.write_text("")
        v = IndependentVerifier(verifier_id="test-verifier")
        result = v.verify("main", BASE_SHA, BASE_SHA, telemetry_log_path=tmp_log)
        assert isinstance(result, VerificationVerdict)
        assert result.candidate_branch == "main"
        assert result.candidate_sha == BASE_SHA
        assert result.base_sha == BASE_SHA
        assert result.verified_at != ""

    def test_verify_valid_sha_no_negative_events_is_ship(self, tmp_log):
        events = [
            {"event_type": "test_coverage_verified", "timestamp": "2026-09-10T00:00:00Z", "data": {"coverage": 85}},
            {"event_type": "bug_closure_verified", "timestamp": "2026-09-10T00:01:00Z", "data": {"issue": 42}},
        ]
        with open(tmp_log, "w") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")
        v = IndependentVerifier(verifier_id="test-verifier")
        result = v.verify("main", BASE_SHA, BASE_SHA, telemetry_log_path=tmp_log)
        assert result.verdict == Verdict.SHIP

    def test_verify_unmerged_branch_with_conflicts_blocks_ship(self, tmp_log):
        tmp_log.write_text("")
        branches = [UnmergedBranch(branch_name="feat/x", age_hours=1.0, conflict_count=1)]
        v = IndependentVerifier(verifier_id="test-verifier")
        result = v.verify("main", BASE_SHA, BASE_SHA, telemetry_log_path=tmp_log, unmerged_branches=branches)
        assert result.verdict == Verdict.DO_NOT_SHIP
        assert any("conflict" in r for r in result.reasons)

    def test_verify_nonexistent_log_with_valid_sha_can_ship(self, tmp_path):
        v = IndependentVerifier(verifier_id="test-verifier")
        result = v.verify("main", BASE_SHA, BASE_SHA, telemetry_log_path=tmp_path / "nonexistent.jsonl")
        assert result.verdict == Verdict.SHIP

    def test_verify_emits_telemetry_events(self, tmp_path):
        collector = TelemetryCollector(run_id="test-run", log_dir=tmp_path)
        v = IndependentVerifier(verifier_id="test-verifier", telemetry=collector)
        input_log = tmp_path / "input.jsonl"
        input_log.write_text("")
        v.verify("main", BASE_SHA, BASE_SHA, telemetry_log_path=input_log)
        tel_file = tmp_path / "test-run.jsonl"
        assert tel_file.exists()
        content = tel_file.read_text()
        assert "verification_start" in content
        assert "verification_result" in content
        assert "test-verifier" in content

    def test_verify_verdict_has_score_and_debt(self, tmp_log):
        tmp_log.write_text("")
        v = IndependentVerifier(verifier_id="test-verifier")
        result = v.verify("main", BASE_SHA, BASE_SHA, telemetry_log_path=tmp_log)
        assert isinstance(result.score, int)
        assert isinstance(result.debt, float)

    def test_verify_verdict_has_test_results(self, tmp_log):
        tmp_log.write_text("")
        v = IndependentVerifier(verifier_id="test-verifier")
        result = v.verify("main", BASE_SHA, BASE_SHA, telemetry_log_path=tmp_log)
        assert isinstance(result.test_results, list)

class TestVerificationVerdict:
    def test_verdict_dataclass_fields(self):
        v = VerificationVerdict(
            verdict=Verdict.SHIP, candidate_branch="main", candidate_sha="abc",
            base_sha="def", reasons=[], score=1, debt=0.0,
            test_results=[], reconciliation_branches=[], verified_at="2026-09-10T00:00:00Z"
        )
        assert v.verdict == Verdict.SHIP
        assert v.score == 1
        assert v.debt == 0.0

    def test_do_not_ship_verdict(self):
        v = VerificationVerdict(
            verdict=Verdict.DO_NOT_SHIP, candidate_branch="feat/x", candidate_sha="abc",
            base_sha="def", reasons=["unmerged_branches_with_conflicts"], score=-1, debt=0.0,
            test_results=[], reconciliation_branches=[], verified_at="2026-09-10T00:00:00Z"
        )
        assert v.verdict == Verdict.DO_NOT_SHIP
        assert len(v.reasons) == 1
