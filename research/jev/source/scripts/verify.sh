#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
python -m pytest -q
python -m compileall -q src tests
python scripts/verify_no_secrets.py .
python -m jev_engineering.cli demo
python -m jev_engineering.cli doctor --config configs/jev-one.example.yaml
python -m jev_engineering.cli models --config configs/jev-one.example.yaml --frontier-only >/dev/null
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git diff --check
fi
python -m jev_engineering.cli intelligence-plan --config configs/hermes-dialagram-qwen-vif.yaml --capability generation
python -m jev_engineering.cli intelligence-plan --config configs/intelligence-fabric-demo.yaml --capability control --required-vsr 0.80 >/dev/null
python -m jev_engineering.cli intelligence-plan --config configs/intelligence-fabric-demo.yaml --capability control --required-vsr 0.90 >/dev/null
python -m jev_engineering.cli intelligence-plan --config configs/intelligence-fabric-demo.yaml --capability control --required-vsr 0.98 >/dev/null
python -m jev_engineering.cli verification-plan --config configs/verified-intelligence-v14-demo.yaml >/dev/null
python -m jev_engineering.cli learning-demo >/dev/null
python -m jev_engineering.cli effect-demo >/dev/null
python -m jev_engineering.cli distributed-demo >/dev/null

python -m jev_engineering.cli transport-demo >/dev/null
python -m jev_engineering.cli v2-demo >/dev/null
python -m jev_engineering.cli v23-demo >/dev/null
python -m jev_engineering.cli v25-demo >/dev/null

python -m jev_engineering.cli v26-demo >/dev/null
