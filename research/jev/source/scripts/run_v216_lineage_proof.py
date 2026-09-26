from __future__ import annotations
import base64, json, os, shutil
from pathlib import Path
from jev_engineering.authenticated_benchmark import run_and_seal_authenticated_benchmark
from jev_engineering.public_receipts import Ed25519ReceiptSigner

root=Path(__file__).resolve().parents[1]
out=root/'artifacts'/'v216-lineage-proof'
if out.exists(): shutil.rmtree(out)
out.mkdir(parents=True,exist_ok=True)
raw_b64=os.environ.get('JEV_EVIDENCE_SIGNING_KEY_B64','')
if not raw_b64: raise SystemExit('missing JEV_EVIDENCE_SIGNING_KEY_B64')
try:
    raw=base64.b64decode(raw_b64, validate=True)
except Exception as exc:
    raise SystemExit('invalid JEV_EVIDENCE_SIGNING_KEY_B64') from exc
signer=Ed25519ReceiptSigner.from_private_key_bytes(key_id='jev-v215-runner', raw=raw)
bundle=run_and_seal_authenticated_benchmark(
    manifest_path=root/'benchmarks'/'v216_authenticated_lineage_proof.yaml',
    output_dir=out,
    signer=signer,
    incumbent_condition='qwen-frontier-control',
    candidate_condition='qwen-jev-control',
    repeats=1,
    seed=216,
    shadow_pairs=0,
    experiment_pairs=0,
    holdout_pairs=1,
)
payload=bundle.to_dict()
(out/'evidence.json').write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
print(json.dumps({
    'status':'PASS' if bundle.verify_signatures() else 'FAIL',
    'pairs':1,
    'signed_executions':len(bundle.signed_executions),
    'receipts_verify':bundle.verify_signatures(),
    'live_provider_measurement':bundle.live_provider_measurement,
    'authenticated_live_ab_executed':False,
    'performance_claim':False,
    'truth_boundary':'one-pair proof establishes authenticated paired lineage only; it is not powered performance evidence',
},sort_keys=True))
if not bundle.verify_signatures(): raise SystemExit(3)
