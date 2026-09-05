# Hard-Case Test Vector Suites (HC1-HC8)
## STUDY-013 G-13a Recruitment Package

**Status:** APPROVED-ACTIVE  
**Owner Approval:** 2026-09-04

These 8 hard-case vector suites define the boundary conditions that any conforming implementation must handle correctly. Each suite contains test inputs and expected outcomes. All implementations must produce fail-closed outcomes for each test.

---

## HC1: Revocation Propagation

**Claim:** Revoked authority never executes post-revoke, cross-runtime.

```json
{
  "suite_id": "HC1",
  "description": "Revocation must propagate immediately across independent runtimes",
  "tests": [
    {
      "id": "HC1-01",
      "name": "Pre-revoke action succeeds, post-revoke action fails",
      "inputs": {
        "initial_delegation": {
          "id": "del-hc1",
          "principal": "urn:p:test",
          "delegate": "urn:d:agent",
          "purpose": "release-production",
          "scope": {"allowed_capabilities": ["mcp://*"]},
          "valid_from": "2026-09-01T00:00:00Z",
          "expires_at": "2026-09-30T00:00:00Z"
        },
        "revocation_timestamp": "2026-09-15T12:00:00Z",
        "actions": [
          {"action_id": "act-001", "capability": "mcp://github/create_pr", "timestamp": "2026-09-15T11:59:00Z"},
          {"action_id": "act-002", "capability": "mcp://github/create_pr", "timestamp": "2026-09-15T12:01:00Z"}
        ]
      },
      "expected_outcome": {
        "act-001": "SUCCESS",
        "act-002": "AUTHORIZATION_FAILED"
      }
    },
    {
      "id": "HC1-02",
      "name": "Cross-runtime revocation propagation",
      "inputs": {
        "runtime_a_delegation": {
          "id": "del-hc1-abc",
          "scope": {"allowed_capabilities": ["mcp://*"]}
        },
        "runtime_b_sync_timestamp": "2026-09-15T12:00:30Z"
      },
      "expected_outcome": {
        "runtime_b_state": "REVOKED",
        "any_post_sync_execution": false
      }
    }
  ]
}
```

---

## HC2: Cross-Organization Delegation

**Claim:** Attenuation conserves budget/permissions across org boundary.

```json
{
  "suite_id": "HC2",
  "description": "Delegation across org boundaries must strictly attenuate",
  "tests": [
    {
      "id": "HC2-01",
      "name": "Budget conservation across org boundary",
      "inputs": {
        "parent_delegation": {
          "id": "del-hc2-parent",
          "budget": {"max_usd": 100.00, "max_tokens": 100000},
          "scope": {"allowed_capabilities": ["mcp://github/*", "mcp://ci/*"]}
        },
        "child_delegation": {
          "id": "del-hc2-child",
          "parent": "del-hc2-parent",
          "budget": {"max_usd": 50.00, "max_tokens": 50000},
          "scope": {"allowed_capabilities": ["mcp://ci/*"]}
        },
        "total_cost_spent": 120.00
      },
      "expected_outcome": {
        "violation_detected": true,
        "violation_type": "BUDGET_EXCEEDED"
      }
    },
    {
      "id": "HC2-02",
      "name": "Permission set must be strict subset",
      "inputs": {
        "parent_scope": {"allowed_capabilities": ["mcp://github/*", "mcp://aws/*"]},
        "child_scope": {"allowed_capabilities": ["mcp://github/*", "mcp://aws/iam:*"]}
      },
      "expected_outcome": {
        "attenuation_valid": false,
        "violation": "CHILD_SCOPE_EXCEEDS_PARENT"
      }
    }
  ]
}
```

---

## HC3: Dynamic Topology Mutation

**Claim:** Org structure changes mid-mission without authority gap.

```json
{
  "suite_id": "HC3",
  "description": "Org topology changes must not break active delegations",
  "tests": [
    {
      "id": "HC3-01",
      "name": "Org restructure during active mission",
      "inputs": {
        "mission_id": "release-production",
        "initial_org": {
          "agents": ["dev-team", "deploy-team"],
          "delegations": {"dev-team": "del-dev", "deploy-team": "del-deploy"}
        },
        "restructure_time": "2026-09-15T14:00:00Z",
        "restructured_org": {
          "agents": ["platform-team"],
          "delegations": {"platform-team": "del-platform"}
        },
        "active_mission_at_restructure": true
      },
      "expected_outcome": {
        "mission_continuity": true,
        "authority_gap_detected": false,
        "handoff_duration_ms": "<=5000"
      }
    }
  ]
}
```

