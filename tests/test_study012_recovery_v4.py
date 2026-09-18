from experiments.live_benchmark.study012_recovery_v4_readiness import TARGETS

def test_v4_readiness_is_exactly_nine_calls():
    assert len(TARGETS)==3
    assert TARGETS[0][0]=="ollama-local"
    assert TARGETS[0][1]=="qwen3.6:latest"
    assert TARGETS[1][1]=="nvidia/nemotron-3-ultra-550b-a55b"
    assert TARGETS[2][1]=="nvidia/nemotron-3-super-120b-a12b"
    assert all(x[3] for x in TARGETS)
