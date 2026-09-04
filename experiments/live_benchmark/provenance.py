import hashlib
import json
import os
import time

# ponytail: Provenance recorder for Live Cloud Model Benchmark Runs (Phase EXT-2).
# Generates immutable, cryptographically hashed JSON manifests for every live model run.
# Ensures that provider receipts, token counts, request hashes, and verifier results are verifiable.

class RunProvenanceRecord:
    def __init__(
        self,
        run_id,
        provider,
        model_id,
        condition,
        task_id,
        mission_contract,
        system_prompt,
        request_params=None
    ):
        self.record = {
            "run_id": run_id,
            "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "timestamp_epoch": time.time(),
            "provider": provider,
            "exact_model_id": model_id,
            "api_version": "2026-Q3",
            "condition": condition,  # One of: A, B, C, D, E, F, G
            "task_id": task_id,
            "request_parameters": request_params or {},
            "hashes": {
                "system_prompt_sha256": hashlib.sha256(system_prompt.encode("utf-8")).hexdigest(),
                "mission_contract_sha256": hashlib.sha256(
                    json.dumps(mission_contract, sort_keys=True).encode("utf-8")
                ).hexdigest()
            },
            "raw_model_output": None,
            "tool_calls": [],
            "tool_responses": [],
            "retry_history": [],
            "trajectory_events": [],
            "verifier_output": None,
            "ground_truth": None,
            "latency_ms": 0.0,
            "provider_usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0
            },
            "actual_price_usd": 0.0,
            "invoice_evidence_ref": None,
            "manifest_sha256": None
        }

    def record_execution_result(
        self,
        raw_output,
        tool_calls,
        tool_responses,
        latency_ms,
        input_tokens,
        output_tokens,
        price_usd,
        verifier_output,
        ground_truth,
        trajectory_events=None,
        retry_history=None
    ):
        self.record["raw_model_output"] = raw_output
        self.record["tool_calls"] = tool_calls or []
        self.record["tool_responses"] = tool_responses or []
        self.record["latency_ms"] = round(latency_ms, 2)
        self.record["provider_usage"] = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }
        self.record["actual_price_usd"] = round(price_usd, 6)
        self.record["verifier_output"] = verifier_output
        self.record["ground_truth"] = ground_truth
        self.record["trajectory_events"] = trajectory_events or []
        self.record["retry_history"] = retry_history or []

        # Seal manifest with SHA-256 hash of all fields
        manifest_bytes = json.dumps(self.record, sort_keys=True).encode("utf-8")
        self.record["manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()

    def save(self, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        filename = f"run_{self.record['run_id']}_{self.record['manifest_sha256'][:10]}.json"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.record, f, indent=2)
        return filepath
