from __future__ import annotations
import base64, json, os, shutil
from pathlib import Path
from jev_engineering.authenticated_benchmark import run_and_seal_authenticated_benchmark
from jev_engineering.campaign_readiness import CompletionReadinessPolicy, analyze_completion_readiness, recommend_turn_budgets
from jev_engineering.public_receipts import Ed25519ReceiptSigner, Ed25519ReceiptVerifier

root=Path(__file__).resolve().parents[1]
out=root/'artifacts'/'v217-completion-diagnostic'
if out.exists(): shutil.rmtree(out)
out.mkdir(parents=True,exist_ok=True)
raw_b64=os.environ.get('JEV_EVIDENCE_SIGNING_KEY_B64','')
if not raw_b64: raise SystemExit('missing JEV_EVIDENCE_SIGNING_KEY_B64')
raw=base64.b64decode(raw_b64,validate=True)
signer=Ed25519ReceiptSigner.from_private_key_bytes(key_id='jev-v215-runner',raw=raw)
bundle=run_and_seal_authenticated_benchmark(
    manifest_path=root/'benchmarks'/'v217_completion_diagnostic.yaml',
    output_dir=out,
    signer=signer,
    incumbent_condition='qwen-frontier-control',
    candidate_condition='qwen-jev-control',
    repeats=1,
    shadow_pairs=3,
    experiment_pairs=0,
    holdout_pairs=0,
    seed=217,
)
verifier=Ed25519ReceiptVerifier({signer.key_id:signer.public_key_bytes()})
verified=bundle.verify(verifier)
readiness=analyze_completion_readiness(
    bundle.execution.records,
    incumbent_condition='qwen-frontier-control',
    candidate_condition='qwen-jev-control',
    policy=CompletionReadinessPolicy(min_pilot_pairs=3),
)
payload={
    'status':'PASS' if verified else 'FAIL',
    'pairs':3,
    'signed_executions':len(bundle.signed_executions),
    'receipts_verify':verified,
    'live_provider_measurement':bundle.live_provider_measurement,
    'completion_readiness':readiness.to_dict(),
    'turn_budget_recommendations':[
        {name:getattr(item,name) for name in item.__slots__}
        for item in recommend_turn_budgets(readiness,current_max_turns=6)
    ],
    'performance_claim':False,
    'truth_boundary':'three-pair shadow diagnostic measures completion readiness only; it cannot support performance promotion',
}
(out/'completion-readiness.json').write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
print(json.dumps(payload,sort_keys=True))
if not verified: raise SystemExit(3)