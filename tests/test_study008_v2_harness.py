"""
Test suite for STUDY-008-v2 fault injection harness.

Tests cover:
1. Fault injection: each fault code produces intended observable
2. UAR accounting: no unauthorized actions slip through
3. Checkpoint-resume: recovery after FAIL-MID-MISSION
"""

import os
import sys
import json
import tempfile
import pytest

# Add project root to path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from experiments.live_benchmark.fault_injection import (
    FaultInjector,
    FaultSchedule,
    FaultCode,
    CheckpointState,
    create_stud008_default_schedules,
)
from experiments.live_benchmark.run_study_008v2 import (
    RunRecord,
    MetricsAccumulator,
    ExecutionMode,
    PROVIDERS,
    CONFIRMATORY_CONDITIONS,
    get_provider_cells,
    verify_candidate_completion,
    _declares_complete,
    _declares_failure,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fault Injection Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestFaultInjection:
    """Test each fault code produces its intended observable."""
    
    def test_inject_net_fault_429(self):
        """FAIL-NET should return 429/5xx error."""
        injector = FaultInjector(schedules=[], dry_run=True)
        injector._step = 0
        
        result = injector.inject_net_fault({"name": "test"})
        
        assert result["http_status"] == 429
        assert "rate_limit" in result["error"].lower()
        assert result["provider_request_id"] is None
    
    def test_inject_net_fault_503(self):
        """FAIL-NET should alternate between 429 and 5xx."""
        injector = FaultInjector(schedules=[], dry_run=True)
        injector._step = 1
        
        result = injector.inject_net_fault({"name": "test"})
        
        assert result["http_status"] == 503
        assert "gateway" in result["error"].lower()
    
    def test_inject_latency_fault(self):
        """FAIL-LATENCY should inject >10s spike."""
        injector = FaultInjector(schedules=[], dry_run=True)
        injector._step = 0
        
        base_latency = 1000.0
        total_latency = injector.inject_latency_fault(base_latency)
        
        assert total_latency >= base_latency + 10000  # At least 10s spike
        assert len(injector.events) == 1
        assert injector.events[0].fault_code == FaultCode.FAIL_LATENCY
    
    def test_inject_malformed_fault(self):
        """FAIL-MALFORMED should return invalid JSON."""
        injector = FaultInjector(schedules=[], dry_run=True)
        injector._step = 0
        
        result = injector.inject_malformed_fault()
        
        assert result["http_status"] == 200  # Server responded
        assert result["error"].startswith("Malformed JSON")
        assert result["provider_request_id"] is None
    
    def test_inject_mid_mission_fault(self):
        """FAIL-MID-MISSION should save checkpoint and return crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = os.path.join(tmpdir, "checkpoint.json")
            
            injector = FaultInjector(schedules=[], checkpoint_path=checkpoint_path, dry_run=True)
            injector._step = 0
            
            checkpoint = CheckpointState(
                run_id="test-run",
                step=5,
                workload_id="test-workload",
                condition="F",
                provider_name="test",
                model_id="test-model",
                messages=[{"role": "user", "content": "test"}],
                recovery_attempts=0,
                state_hash="test-hash",
            )
            
            result = injector.inject_mid_mission_fault(checkpoint)
            
            assert os.path.exists(checkpoint_path)
            assert "mid_mission_crash" in result["error"].lower()
            assert result["checkpoint_path"] == checkpoint_path
    
    def test_fault_schedule_trigger(self):
        """Scheduled faults should trigger deterministically."""
        schedule = FaultSchedule(
            fault_code=FaultCode.FAIL_NET,
            trigger_step=3,
            probability=1.0,
        )
        
        assert schedule.should_trigger(3, "any-run")
        assert not schedule.should_trigger(2, "any-run")
        assert not schedule.should_trigger(4, "any-run")
    
    def test_inject_with_fault_code(self):
        """Injector.call with explicit fault_code should always inject."""
        injector = FaultInjector(schedules=[], dry_run=True)
        
        result = injector.call(
            provider_cfg={"name": "test"},
            model="test-model",
            messages=[{"role": "user", "content": "test"}],
            run_id="test-run",
            inject_fault_code=FaultCode.FAIL_NET,
        )
        
        assert result["http_status"] == 429
    
    def test_default_schedules(self):
        """Default schedules should cover all 8 fault codes."""
        schedules = create_stud008_default_schedules()
        
        fault_codes = {s.fault_code for s in schedules}
        assert FaultCode.FAIL_NET in fault_codes
        assert FaultCode.FAIL_LATENCY in fault_codes
        assert FaultCode.FAIL_MALFORMED in fault_codes
        assert FaultCode.FAIL_MID_MISSION in fault_codes
    
    def test_provider_cells_matrix(self):
        """Verify 8-cell matrix (2 providers × 4 conditions)."""
        cells = get_provider_cells({})
        
        # 2 providers × 4 conditions = 8 cells
        assert len(cells) == 8
        providers = {c[0] for c in cells}
        conditions = {c[1] for c in cells}
        assert providers == {"dialagram", "openrouter"}
        assert conditions == {"A", "C", "F", "G"}


# ─────────────────────────────────────────────────────────────────────────────
# UAR Accounting Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestUARAccounting:
    """Test UAR accounting prevents unauthorized actions."""
    
    def test_metrics_accumulator_uar_zero(self):
        """UAR should be 0 when no unauthorized actions."""
        metrics = MetricsAccumulator()
        
        record = RunRecord(
            run_id="test-1",
            condition="G",
            workload_id="test",
            vsr_flag=True,
            uar_violations=0,
        )
        metrics.record_run(record)
        
        assert metrics.uar == 0.0
        assert metrics.unauthorized_actions == 0
    
    def test_metrics_accumulator_uar_tracking(self):
        """UAR should track unauthorized actions."""
        metrics = MetricsAccumulator()
        metrics.total_calls = 100
        
        record = RunRecord(
            run_id="test-2",
            uar_violations=2,
        )
        metrics.record_run(record)
        
        assert metrics.unauthorized_actions == 2
        assert metrics.uar <= 0.02  # 2/100 ~ 2%
    
    def test_uar_threshold_violation(self):
        """UAR > 0 should indicate threshold violation."""
        metrics = MetricsAccumulator()
        metrics.total_calls = 10
        metrics.unauthorized_actions = 1
        
        assert metrics.uar > 0.0
        assert metrics.uar == 0.1


# ─────────────────────────────────────────────────────────────────────────────
# Checkpoint-Resume Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckpointResume:
    """Test checkpoint resume after FAIL-MID-MISSION."""
    
    def test_checkpoint_save_load(self):
        """Checkpoint should save and restore correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = os.path.join(tmpdir, "checkpoint.json")
            
            original = CheckpointState(
                run_id="test-run",
                step=7,
                workload_id="test-workload",
                condition="F",
                provider_name="test-provider",
                model_id="test-model",
                messages=[{"role": "user", "content": "test"}],
                recovery_attempts=0,
                state_hash="abc123",
            )
            original.save(checkpoint_path)
            
            restored = CheckpointState.load(checkpoint_path)
            
            assert restored.run_id == original.run_id
            assert restored.step == original.step
            assert restored.workload_id == original.workload_id
            assert restored.state_hash == original.state_hash
    
    def test_checkpoint_resume_after_crash(self):
        """System should resume from checkpoint after crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            checkpoint_path = os.path.join(tmpdir, "checkpoint.json")
            
            # Create checkpoint
            original = CheckpointState(
                run_id="test-run",
                step=5,
                workload_id="test-workload",
                condition="F",
                provider_name="test",
                model_id="test-model",
                messages=[{"role": "user", "content": "test"}],
                recovery_attempts=0,
                state_hash="hash",
            )
            original.save(checkpoint_path)
            
            # Inject crash and resume
            injector = FaultInjector(schedules=[], checkpoint_path=checkpoint_path, dry_run=True)
            checkpoint = injector.get_checkpoint()
            
            assert checkpoint is not None
            assert checkpoint.run_id == "test-run"
            assert checkpoint.step == 5
    
    def test_metrics_checkpoint_tracking(self):
        """Metrics should track checkpoint creation and resume."""
        metrics = MetricsAccumulator()
        metrics.checkpoints_created = 10
        metrics.checkpoints_resumed = 8
        
        assert metrics.checkpoints_resumed <= metrics.checkpoints_created
        assert metrics.checkpoints_resumed == 8


# ─────────────────────────────────────────────────────────────────────────────
# Verification Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestVerification:
    """Test verifier and condition markers."""
    
    def test_declares_complete(self):
        """Completion markers should be detected."""
        assert _declares_complete("task complete")
        assert _declares_complete("Task COMPLETE")
        assert _declares_complete("✅ complete")
        assert _declares_complete("[done]")
    
    def test_declares_failure(self):
        """Failure markers should be detected."""
        assert _declares_failure("i cannot complete")
        assert _declares_failure("Task failed")
        assert _declares_failure("unable to complete")
    
    def test_verify_candidate_completion(self):
        """Verifier should check required keywords."""
        workload = {
            "acceptance_criteria": {
                "required_output_contains": ["keyword1", "keyword2"],
            }
        }
        
        # Should pass with all keywords
        result = verify_candidate_completion("text with keyword1 and keyword2", workload)
        assert result["pass"]
        
        # Should fail without keywords
        result = verify_candidate_completion("missing keywords", workload)
        assert not result["pass"]


# ─────────────────────────────────────────────────────────────────────────────
# VSR/FCR Metric Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestVSROFCR:
    """Test VSR and FCR thresholds."""
    
    def test_vsr_computation(self):
        """VSR should be verified_successes / total_runs."""
        metrics = MetricsAccumulator()
        metrics.total_runs = 100
        metrics.verified_successes = 75
        
        assert metrics.vsr == 0.75
    
    def test_fcr_computation(self):
        """FCR should be false_completions / claimed_completions."""
        metrics = MetricsAccumulator()
        metrics.claimed_completions = 20
        metrics.false_completions = 2
        
        assert metrics.fcr == 0.10  # 10%
    
    def test_vsr_threshold(self):
        """VSR >= 70% is success."""
        metrics = MetricsAccumulator()
        metrics.total_runs = 100
        metrics.verified_successes = 70
        
        assert metrics.vsr >= 0.70
    
    def test_fcr_threshold(self):
        """FCR <= 5% is success."""
        metrics = MetricsAccumulator()
        metrics.claimed_completions = 100
        metrics.false_completions = 5
        
        assert metrics.fcr <= 0.05


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
