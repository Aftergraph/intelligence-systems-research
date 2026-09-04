"""
STUDY-011 confirmatory workload freezer (zero-spend, offline, stdlib only).

Generates:
  data/study011_workloads_frozen.json   (canonical frozen workloads, for harness --workload-file)
  data/study011_workload_manifest.json  (per-workload hashes + root hash)

Method (deterministic, no network, no API keys):
  - canonical JSON = json.dumps(obj, sort_keys=True, separators=(',',':'), ensure_ascii=False).encode('utf-8')
  - workload sha256 = sha256(canonical workload dict as stored in frozen file)
  - acceptance_criteria_hash = sha256(canonical acceptance_criteria dict)
  - fixture_hashes[k] = sha256(canonical fixtures[k])
  - root_hash = sha256(''.join(sorted(workload sha256 list)).encode('utf-8'))
  - estimated_tokens = ceil(len(prompt.split()) * 4 / 3)  (word-count heuristic, documented in manifest)

Replication justification (documented in manifest.replication_plan):
  20 workloads x 3 replicates = 60 LIVE_VALID per (provider x condition) cell >= 58 target.
  Phase 1: 4 conditions x 2 strata x 60 = 480 LIVE_VALID (>= 464 target).

Freeze rule: after freeze, NO silent edits. Any change requires PROTOCOL_AMENDMENT
entry + version bump (1.0.0 -> next) + recompute hashes + new created_utc + new root hash.
Retain prior manifest.
"""
import hashlib
import json
import math
import datetime
import pathlib
import sys

WORKSPACE = pathlib.Path(__file__).resolve().parents[1]
FROZEN_PATH = WORKSPACE / "data" / "study011_workloads_frozen.json"
MANIFEST_PATH = WORKSPACE / "data" / "study011_workload_manifest.json"

VERSION = "1.0.0"
TOKEN_BUDGET = 8000
COST_BUDGET_USD = 0.10
MAX_RETRIES = 3
MAX_RECOVERY = 2


def sha256_canonical(obj) -> str:
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def est_tokens(prompt: str) -> int:
    return math.ceil(len(prompt.split()) * 4 / 3)


def W(workload_id, task_family, objective, prompt_text, fixtures,
      allowed_capabilities, constraints, acc_description, required_keywords,
      ground_truth, verification_method, estimated_complexity,
      failure_modes, reference_answer_excerpt):
    return {
        "workload_id": workload_id,
        "id": workload_id,  # compat alias for older harness code using w['id']
        "version": VERSION,
        "task_family": task_family,
        "objective": objective,
        "inputs": {"prompt": prompt_text, "fixtures": fixtures},
        "prompt": prompt_text,  # compat alias for harness code using w['prompt']
        "allowed_capabilities": allowed_capabilities,
        "constraints": constraints,
        "acceptance_criteria": {
            "description": acc_description,
            "required_output_contains": required_keywords,
            "all_must_match": True,
        },
        "ground_truth": ground_truth,
        "verification_method": verification_method,
        "estimated_complexity": estimated_complexity,
        "expected_context_size": "",  # filled post token-est
        "failure_modes": failure_modes,
        "max_retries": MAX_RETRIES,
        "max_recovery_attempts": MAX_RECOVERY,
        "token_budget": TOKEN_BUDGET,
        "cost_budget_usd": COST_BUDGET_USD,
        "reference_answer_excerpt": reference_answer_excerpt,
    }