---

## HC4: Budget Conservation

**Claim:** No budget escape via delegation chains.

```json
{
  "suite_id": "HC4",
  "description": "Budget limits must be enforced across all delegation chains",
  "tests": [
    {
      "id": "HC4-01",
      "name": "Aggregate budget across all child delegations",
      "inputs": {
        "root_budget": {"max_usd": 50.00, "max_tokens": 50000},
        "delegation_chain": [
          {"id": "del-1", "budget": {"max_usd": 30.00, "max_tokens": 30000}},
          {"id": "del-2", "budget": {"max_usd": 30.00, "max_tokens": 30000}}
        ],
        "total_budget_allocated": 60.00
      },
      "expected_outcome": {
        "violation_detected": true,
        "violation_type": "CHAIN_BUDGET_EXCEEDS_ROOT"
      }
    },
    {
      "id": "HC4-02",
      "name": "Parallel execution budget accounting",
      "inputs": {
        "mission_budget": {"max_usd": 20.00},
        "parallel_agents": [
          {"agent": "agent-a", "spend": 15.00},
          {"agent": "agent-b", "spend": 10.00}
        ],
        "total_parallel_spend": 25.00
      },
      "expected_outcome": {
        "agent_a_result": "SUCCESS",
        "agent_b_result": "BUDGET_LIMITED",
        "violation_detected": false
      }
    }
  ]
}
```

---

## HC5: Replay/Idempotency

**Claim:** Replayed action_id cannot double-execute or double-count.

```json
{
  "suite_id": "HC5",
  "description": "Action ID replay must be idempotent",
  "tests": [
    {
      "id": "HC5-01",
      "name": "Duplicate action_id rejected",
      "inputs": {
        "original_action": {
          "action_id": "act-001",
          "capability": "mcp://github/create_pr",
          "payload": {"repo": "test", "title": "PR"},
          "execution_result": "SUCCESS"
        },
        "replayed_action": {
          "action_id": "act-001",
          "capability": "mcp://github/create_pr",
          "payload": {"repo": "test", "title": "PR"},
          "replay_timestamp": "2026-09-15T15:00:00Z"
        }
      },
      "expected_outcome": {
        "replay_result": "DEJAVU_DETECTED",
        "second_execution_attempted": false,
        "state_consistent": true
      }
    },
    {
      "id": "HC5-02",
      "name": "Evidence not double-counted on replay",
      "inputs": {
        "original_evidence": {"id": "ev-001", "criterion": "build_passed"},
        "replay_evidence": {"id": "ev-001", "criterion": "build_passed"}
      },
      "expected_outcome": {
        "verified_count": 1,
        "double_counting_detected": false
      }
    }
  ]
}
```

---

## HC6: Stale Authority / Partitions

**Claim:** Partitioned runtimes fail closed on stale authority.

```json
{
  "suite_id": "HC6",
  "description": "Network partition with stale authority must fail closed",
  "tests": [
    {
      "id": "HC6-01",
      "name": "Partitioned runtime cannot consult authority source",
      "inputs": {
        "authority_source": "central-auth-service",
        "partition_start": "2026-09-15T10:00:00Z",
        "partition_end": "2026-09-15T10:30:00Z",
        "delegation_at_partition_start": {
          "id": "del-hc6",
          "expires_at": "2026-09-30T00:00:00Z"
        },
        "revocation_during_partition": "2026-09-15T10:15:00Z",
        "action_during_partition": "2026-09-15T10:20:00Z"
      },
      "expected_outcome": {
        "action_result": "AUTHORIZATION_FAILED",
        "reason": "COULD_NOT_VERIF_FRESH_AUTHORITY",
        "violation_detected": false
      }
    },
    {
      "id": "HC6-02",
      "name": "Cached delegation beyond validity",
      "inputs": {
        "cached_delegation": {
          "id": "del-hc6-2",
          "expires_at": "2026-09-15T10:00:00Z"
        },
        "action_timestamp": "2026-09-15T10:05:00Z",
        "connectivity_to_auth": false
      },
      "expected_outcome": {
        "action_result": "AUTHORIZATION_FAILED",
        "reason": "DELEGATION_EXPIRED"
      }
    }
  ]
}
```

