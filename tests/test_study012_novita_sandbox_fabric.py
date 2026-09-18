from experiments.live_benchmark.study012_novita_sandbox_fabric import build_plan,canonical_hash,NOVITA_SDK_VERSION
from experiments.live_benchmark.study012_matrix_plan_v2 import allocation

def test_sandbox_plan_is_deterministic_and_separate():
    rows=allocation()[:12]
    a=build_plan(rows); b=build_plan(rows)
    assert a==b
    assert a["rows_hash"]==canonical_hash(rows)
    assert a["execution_id"]=="study012-recovery-v2-20260918"
    assert len(a["rows"])==12

def test_novita_sdk_version_is_pinned():
    assert NOVITA_SDK_VERSION=="2.1.1"