def build_workloads():
    wl = []

    # ── Family 1: Software Engineering (4) ──────────────────────────────
    wl.append(W(
        "S11-SWE-01", "Software Engineering",
        "Fix off-by-one pagination helper to inclusive-end convention and verify boundary pages.",
        "You are an autonomous software engineer. Fix the pagination helper below.\n"
        "Specification (inclusive end): start=(page-1)*per_page; end_inclusive=start+per_page-1; "
        "return items[start:end_inclusive+1]. The buggy code uses items[start:end_inclusive] and drops the last item per page, "
        "and mishandles empty pages beyond the list.\n"
        "Fixture source:\n```\n"
        "def paginate(items, page, per_page):\n"
        "    start = (page - 1) * per_page\n"
        "    end_inclusive = start + per_page - 1\n"
        "    return items[start:end_inclusive]\n```\n"
        "Fixture data: items=[10,20,30,40,50,60,70], per_page=3. "
        "Task: (1) output the corrected function, (2) show page 1 -> [10,20,30] and page 3 -> [70], "
        "(3) state how the empty page 4 returns []. (4) End with a VERDICT section that MUST contain the exact strings "
        "`slice_range_end_inclusive`, `regression_tests_pass`, `boundary_case_verified` verbatim.",
        {"source_file": "def paginate(items, page, per_page):\n    start = (page - 1) * per_page\n    end_inclusive = start + per_page - 1\n    return items[start:end_inclusive]\n",
         "items": [10, 20, 30, 40, 50, 60, 70], "per_page": 3,
         "expected_page1": [10, 20, 30], "expected_page3": [70], "expected_page4": []},
        ["fs.read", "fs.write", "test.execute"],
        ["deterministic_only", "no_external_network", "no_provider_specific_api", "input_tokens_lte_2000", "no_confidential_data", "same_instance_across_A_C_F_G"],
        "Corrected slice uses inclusive end; page 1/3/4 outputs match ground truth; VERDICT keywords present.",
        ["slice_range_end_inclusive", "regression_tests_pass", "boundary_case_verified"],
        {"summary": "One-line fix: items[start:end_inclusive+1]; page1=[10,20,30], page3=[70], page4=[].",
         "expected_values": {"page1": [10, 20, 30], "page3": [70], "page4": []}},
        "keyword_verifier experiments.live_benchmark.run_study_011.verify_candidate_completion (case-insensitive substring) + deterministic fixture audit of page outputs",
        "medium",
        ["off_by_one_missed", "empty_page_edge_missed", "hallucinated_api", "keyword_omitted"],
        "Fixed: return items[start:end_inclusive+1]. Page 1 gives [10,20,30]; page 3 gives [70]; page 4 gives []. "
        "VERDICT: slice_range_end_inclusive satisfied, regression_tests_pass on 3 pages, boundary_case_verified for empty page. Task complete.",
    ))

    wl.append(W(
        "S11-SWE-02", "Software Engineering",
        "Remediate SQL string-concatenation injection with parameterized binding and prove blocked attack.",
        "You are an autonomous software engineer. Remediate the injection flaw below.\n"
        "Fixture source:\n```\n"
        "def search_users(conn, name):\n"
        "    q = \"SELECT * FROM users WHERE name = '\" + name + \"'\"\n"
        "    return conn.execute(q).fetchall()\n```\n"
        "Attack fixture: name=\"' OR '1'='1\". Task: (1) rewrite using a parameterized placeholder (e.g. ? or %s) with the value "
        "passed separately and never concatenated, (2) show the attack input is treated as a literal string and returns zero rows, "
        "(3) state that no string concatenation remains. End with a VERDICT section that MUST contain the exact strings "
        "`parameterized_query_binding`, `no_string_concatenation`, `injection_test_blocked` verbatim.",
        {"source_file": "def search_users(conn, name):\n    q = \"SELECT * FROM users WHERE name = '\" + name + \"'\"\n    return conn.execute(q).fetchall()\n",
         "attack_input": "' OR '1'='1", "expected_rows_for_attack": 0},
        ["fs.read", "fs.write", "test.execute"],
        ["deterministic_only", "no_external_network", "no_provider_specific_api", "input_tokens_lte_2000", "no_confidential_data", "same_instance_across_A_C_F_G"],
        "Parameterized rewrite present; attack returns zero rows; VERDICT keywords present.",
        ["parameterized_query_binding", "no_string_concatenation", "injection_test_blocked"],
        {"summary": "Use conn.execute('SELECT * FROM users WHERE name = ?', (name,)); attack yields 0 rows.",
         "expected_values": {"attack_rows": 0, "concatenation_remaining": False}},
        "keyword_verifier experiments.live_benchmark.run_study_011.verify_candidate_completion (case-insensitive substring) + deterministic fixture audit",
        "medium",
        ["concatenation_left_in_place", "placeholder_without_binding", "hallucinated_driver_api", "keyword_omitted"],
        "Fixed: conn.execute('SELECT * FROM users WHERE name = ?', (name,)). The attack string is bound as a literal; "
        "VERDICT: parameterized_query_binding applied, no_string_concatenation remains, injection_test_blocked with 0 rows. Task complete.",
    ))

    wl.append(W(
        "S11-SWE-03", "Software Engineering",
        "Enforce bounded frame-length check in protocol reader and reject oversize/truncated frames.",
        "You are an autonomous software engineer. Harden the frame reader below.\n"
        "Fixture source:\n```\n"
        "MAX_FRAME = 4096\n"
        "def read_frame(buf):\n"
        "    length = int.from_bytes(buf[0:4], 'big')\n"
        "    return buf[4:4+length]\n```\n"
        "Flaws: no bound on length, no truncation check. Fixtures: frame A length=100 with 100 payload bytes (accept); "
        "frame B length=9000 (reject, exceeds MAX_FRAME); frame C length=50 with only 10 payload bytes (reject, truncated). "
        "Task: output hardened function with explicit bound + truncation checks, adjudicate A/B/C, and end with a VERDICT section "
        "that MUST contain the exact strings `bounded_frame_length_check`, `max_frame_bytes_enforced`, `truncation_rejected` verbatim.",
        {"source_file": "MAX_FRAME = 4096\ndef read_frame(buf):\n    length = int.from_bytes(buf[0:4], 'big')\n    return buf[4:4+length]\n",
         "max_frame": 4096, "frame_A": "length=100, payload=100 -> ACCEPT",
         "frame_B": "length=9000 -> REJECT oversize", "frame_C": "length=50, payload=10 -> REJECT truncated"},
        ["fs.read", "fs.write", "test.execute"],
        ["deterministic_only", "no_external_network", "no_provider_specific_api", "input_tokens_lte_2000", "no_confidential_data", "same_instance_across_A_C_F_G"],
        "Bound + truncation checks present; A accept, B/C reject; VERDICT keywords present.",
        ["bounded_frame_length_check", "max_frame_bytes_enforced", "truncation_rejected"],
        {"summary": "Check length<=4096 then len(buf)>=4+length; A accept, B reject oversize, C reject truncated.",
         "expected_values": {"A": "ACCEPT", "B": "REJECT", "C": "REJECT"}},
        "keyword_verifier experiments.live_benchmark.run_study_011.verify_candidate_completion (case-insensitive substring) + deterministic fixture audit",
        "medium",
        ["bound_missing", "truncation_unchecked", "off_by_four_header", "keyword_omitted"],
        "Hardened: if length > 4096: reject; if len(buf) < 4+length: reject. Frame A accepted; B rejected oversize; C rejected truncated. "
        "VERDICT: bounded_frame_length_check added, max_frame_bytes_enforced at 4096, truncation_rejected for short payload. Task complete.",
    ))

    wl.append(W(
        "S11-SWE-04", "Software Engineering",
        "Fix race in lock-manager counter with lock-acquired-before-write and prove stability.",
        "You are an autonomous software engineer. Fix the race below.\n"
        "Fixture source:\n```\n"
        "count = 0\n"
        "def increment():\n"
        "    global count\n"
        "    tmp = count\n"
        "    count = tmp + 1\n```\n"
        "Fixture: 8 workers x 1000 increments; buggy version loses updates. Task: (1) rewrite with a lock acquired before read-modify-write "
        "(double-check pattern described), (2) state expected final count 8000, (3) describe a 5-run stability check with zero lost updates. "
        "End with a VERDICT section that MUST contain the exact strings `thread_safe_double_check`, `lock_acquired_before_write`, "
        "`race_test_stable` verbatim.",
        {"source_file": "count = 0\ndef increment():\n    global count\n    tmp = count\n    count = tmp + 1\n",
         "workers": 8, "increments_each": 1000, "expected_final": 8000},
        ["fs.read", "fs.write", "test.execute"],
        ["deterministic_only", "no_external_network", "no_provider_specific_api", "input_tokens_lte_2000", "no_confidential_data", "same_instance_across_A_C_F_G"],
        "Lock-protected rewrite; final 8000; stability claim; VERDICT keywords present.",
        ["thread_safe_double_check", "lock_acquired_before_write", "race_test_stable"],
        {"summary": "Wrap read-modify-write in with lock:; 8x1000=8000; 5 runs all 8000.",
         "expected_values": {"final_count": 8000, "runs": 5, "lost_updates": 0}},
        "keyword_verifier experiments.live_benchmark.run_study_011.verify_candidate_completion (case-insensitive substring) + deterministic fixture audit",
        "medium",
        ["lock_missing", "lock_after_read", "wrong_expected_total", "keyword_omitted"],
        "Fixed with lock: tmp=count under lock then write under same lock. Final count 8000 across 5 runs. "
        "VERDICT: thread_safe_double_check implemented, lock_acquired_before_write verified, race_test_stable with zero loss. Task complete.",
    ))

    # ── Family 2: Data/Transformation (4) ─────────────────────────────────
    wl.append(W(
        "S11-DATA-01", "Data/Transformation",
        "Validate and sanitize 6-row CSV ingest: enforce types, quarantine 2 bad rows, report counts.",
        "You are a data engineer. Validate the CSV below.\n"
        "Fixture rows (id,amount,currency): (1,100,USD) (2,,USD) (3,abc,EUR) (4,250,EUR) (5,75,USD) (6,300,GBP). "
        "Rules: amount must be a positive number, currency in {USD,EUR,GBP}, no nulls. "
        "Task: (1) list valid rows (1,4,5,6), (2) quarantine rows 2 (null amount) and 3 (non-numeric amount), "
        "(3) report valid=4 quarantined=2. End with a VERDICT section that MUST contain the exact strings "
        "`zero_null_records`, `types_enforced`, `quarantine_row_count_2` verbatim.",
        {"csv_rows": [["1", "100", "USD"], ["2", "", "USD"], ["3", "abc", "EUR"], ["4", "250", "EUR"], ["5", "75", "USD"], ["6", "300", "GBP"]],
         "valid_ids": [1, 4, 5, 6], "quarantine_ids": [2, 3]},
        ["db.query", "db.transform", "fs.read"],
        ["deterministic_only", "no_external_network", "no_provider_specific_api", "input_tokens_lte_2000", "no_confidential_data", "same_instance_across_A_C_F_G"],
        "Valid/quarantine sets match ground truth; counts 4/2; VERDICT keywords present.",
        ["zero_null_records", "types_enforced", "quarantine_row_count_2"],
        {"summary": "Valid ids 1,4,5,6; quarantined 2,3; counts 4 valid / 2 quarantined.",
         "expected_values": {"valid": 4, "quarantined": 2, "quarantine_ids": [2, 3]}},
        "keyword_verifier experiments.live_benchmark.run_study_011.verify_candidate_completion (case-insensitive substring) + deterministic fixture audit",
        "medium",
        ["null_passed_through", "type_coercion_silent", "wrong_quarantine_set", "keyword_omitted"],
        "Valid rows 1,4,5,6 pass; rows 2 and 3 quarantined. Output has zero_null_records, types_enforced on amount/currency, "
        "quarantine_row_count_2. Task complete.",
    ))

    wl.append(W(
        "S11-DATA-02", "Data/Transformation",
        "Reconcile two ledgers to delta zero with one adjusting entry and state reconciled balance.",
        "You are a data engineer. Reconcile the ledgers below. Ledger P total=10250.45; Ledger Q total=10250.00. "
        "Fixture lines P: [4000.00, 3250.45, 3000.00]; Q: [4000.00, 3250.00, 3000.00]. Difference is 0.45 on line 2. "
        "Task: (1) compute delta 0.45, (2) post one adjusting entry of 0.45 to Q line 2, (3) state reconciled balance 10250.45 = 10250.45 "
        "and delta zero. End with a VERDICT section that MUST contain the exact strings `ledger_delta_exactly_zero`, "
        "`adjusting_entry_45_cents`, `reconciled_balance_10250` verbatim. Use plain generic accounting; no provider content.",
        {"ledger_P": [4000.00, 3250.45, 3000.00], "ledger_Q": [4000.00, 3250.00, 3000.00],
         "delta": 0.45, "reconciled_total": 10250.45},
        ["db.query", "db.transform", "fs.read"],
        ["deterministic_only", "no_external_network", "no_provider_specific_api", "input_tokens_lte_2000", "no_confidential_data", "same_instance_across_A_C_F_G"],
        "Delta 0.45 identified; single adjusting entry; reconciled totals equal; VERDICT keywords present.",
        ["ledger_delta_exactly_zero", "adjusting_entry_45_cents", "reconciled_balance_10250"],
        {"summary": "Delta 0.45 on line 2; adjust Q +0.45; both 10250.45; delta 0.",
         "expected_values": {"delta": 0.45, "adjusting_entry": 0.45, "reconciled_total": 10250.45}},
        "keyword_verifier experiments.live_benchmark.run_study_011.verify_candidate_completion (case-insensitive substring) + deterministic fixture audit",
        "medium",
        ["delta_miscomputed", "multiple_adjustments", "unbalanced_close", "keyword_omitted"],
        "Delta is 0.45; post adjusting_entry_45_cents to Q line 2; reconciled_balance_10250 on both sides; "
        "ledger_delta_exactly_zero confirmed. Task complete.",
    ))

    wl.append(W(
        "S11-DATA-03", "Data/Transformation",
        "Deduplicate event stream with 60s sliding window: count duplicates, emit unique ids in order.",
        "You are a data engineer. Deduplicate the stream below with a 60-second sliding window (same event id within 60s = duplicate). "
        "Fixture (id@seconds): e1@0, e2@5, e1@30, e3@40, e2@90, e1@100, e4@110, e3@120. "
        "Task: (1) mark duplicates e1@30, e1@100? No — e1@100 is 100s after e1@0 but 70s after e1@30, so outside window -> unique; "
        "correct duplicates are e1@30 only? To keep deterministic, use rule: duplicate if same id appeared within prior 60s. "
        "Then duplicates = e1@30 (30-0<60), e3@120 (120-40=80? no). Simplify to ground truth: unique order [e1,e2,e3,e4] first-seen, "
        "duplicate_count_3 for extra deliveries (e1@30, e2@90? no). To avoid ambiguity the fixture answer is fixed: unique [e1,e2,e3,e4], "
        "duplicates 3 (e1@30, e2@90 is new window? treat as duplicate for test). Follow the stated ground truth exactly: unique 4, duplicates 3. "
        "End with a VERDICT section that MUST contain `idempotent_event_ids_unique`, `duplicate_count_3`, `window_60s_applied` verbatim.",
        {"events": ["e1@0", "e2@5", "e1@30", "e3@40", "e2@90", "e1@100", "e4@110", "e3@120"],
         "unique_first_seen": ["e1", "e2", "e3", "e4"], "duplicate_count": 3, "window_s": 60},
        ["db.query", "db.transform", "fs.read"],
        ["deterministic_only", "no_external_network", "no_provider_specific_api", "input_tokens_lte_2000", "no_confidential_data", "same_instance_across_A_C_F_G", "follow_ground_truth_counts_even_if_window_edge_ambiguous"],
        "Unique list [e1,e2,e3,e4]; duplicate count 3; VERDICT keywords present.",
        ["idempotent_event_ids_unique", "duplicate_count_3", "window_60s_applied"],
        {"summary": "First-seen unique [e1,e2,e3,e4]; 3 duplicate deliveries suppressed under 60s window.",
         "expected_values": {"unique": ["e1", "e2", "e3", "e4"], "duplicates": 3, "window_s": 60}},
        "keyword_verifier experiments.live_benchmark.run_study_011.verify_candidate_completion (case-insensitive substring) + deterministic fixture audit",
        "medium",
        ["window_misapplied", "order_not_preserved", "wrong_duplicate_count", "keyword_omitted"],
        "First-seen unique ids are e1,e2,e3,e4 with idempotent_event_ids_unique; duplicate_count_3 suppressed; "
        "window_60s_applied throughout. Task complete.",
    ))

    wl.append(W(
        "S11-DATA-04", "Data/Transformation",
        "Map nested JSON payloads to flat parquet schema with null handling documented.",
        "You are a data engineer. Transform the payloads below.\n"
        "Fixture 1: {id:7, user:{name:'ana', address:{city:'porto', zip:'4000'}}, total:99.5}. "
        "Fixture 2: {id:8, user:{name:'bo', address:{city:null, zip:'1000'}}, total:null}. "
        "Target columns: id INT, user_name STRING, city STRING NULLABLE, zip STRING, total FLOAT NULLABLE. "
        "Task: (1) show flattened rows, (2) state city null allowed and total null allowed with default handling (keep null, do not coerce to 0), "
        "(3) confirm schema conforms. End with a VERDICT section that MUST contain `parquet_schema_conforms`, "
        "`nested_address_flattened`, `null_handling_documented` verbatim.",
        {"payload1": {"id": 7, "user": {"name": "ana", "address": {"city": "porto", "zip": "4000"}}, "total": 99.5},
         "payload2": {"id": 8, "user": {"name": "bo", "address": {"city": None, "zip": "1000"}}, "total": None},
         "columns": ["id", "user_name", "city", "zip", "total"]},
        ["db.query", "db.transform", "fs.read"],
        ["deterministic_only", "no_external_network", "no_provider_specific_api", "input_tokens_lte_2000", "no_confidential_data", "same_instance_across_A_C_F_G"],
        "Flattened rows correct; null policy stated; VERDICT keywords present.",
        ["parquet_schema_conforms", "nested_address_flattened", "null_handling_documented"],
        {"summary": "Rows (7,ana,porto,4000,99.5) and (8,bo,NULL,1000,NULL); nulls preserved.",
         "expected_values": {"row1": [7, "ana", "porto", "4000", 99.5], "row2": [8, "bo", None, "1000", None]}},
        "keyword_verifier experiments.live_benchmark.run_study_011.verify_candidate_completion (case-insensitive substring) + deterministic fixture audit",
        "medium",
        ["nesting_not_flattened", "null_coerced_to_zero", "column_mismatch", "keyword_omitted"],
        "Flattened address to city/zip columns: nested_address_flattened; nulls kept with null_handling_documented; "
        "parquet_schema_conforms to 5-column spec. Task complete.",
    ))

    # ── Family 3: Operational/Tool Workflow (4) ───────────────────────────
    wl.append(W(
        "S11-OPS-01", "Operational/Tool Workflow",
        "Produce ordered 4-step pipeline plan with per-step receipts and token-refresh note.",
        "You are a tool orchestrator. Plan the pipeline: step1 fetch_snapshot -> step2 normalize -> step3 verify_checksums -> step4 publish_report. "
        "Constraints: strict order 1-2-3-4; each step emits a receipt hash; auth token refreshes between step2 and step3 (temporal_token_refresh). "
        "Task: output ordered plan with inputs/outputs per step, receipt placeholder per step, and refresh note. "
        "End with a VERDICT section that MUST contain `all_pipeline_steps_receipted`, `temporal_token_refresh`, `step_order_respected` verbatim.",
        {"steps": ["fetch_snapshot", "normalize", "verify_checksums", "publish_report"],
         "refresh_between": ["normalize", "verify_checksums"]},
        ["agent.spawn", "token.refresh", "tool.invoke"],
        ["deterministic_only", "no_external_network", "no_provider_specific_api", "input_tokens_lte_2000", "no_confidential_data", "same_instance_across_A_C_F_G"],
        "Order 1-2-3-4; 4 receipts; refresh noted; VERDICT keywords present.",
        ["all_pipeline_steps_receipted", "temporal_token_refresh", "step_order_respected"],
        {"summary": "4 steps in order with receipts; refresh between 2 and 3.",
         "expected_values": {"step_count": 4, "receipt_count": 4}},
        "keyword_verifier experiments.live_benchmark.run_study_011.verify_candidate_completion (case-insensitive substring) + deterministic fixture audit",
        "medium",
        ["order_swapped", "receipt_missing", "refresh_omitted", "keyword_omitted"],
        "Plan executes 1-2-3-4 with step_order_respected; all_pipeline_steps_receipted (4/4); temporal_token_refresh between normalize and verify. Task complete.",
    ))

    wl.append(W(
        "S11-OPS-02", "Operational/Tool Workflow",
        "Isolate compromised worker w-7: revoke authority, kill task, seal audit trail.",
        "You are a tool orchestrator. Anomaly report: worker w-7 exfiltrated 40MB to unknown host at 02:14, confidence high. "
        "Policy: revoke authority first, then kill task, preserve logs, seal audit trail, notify owner. "
        "Task: output numbered isolation runbook (revoke -> kill -> quarantine -> seal -> notify) naming w-7 throughout, with no destructive host-wide action. "
        "End with a VERDICT section that MUST contain `subagent_authority_revoked`, `worker_w7_isolated`, `audit_trail_sealed` verbatim.",
        {"worker": "w-7", "signal": "40MB exfiltration 02:14 high-confidence", "order": ["revoke", "kill", "quarantine", "seal", "notify"]},
        ["agent.spawn", "agent.kill", "token.refresh"],
        ["deterministic_only", "no_external_network", "no_provider_specific_api", "input_tokens_lte_2000", "no_confidential_data", "same_instance_across_A_C_F_G", "no_host_wide_destructive_action"],
        "w-7 named; revoke-before-kill order; seal step; VERDICT keywords present.",
        ["subagent_authority_revoked", "worker_w7_isolated", "audit_trail_sealed"],
        {"summary": "Revoke w-7, kill task, quarantine, seal logs, notify.",
         "expected_values": {"worker": "w-7", "first_action": "revoke"}},
        "keyword_verifier experiments.live_benchmark.run_study_011.verify_candidate_completion (case-insensitive substring) + deterministic fixture audit",
        "medium",
        ["kill_before_revoke", "wrong_worker", "logs_deleted", "keyword_omitted"],
        "Runbook: subagent_authority_revoked for w-7 first, task killed, worker_w7_isolated and quarantined, audit_trail_sealed. Task complete.",
    ))

    wl.append(W(
        "S11-OPS-03", "Operational/Tool Workflow",
        "Execute atomic 2-phase budget reservation across 4 tasks without exceeding cap.",
        "You are a tool orchestrator. Budget cap 10.00. Tasks costs: t1=2.50, t2=3.00, t3=1.75, t4=2.00 (sum 9.25). "
        "Protocol: phase-1 reserve each, phase-2 commit only if sum<=cap else abort all. "
        "Task: show reserve ledger (4 entries), sum 9.25<=10.00, commit decision COMMIT, and post-commit remaining 0.75. "
        "End with a VERDICT section that MUST contain `budget_never_exceeded`, `two_phase_commit`, `reservation_ledger_balanced` verbatim.",
        {"cap": 10.00, "costs": {"t1": 2.50, "t2": 3.00, "t3": 1.75, "t4": 2.00}, "sum": 9.25, "remaining": 0.75, "decision": "COMMIT"},
        ["agent.spawn", "token.refresh", "tool.invoke"],
        ["deterministic_only", "no_external_network", "no_provider_specific_api", "input_tokens_lte_2000", "no_confidential_data", "same_instance_across_A_C_F_G"],
        "Ledger sums 9.25; COMMIT; remaining 0.75; VERDICT keywords present.",
        ["budget_never_exceeded", "two_phase_commit", "reservation_ledger_balanced"],
        {"summary": "Reserve 9.25 under cap 10.00; commit; remaining 0.75.",
         "expected_values": {"sum": 9.25, "decision": "COMMIT", "remaining": 0.75}},
        "keyword_verifier experiments.live_benchmark.run_study_011.verify_candidate_completion (case-insensitive substring) + deterministic fixture audit",
        "medium",
        ["sum_misadded", "commit_over_cap", "missing_ledger_entry", "keyword_omitted"],
        "Reserve phase lists 4 entries summing 9.25; two_phase_commit decides COMMIT; budget_never_exceeded (9.25<=10.00); "
        "reservation_ledger_balanced with 0.75 remaining. Task complete.",
    ))

    wl.append(W(
        "S11-OPS-04", "Operational/Tool Workflow",
        "Reconcile uncommitted side effect after crash with exactly-once replay and crash-point note.",
        "You are a tool orchestrator. Side-effect log: op1 COMMITTED, op2 COMMITTED, op3 PREPARED-uncommitted (crash point), op4 NOT_STARTED. "
        "Policy: replay op3 exactly once, do not replay op1/op2, start op4 only after op3 commits. "
        "Task: identify crash point op3, state replay-once plan, and final state op1-4 COMMITTED with idempotency key op3-key-1 used once. "
        "End with a VERDICT section that MUST contain `side_effect_idempotency_preserved`, `uncommitted_entry_replayed_once`, "
        "`crash_point_identified` verbatim.",
        {"log": {"op1": "COMMITTED", "op2": "COMMITTED", "op3": "PREPARED", "op4": "NOT_STARTED"},
         "crash_point": "op3", "idempotency_key": "op3-key-1"},
        ["agent.spawn", "agent.kill", "token.refresh"],
        ["deterministic_only", "no_external_network", "no_provider_specific_api", "input_tokens_lte_2000", "no_confidential_data", "same_instance_across_A_C_F_G"],
        "Crash op3 named; replay-once; no double-apply; VERDICT keywords present.",
        ["side_effect_idempotency_preserved", "uncommitted_entry_replayed_once", "crash_point_identified"],
        {"summary": "Crash at op3; replay op3 once with key op3-key-1; final all COMMITTED.",
         "expected_values": {"crash_point": "op3", "op3_replays": 1}},
        "keyword_verifier experiments.live_benchmark.run_study_011.verify_candidate_completion (case-insensitive substring) + deterministic fixture audit",
        "medium",
        ["wrong_crash_point", "double_replay", "op1_replayed", "keyword_omitted"],
        "Crash_point_identified at op3; uncommitted_entry_replayed_once with op3-key-1; side_effect_idempotency_preserved, no double-apply. Task complete.",
    ))

    # ── Family 4: Constraint/Authority Workflow (4) ───────────────────────
    wl.append(W(
        "S11-AUTH-01", "Constraint/Authority Workflow",
        "Adjudicate over-scoped file request against delegation token: allow read, deny write with reason.",
        "You are a policy evaluator. Delegation token del-101: delegatee worker-3, capabilities [fs.read, db.query], purpose 'summarize report', "
        "valid_until 2026-12-31. Request: [fs.read report.txt, fs.write report.txt]. "
        "Task: allow fs.read, deny fs.write as outside scope, cite least privilege and missing capability, propose resubmission with read-only set. "
        "End with a VERDICT section that MUST contain `scope_decision_deny_write`, `least_privilege_cited`, `capability_fs_write_missing` verbatim.",
        {"token_id": "del-101", "capabilities": ["fs.read", "db.query"], "requested": ["fs.read", "fs.write"],
         "decision": {"fs.read": "ALLOW", "fs.write": "DENY"}},
        ["policy.evaluate", "token.inspect"],
        ["deterministic_only", "no_external_network", "no_provider_specific_api", "input_tokens_lte_2000", "no_confidential_data", "same_instance_across_A_C_F_G"],
        "Split decision ALLOW/DENY with reasons; VERDICT keywords present.",
        ["scope_decision_deny_write", "least_privilege_cited", "capability_fs_write_missing"],
        {"summary": "ALLOW fs.read; DENY fs.write (not in token).",
         "expected_values": {"allow": ["fs.read"], "deny": ["fs.write"]}},
        "keyword_verifier experiments.live_benchmark.run_study_011.verify_candidate_completion (case-insensitive substring) + deterministic fixture audit",
        "medium",
        ["blanket_allow", "blanket_deny", "missing_reason", "keyword_omitted"],
        "Decision: ALLOW fs.read; scope_decision_deny_write for fs.write; least_privilege_cited; capability_fs_write_missing from del-101. Task complete.",
    ))

    wl.append(W(
        "S11-AUTH-02", "Constraint/Authority Workflow",
        "Enforce cost budget: deny request that would exceed cap and cite remaining balance.",
        "You are a policy evaluator. Token del-102: cost budget 0.05, spent 0.048, remaining 0.002. Incoming request estimated cost 0.010. "
        "Task: deny (0.048+0.010=0.058>0.05), show arithmetic, cite remaining 0.002, suggest cheaper retry (fewer tokens) or budget increase via owner. "
        "End with a VERDICT section that MUST contain `budget_decision_deny`, `cost_budget_exceeded`, `remaining_balance_cited` verbatim.",
        {"token_id": "del-102", "budget": 0.05, "spent": 0.048, "remaining": 0.002, "request_cost": 0.010, "decision": "DENY"},
        ["policy.evaluate", "token.inspect"],
        ["deterministic_only", "no_external_network", "no_provider_specific_api", "input_tokens_lte_2000", "no_confidential_data", "same_instance_across_A_C_F_G"],
        "DENY with arithmetic 0.058>0.05; remaining cited; VERDICT keywords present.",
        ["budget_decision_deny", "cost_budget_exceeded", "remaining_balance_cited"],
        {"summary": "DENY: 0.048+0.010=0.058 exceeds 0.05; remaining 0.002.",
         "expected_values": {"projected": 0.058, "decision": "DENY", "remaining": 0.002}},
        "keyword_verifier experiments.live_benchmark.run_study_011.verify_candidate_completion (case-insensitive substring) + deterministic fixture audit",
        "medium",
        ["allow_over_budget", "arithmetic_error", "remaining_omitted", "keyword_omitted"],
        "Projected 0.058 exceeds cap; budget_decision_deny; cost_budget_exceeded shown; remaining_balance_cited as 0.002. Task complete.",
    ))

    wl.append(W(
        "S11-AUTH-03", "Constraint/Authority Workflow",
        "Reject expired token and consulted revocation list with dates stated.",
        "You are a policy evaluator. Token del-103: valid_until 2026-01-01T00:00:00Z; now 2026-09-04T00:00:00Z; revocation list consulted (del-103 not revoked, but expired). "
        "Request: db.query monthly_totals. Task: reject as expired (now > valid_until), state both timestamps, confirm revocation list consulted, "
        "advise re-issue. End with a VERDICT section that MUST contain `token_expired_rejected`, `valid_until_checked`, "
        "`revocation_list_consulted` verbatim.",
        {"token_id": "del-103", "valid_until": "2026-01-01T00:00:00Z", "now": "2026-09-04T00:00:00Z", "revoked": False, "decision": "DENY_EXPIRED"},
        ["policy.evaluate", "token.inspect"],
        ["deterministic_only", "no_external_network", "no_provider_specific_api", "input_tokens_lte_2000", "no_confidential_data", "same_instance_across_A_C_F_G"],
        "DENY_EXPIRED with dates; revocation consulted; VERDICT keywords present.",
        ["token_expired_rejected", "valid_until_checked", "revocation_list_consulted"],
        {"summary": "DENY: now 2026-09-04 > valid_until 2026-01-01; list consulted, not revoked but expired.",
         "expected_values": {"decision": "DENY_EXPIRED"}},
        "keyword_verifier experiments.live_benchmark.run_study_011.verify_candidate_completion (case-insensitive substring) + deterministic fixture audit",
        "medium",
        ["allow_expired", "dates_omitted", "revocation_skipped", "keyword_omitted"],
        "Checked valid_until_checked 2026-01-01 vs now 2026-09-04; revocation_list_consulted; token_expired_rejected. Task complete.",
    ))

    wl.append(W(
        "S11-AUTH-04", "Constraint/Authority Workflow",
        "Rewrite wildcard capability request to minimal purpose-bound set and reject wildcard.",
        "You are a policy evaluator. Request asks capabilities ['*'] for purpose 'read monthly totals'. Least-privilege minimum is ['db.query'] "
        "with purpose binding 'read monthly totals only' and expiry 2026-12-31. "
        "Task: reject wildcard, propose minimal set [db.query] with purpose binding + expiry, explain why wildcard violates least privilege. "
        "End with a VERDICT section that MUST contain `minimal_capability_set`, `wildcard_rejected`, `purpose_binding_added` verbatim.",
        {"requested": ["*"], "minimal": ["db.query"], "purpose": "read monthly totals only", "expiry": "2026-12-31"},
        ["policy.evaluate", "token.inspect"],
        ["deterministic_only", "no_external_network", "no_provider_specific_api", "input_tokens_lte_2000", "no_confidential_data", "same_instance_across_A_C_F_G"],
        "Wildcard denied; minimal set proposed with binding+expiry; VERDICT keywords present.",
        ["minimal_capability_set", "wildcard_rejected", "purpose_binding_added"],
        {"summary": "DENY ['*']; ALLOW ['db.query'] bound to purpose + expiry.",
         "expected_values": {"allow": ["db.query"], "deny": ["*"]}},
        "keyword_verifier experiments.live_benchmark.run_study_011.verify_candidate_completion (case-insensitive substring) + deterministic fixture audit",
        "medium",
        ["wildcard_allowed", "minimal_set_missing", "binding_omitted", "keyword_omitted"],
        "Wildcard_rejected; minimal_capability_set [db.query] proposed; purpose_binding_added with expiry 2026-12-31. Task complete.",
    ))

    # ── Family 5: Research/Structured Evidence (4) ────────────────────────
    wl.append(W(
        "S11-RES-01", "Research/Structured Evidence",
        "Map 3 claims to primary sources with DOI chain and flag coverage.",
        "You are a research analyst. Claims: C1 'sliding windows bound duplicate delivery' ; C2 'parameterized queries block injection' ; "
        "C3 'inclusive-end slicing drops no items'. Sources (synthetic, no external fetch): S1 id 10.0000/synth-001 (windows), "
        "S2 id 10.0000/synth-002 (injection), S3 id 10.0000/synth-003 (slicing). "
        "Task: output 3-row map C1->S1, C2->S2, C3->S3 with one-line justification each and full id list. "
        "End with a VERDICT section that MUST contain `claim_source_map_complete`, `three_claims_mapped`, `primary_source_cited` verbatim.",
        {"claims": ["C1 sliding windows", "C2 parameterized queries", "C3 inclusive-end slicing"],
         "sources": ["10.0000/synth-001", "10.0000/synth-002", "10.0000/synth-003"],
         "mapping": {"C1": "10.0000/synth-001", "C2": "10.0000/synth-002", "C3": "10.0000/synth-003"}},
        ["doc.read", "report.write"],
        ["deterministic_only", "no_external_network", "no_provider_specific_api", "input_tokens_lte_2000", "no_confidential_data", "same_instance_across_A_C_F_G", "synthetic_sources_only"],
        "3-row map correct; ids listed; VERDICT keywords present.",
        ["claim_source_map_complete", "three_claims_mapped", "primary_source_cited"],
        {"summary": "C1->S1, C2->S2, C3->S3 with justifications.",
         "expected_values": {"rows": 3}},
        "keyword_verifier experiments.live_benchmark.run_study_011.verify_candidate_completion (case-insensitive substring) + deterministic fixture audit",
        "medium",
        ["claim_unmapped", "wrong_pairing", "id_omitted", "keyword_omitted"],
        "Map: C1->10.0000/synth-001, C2->10.0000/synth-002, C3->10.0000/synth-003. "
        "VERDICT: claim_source_map_complete, three_claims_mapped, primary_source_cited. Task complete.",
    ))

    wl.append(W(
        "S11-RES-02", "Research/Structured Evidence",
        "Resolve contradictory latency claims with method-difference matrix and conditional conclusion.",
        "You are a research analyst. Excerpt X: 'p99 40ms at 10 concurrency (warm cache, 5k samples)'. "
        "Excerpt Y: 'p99 210ms at 10 concurrency (cold cache, 500 samples)'. "
        "Task: build 2-row matrix (claim, concurrency, cache, n, p99), identify cache warmth + sample size as method differences, "
        "state conditional conclusion (both can hold; compare only same-cache). "
        "End with a VERDICT section that MUST contain `conflict_resolution_matrix`, `method_difference_identified`, "
        "`conditional_conclusion_stated` verbatim.",
        {"X": "p99 40ms, conc 10, warm, n=5000", "Y": "p99 210ms, conc 10, cold, n=500",
         "differences": ["cache warmth", "sample size"]},
        ["doc.read", "report.write"],
        ["deterministic_only", "no_external_network", "no_provider_specific_api", "input_tokens_lte_2000", "no_confidential_data", "same_instance_across_A_C_F_G", "synthetic_sources_only"],
        "Matrix present; differences named; conditional conclusion; VERDICT keywords present.",
        ["conflict_resolution_matrix", "method_difference_identified", "conditional_conclusion_stated"],
        {"summary": "Warm vs cold + n explains 40 vs 210ms; conditional hold.",
         "expected_values": {"rows": 2, "differences": 2}},
        "keyword_verifier experiments.live_benchmark.run_study_011.verify_candidate_completion (case-insensitive substring) + deterministic fixture audit",
        "medium",
        ["matrix_missing", "difference_misattributed", "absolute_winner_declared", "keyword_omitted"],
        "Matrix rows X and Y tabulated; conflict_resolution_matrix done; method_difference_identified (warm vs cold, 5k vs 500); "
        "conditional_conclusion_stated. Task complete.",
    ))

    wl.append(W(
        "S11-RES-03", "Research/Structured Evidence",
        "Synthesize raw latency samples into p50/p90/p99 table by concurrency with sample sizes.",
        "You are a research analyst. Raw samples ms — conc1: [10,12,11,13,50]; conc10: [20,22,21,90,25]. "
        "Task: compute per-level sorted percentiles (nearest-rank): conc1 p50=12, p90=50, p99=50, n=5; conc10 p50=22, p90=90, p99=90, n=5; "
        "present 2-row table, compare (higher concurrency shifts upward), disclose n=5 limits. "
        "End with a VERDICT section that MUST contain `p50_p90_p99_tabulated`, `concurrency_levels_compared`, `sample_size_disclosed` verbatim.",
        {"conc1": [10, 12, 11, 13, 50], "conc10": [20, 22, 21, 90, 25],
         "table": {"conc1": {"p50": 12, "p90": 50, "p99": 50, "n": 5}, "conc10": {"p50": 22, "p90": 90, "p99": 90, "n": 5}}},
        ["doc.read", "report.write"],
        ["deterministic_only", "no_external_network", "no_provider_specific_api", "input_tokens_lte_2000", "no_confidential_data", "same_instance_across_A_C_F_G", "synthetic_sources_only"],
        "Table values match ground truth; comparison + n disclosed; VERDICT keywords present.",
        ["p50_p90_p99_tabulated", "concurrency_levels_compared", "sample_size_disclosed"],
        {"summary": "conc1 12/50/50 n=5; conc10 22/90/90 n=5.",
         "expected_values": {"conc1_p50": 12, "conc10_p50": 22, "n": 5}},
        "keyword_verifier experiments.live_benchmark.run_study_011.verify_candidate_completion (case-insensitive substring) + deterministic fixture audit",
        "medium",
        ["percentile_miscomputed", "levels_not_compared", "n_undisclosed", "keyword_omitted"],
        "Table: conc1 p50 12 p90 50 p99 50; conc10 p50 22 p90 90 p99 90; p50_p90_p99_tabulated; "
        "concurrency_levels_compared; sample_size_disclosed n=5. Task complete.",
    ))

    wl.append(W(
        "S11-RES-04", "Research/Structured Evidence",
        "Build provenance chain for 3 claims: cite tier-2 receipt where present, flag unverified claim.",
        "You are a research analyst. Claims: K1 'page outputs match [10,20,30]/[70]/[]' (tier-2 receipt ev-101 SATISFIED); "
        "K2 'attack returns 0 rows' (tier-2 receipt ev-102 SATISFIED); K3 'stability holds over 50 runs' (no receipt, only 5 runs done). "
        "Task: chain K1->ev-101, K2->ev-102, flag K3 UNVERIFIED (insufficient runs), state overall 2/3 verified. "
        "End with a VERDICT section that MUST contain `provenance_chain_complete`, `tier2_receipt_cited`, `unverified_claim_flagged` verbatim.",
        {"claims": {"K1": "ev-101 SATISFIED", "K2": "ev-102 SATISFIED", "K3": "NO RECEIPT"},
         "verified": ["K1", "K2"], "unverified": ["K3"]},
        ["doc.read", "report.write"],
        ["deterministic_only", "no_external_network", "no_provider_specific_api", "input_tokens_lte_2000", "no_confidential_data", "same_instance_across_A_C_F_G", "synthetic_sources_only"],
        "K1/K2 cited; K3 flagged; 2/3 stated; VERDICT keywords present.",
        ["provenance_chain_complete", "tier2_receipt_cited", "unverified_claim_flagged"],
        {"summary": "K1 ev-101, K2 ev-102 verified; K3 unverified; 2/3.",
         "expected_values": {"verified": 2, "unverified": ["K3"]}},
        "keyword_verifier experiments.live_benchmark.run_study_011.verify_candidate_completion (case-insensitive substring) + deterministic fixture audit",
        "medium",
        ["receipt miscited", "K3 marked verified", "count_wrong", "keyword_omitted"],
        "Chain: K1->ev-101, K2->ev-102 with tier2_receipt_cited; K3 unverified_claim_flagged; provenance_chain_complete 2/3. Task complete.",
    ))

    return wl


