from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]

def test_diagnostic_is_three_shadow_pairs_and_not_performance_campaign():
    m=yaml.safe_load((ROOT/'benchmarks/v217_completion_diagnostic.yaml').read_text())
    assert len(m['cases'])==3
    for rel in ('configs/v217-diagnostic-frontier.yaml','configs/v217-diagnostic-jev.yaml'):
        c=yaml.safe_load((ROOT/rel).read_text())
        assert c['runtime']['max_turns']==6
        assert c['runtime']['command_mode']=='verify_only'
    script=(ROOT/'scripts/run_v217_completion_diagnostic.py').read_text()
    assert 'shadow_pairs=3' in script
    assert 'holdout_pairs=0' in script
    assert "'performance_claim':False" in script