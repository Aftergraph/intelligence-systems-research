#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, json, os, subprocess, sys
from pathlib import Path
from jev_engineering.public_receipts import Ed25519ReceiptSigner
from jev_engineering.sealed_secrets import generate_runner_seal_keypair, public_key_b64_from_private, load_bundle, unseal_values
from jev_engineering.provider_health import run_provider_smoke


def private_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists(): path.write_bytes(data)
    try: os.chmod(path,0o600)
    except OSError: pass


def bootstrap(args):
    seal=Path(args.seal_private); signing=Path(args.signing_private)
    if not seal.exists():
        private,_=generate_runner_seal_keypair(); private_write(seal,private)
    if not signing.exists(): Ed25519ReceiptSigner.generate(key_id=args.signing_key_id).write_private_key(signing)
    public_b64=public_key_b64_from_private(seal.read_bytes())
    signer=Ed25519ReceiptSigner.load_private_key(key_id=args.signing_key_id,path=signing)
    print(json.dumps({"status":"READY","seal_public_key_der_b64":public_b64,"seal_key_fingerprint_sha256":__import__('hashlib').sha256(base64.b64decode(public_b64)).hexdigest(),"signing_key_id":args.signing_key_id,"signing_public_key_b64":base64.b64encode(signer.public_key_bytes()).decode()}))


def exec_with_env(args):
    values=unseal_values(load_bundle(args.bundle),Path(args.seal_private).read_bytes())
    env=os.environ.copy(); env.update(values)
    env["JEV_EVIDENCE_SIGNING_KEY_B64"]=base64.b64encode(Path(args.signing_private).read_bytes()).decode("ascii")
    if not args.command:
        raise SystemExit("exec requires command after --")
    proc=subprocess.run(args.command,env=env)
    raise SystemExit(proc.returncode)


def smoke(args):
    values=unseal_values(load_bundle(args.bundle),Path(args.seal_private).read_bytes())
    report=run_provider_smoke(typesafe_api_key=values['TYPESAFE_API_KEY'],dialagram_api_key=values['DIALAGRAM_API_KEY'])
    signer=Ed25519ReceiptSigner.load_private_key(key_id=args.signing_key_id,path=args.signing_private)
    payload={"schema":"aftergraph.v215-authenticated-provider-smoke/1.0","providers":["typesafe","dialagram"],"ok":report["ok"],"request_lineage_present":report["request_lineage_present"],"authenticated_https":report["authenticated_https"],"checks":report["checks"],"live_provider_smoke_executed":True,"performance_claim":False}
    receipt=signer.sign(payload)
    out={"receipt":receipt.to_dict() if hasattr(receipt,'to_dict') else {"payload":receipt.payload,"key_id":receipt.key_id,"algorithm":receipt.algorithm,"payload_sha256":receipt.payload_sha256,"signature_b64":receipt.signature_b64},"signing_public_key_b64":base64.b64encode(signer.public_key_bytes()).decode()}
    Path(args.evidence_out).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding='utf-8')
    print(json.dumps({"status":"PASS" if report['ok'] else "FAIL","request_lineage_present":report['request_lineage_present'],"authenticated_https":report['authenticated_https'],"evidence_out":args.evidence_out}))
    if not report['ok']: raise SystemExit(4)

p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True)
for name,fn in [('bootstrap',bootstrap),('smoke',smoke),('exec',exec_with_env)]:
    q=sub.add_parser(name); q.set_defaults(fn=fn); q.add_argument('--seal-private',required=True); q.add_argument('--signing-private',required=True); q.add_argument('--signing-key-id',default='jev-v215-runner')
    if name in {'smoke','exec'}: q.add_argument('--bundle',required=True)
    if name=='smoke': q.add_argument('--evidence-out',required=True)
    if name=='exec': q.add_argument('command',nargs=argparse.REMAINDER)
a=p.parse_args(); a.fn(a)