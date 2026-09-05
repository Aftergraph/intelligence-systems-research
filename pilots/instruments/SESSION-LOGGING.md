# SESSION-LOGGING — STUDY-006 Telemetry Schema

**Protocol ID:** `STUDY-006-PREREG-001`  
**Measure:** Event-Level Telemetry (behavioral proxies)  
**Platform:** Track B.4 platform-in-the-loop logging

---

## 1. Schema Overview

Every session generates a JSONL (JSON Lines) log file with one event per line.

**Filename:** `{participant_id}_{arm}_{session_date}.jsonl`

---

## 2. Event Schema

Each event is a JSON object with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `participant_id` | string | Anonymized participant identifier (e.g., `P001`) |
| `arm` | string | Study arm: `chat_only`, `gui`, `hybrid`, `mission` |
| `task_id` | integer | Task number: 1, 2, 3, or 4 |
| `event_type` | string | Event category (see Table 1) |
| `timestamp` | string | ISO 8601 UTC timestamp (e.g., `2026-09-15T14:23:45Z`) |
| `payload_hash` | string | SHA-256 hash of event payload for integrity verification |

---

## 3. Event Types

| Event Type | Description | Payload Contents |
|------------|-------------|------------------|
| `session_start` | Participant begins session | arm, task_order, session_version |
| `task_start` | Participant begins task | task_id, task_description_hash |
| `agent_action` | Agent proposes/ executes an action | action_type, target_resource, predicted_impact |
| `user_approval` | User approves agent action | action_id, approval_latency_ms |
| `user_intervention` | User intervenes/modifies action | intervention_type, before_state, after_state |
| `task_complete` | Task completes (success/failure) | outcome, time_to_outcome_ms, errors_detected |
| `session_end` | Session concludes | total_time_ms, events_logged_count |
| `system_alert` | Platform-level system warning | alert_type, severity, triggered_rule |

---

## 4. Integrity & Anonymity

**Payload Hashing:**
- Each event's payload is hashed with SHA-256
- Hash is stored in the event for integrity verification
- Original payloads are stored separately (encrypted) for debugging

**Participant Anonymity:**
- `participant_id` is assigned at screening; no PII in logs
- Logs are stored on encrypted drive
- Logs are deleted after study closure (90 days post-session)

---

## 5. Derivable Metrics

From raw events, compute:

| Metric | Formula |
|--------|---------|
| **Intervention Count** | Count of `user_intervention` events per task |
| **Takeover Latency** | `timestamp(user_intervention) - timestamp(agent_alert)` |
| **Time to Verified Outcome (TVO)** | `timestamp(task_complete) - timestamp(task_start)` |
| **Approval Rate** | `user_approval` / (`user_approval` + `user_intervention`) |

---

## 6. Implementation Notes

**JSONL Format:**
```json
{"participant_id": "P001", "arm": "mission", "task_id": 1, "event_type": "task_start", "timestamp": "2026-09-15T14:23:45Z", "payload_hash": "abc123..."}
{"participant_id": "P001", "arm": "mission", "task_id": 1, "event_type": "agent_action", "timestamp": "2026-09-15T14:23:52Z", "payload_hash": "def456..."}
```

**Platform Integration:**
- Logged via Track B.4 telemetry service
- Events are streamed to local buffer (no network transmission)
- Buffer flushed to disk after session_end

---

*Schema version: 1.0 — Matches STUDY-006 preregistration (Section 3.1, 3.5)*