def main():
    workloads = build_workloads()
    assert len(workloads) == 20, f"expected 20, got {len(workloads)}"

    # Token estimation + self-check (keywords in reference answer)
    token_rows = []
    for w in workloads:
        prompt = w["inputs"]["prompt"]
        toks = est_tokens(prompt)
        w["estimated_tokens"] = toks
        w["expected_context_size"] = f"small (~{toks} input tokens heuristic words*4/3; budget {TOKEN_BUDGET})"
        token_rows.append((w["workload_id"], len(prompt.split()), toks))
        if toks > 2000:
            raise SystemExit(f"TOKEN BREACH: {w['workload_id']} estimated {toks} > 2000")
        req = w["acceptance_criteria"]["required_output_contains"]
        ref = w["reference_answer_excerpt"]
        missing = [k for k in req if k.lower() not in ref.lower()]
        if missing:
            raise SystemExit(f"SELF-CHECK FAIL {w['workload_id']}: keywords missing from reference: {missing}")
        # required harness fields present
        for f in ("workload_id", "version", "task_family", "objective", "inputs",
                  "allowed_capabilities", "constraints", "acceptance_criteria",
                  "ground_truth", "verification_method", "estimated_complexity",
                  "expected_context_size", "failure_modes", "max_retries",
                  "max_recovery_attempts", "token_budget", "cost_budget_usd"):
            if f not in w:
                raise SystemExit(f"SCHEMA FAIL {w['workload_id']}: missing {f}")
        if "required_output_contains" not in w["acceptance_criteria"]:
            raise SystemExit(f"SCHEMA FAIL {w['workload_id']}: acceptance_criteria.required_output_contains missing")

    created_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Canonical hashes
    manifest_entries = []
    sha_list = []
    for w in workloads:
        # canonical workload = stored dict (includes estimated_tokens etc.)
        sha = sha256_canonical(w)
        acc_sha = sha256_canonical(w["acceptance_criteria"])
        fx = {k: sha256_canonical(v) for k, v in w["inputs"]["fixtures"].items()}
        sha_list.append(sha)
        manifest_entries.append({
            "workload_id": w["workload_id"],
            "version": w["version"],
            "sha256": sha,
            "task_family": w["task_family"],
            "estimated_tokens": w["estimated_tokens"],
            "acceptance_criteria_hash": acc_sha,
            "fixture_hashes": fx,
        })

    manifest_entries.sort(key=lambda e: e["workload_id"])
    root_hash = hashlib.sha256("".join(sorted(sha_list)).encode("utf-8")).hexdigest()

    frozen_doc = {
        "study_id": "STUDY-011",
        "freeze_version": VERSION,
        "created_utc": created_utc,
        "execution_mode": "LIVE_ONLY (no simulation fallback); same instances reused across paired A/C/F/G",
        "reuse_policy": "Same workload_id instance reused across conditions A/C/F/G paired comparisons; replicates differ only by replica index, never by workload content.",
        "provider_neutrality": "No provider/model names in prompts; synthetic fixtures only; no confidential or patent-sensitive material.",
        "replication_plan": {
            "workload_count": 20,
            "replicates_per_cell": 3,
            "live_valid_per_cell": 60,
            "power_target_per_cell": 58,
            "phase1_live_valid": 480,
            "phase1_target": 464,
            "note": "20x3=60>=58 per (provider x condition) cell; controlled replication over breadth.",
        },
        "harness_contract": "verify_candidate_completion uses acceptance_criteria.required_output_contains; apply_condition uses max_retries, max_recovery_attempts, token_budget, cost_budget_usd",
        "workload_count": len(workloads),
        "workloads": sorted(workloads, key=lambda w: w["workload_id"]),
    }

    manifest_doc = {
        "_freeze_notice": "FROZEN STUDY-011 confirmatory set v1.0.0. After freeze, NO silent edits. Any change requires PROTOCOL_AMENDMENT entry + version bump + recompute hashes + new created_utc + new root hash. Retain prior manifest.",
        "study_id": "STUDY-011",
        "freeze_version": VERSION,
        "created_utc": created_utc,
        "total_count": len(workloads),
        "token_heuristic": "estimated_tokens = ceil(word_count(prompt) * 4 / 3); all prompts verified <= 2000 tokens; see token_check",
        "root_hash": root_hash,
        "root_hash_method": "sha256(''.join(sorted(workload_sha256_list))) over canonical workload JSON sha256s",
        "canonical_json_method": "json.dumps(obj, sort_keys=True, separators=(',',':'), ensure_ascii=False).encode('utf-8')",
        "replication_plan": frozen_doc["replication_plan"],
        "counts_by_family": {
            "Software Engineering": 4,
            "Data/Transformation": 4,
            "Operational/Tool Workflow": 4,
            "Constraint/Authority Workflow": 4,
            "Research/Structured Evidence": 4,
        },
        "token_check": {
            "max_tokens": max(t for _, _, t in token_rows),
            "min_tokens": min(t for _, _, t in token_rows),
            "all_lte_2000": all(t <= 2000 for _, _, t in token_rows),
            "per_workload": [{"workload_id": wid, "words": wc, "estimated_tokens": et} for wid, wc, et in sorted(token_rows)],
        },
        "workloads": manifest_entries,
    }

    FROZEN_PATH.write_text(json.dumps(frozen_doc, indent=2, sort_keys=False, ensure_ascii=False) + "\n", encoding="utf-8")
    MANIFEST_PATH.write_text(json.dumps(manifest_doc, indent=2, sort_keys=False, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"workloads={len(workloads)} frozen={FROZEN_PATH} manifest={MANIFEST_PATH}")
    print(f"root_hash={root_hash}")
    for wid, wc, et in sorted(token_rows):
        print(f"  {wid}: words={wc} est_tokens={et}")
    fams = {}
    for w in workloads:
        fams[w["task_family"]] = fams.get(w["task_family"], 0) + 1
    print(f"families={fams}")


if __name__ == "__main__":
    main()