---

## HC7: Evidence Compatibility

**Claim:** L1-L4 bundles verify across independent runtimes.

```json
{
  "suite_id": "HC7",
  "description": "Evidence generated by one runtime must verify in another",
  "tests": [
    {
      "id": "HC7-01",
      "name": "Tier-2 deterministic evidence verification",
      "inputs": {
        "runtime_a": "reference-runtime",
        "runtime_b": "independent-implementation",
        "evidence_bundle": {
          "id": "ev-bundle-hc7",
          "items": [
            {
              "id": "ev-build",
              "tier": "tier_2_deterministic",
              "verifier": {"type": "build_harness", "identifier": "gha"},
              "result": "SATISFIED",
              "artifact_hash": "sha256:abc123..."
            },
            {
              "id": "ev-test",
              "tier": "tier_2_deterministic",
              "verifier": {"type": "test_harness", "identifier": "pytest"},
              "result": "SATISFIED",
              "coverage": 0.85
            }
          ]
        }
      },
      "expected_outcome": {
        "runtime_a_verification": "VERIFIED",
        "runtime_b_verification": "VERIFIED",
        "bundle_compatible": true
      }
    },
    {
      "id": "HC7-02",
      "name": "Tier-3 cryptographic attestation verification",
      "inputs": {
        "evidence_item": {
          "id": "ev-crypto",
          "tier": "tier_3_attestation",
          "verifier": {"type": "cryptographic", "algorithm": "ecdsa-sha256"},
          "signature": "0x...",
          "public_key_id": "pubkey-001",
          "timestamp": "2026-09-15T12:00:00Z"
        }
      },
      "expected_outcome": {
        "verification_result": "VERIFIED",
        "cross_runtime_compatible": true
      }
    }
  ]
}
```

---

## HC8: Human Approval/Takeover Continuity

**Claim:** Takeover survives re-admission, no authority leak.

```json
{
  "suite_id": "HC8",
  "description": "Human takeover must be clean with no authority leakage",
  "tests": [
    {
      "id": "HC8-01",
      "name": "Takeover and return to agent",
      "inputs": {
        "mission_id": "release-production",
        "agent_delegation": {
          "id": "del-hc8-agent",
          "max_delegation_depth": 2
        },
        "human_takeover": {
          "timestamp": "2026-09-15T11:00:00Z",
          "reason": "budget_warning"
        },
        "human_actions": ["approve_deployment"],
        "agent_resumption": {
          "timestamp": "2026-09-15T11:30:00Z"
        }
      },
      "expected_outcome": {
        "human_action_valid": true,
        "agent_resumption_valid": true,
        "authority_leak_detected": false,
        "mission_state": "AUTHORIZED"
      }
    },
    {
      "id": "HC8-02",
      "name": "Delegation depth enforcement after takeover",
      "inputs": {
        "initial_depth": 2,
        "after_takeover_depth": 2
      },
      "expected_outcome": {
        "delegation_depth_preserved": true,
        "depth_reinflation_detected": false
      }
    }
  ]
}
```

---

## Summary: Hard-Case Requirements

| HC | Primary Invariant | Fail-Closed Condition |
|----|-------------------|----------------------|
| HC1 | Revocation propagation | Post-revoke actions return AUTHORIZATION_FAILED |
| HC2 | Cross-org attenuation | Child scope strictly subset of parent; budget conserved |
| HC3 | Topology mutation | No authority gap during org changes |
| HC4 | Budget conservation | Aggregate child budgets ≤ parent |
| HC5 | Replay/idempotency | Duplicate action_id rejected; evidence not double-counted |
| HC6 | Stale authority/partitions | Cannot verify → AUTHORIZATION_FAILED |
| HC7 | Evidence compatibility | Tier-2/Tier-3 bundles verify cross-runtime |
| HC8 | Human takeover | No authority leak; depth preserved |

**All implementations must produce these fail-closed outcomes to achieve HC compliance.**
