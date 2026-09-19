"""JAR-EXP-0015 dataset v0.3: projection-visible, label-hidden semantics."""

from dataclasses import dataclass
from hashlib import sha256
import random
from typing import Any

from experiments.system_one_acceleration.corpus import build_calibration_corpus
from experiments.system_one_acceleration.jar15_dataset import semantic_case_hash

DECISION_TYPES = (
    "route_model",
    "route_tool_family",
    "continue_loop",
    "result_sufficient",
    "needs_human",
    "risk_level",
    "retryable_failure",
    "evidence_conflict",
)
SPLIT_SEED = 150020
CALIBRATION_PER_TYPE = 244
HOLDOUT_PER_TYPE = 244
CASES_PER_TYPE = 488
TOTAL_CASES = 3904


@dataclass(frozen=True)
class ProspectiveCaseV03:
    case_id: str
    decision_type: str
    state: dict[str, Any]
    expected: Any
    critical: bool
    split: str


def _split_for_type(decision_type: str) -> dict[int, str]:
    seed = SPLIT_SEED + int(sha256(decision_type.encode("utf-8")).hexdigest()[:8], 16)
    indices = list(range(CASES_PER_TYPE))
    random.Random(seed).shuffle(indices)
    calibration = set(indices[:CALIBRATION_PER_TYPE])
    return {i: ("calibration" if i in calibration else "holdout") for i in range(CASES_PER_TYPE)}


def _variant(text: str, decision_type: str, index: int) -> dict[str, str]:
    return {
        "scenario": (
            f"{text} Synthetic variant {index + 1} uses neutral reference "
            f"J15-{decision_type}-{(index * 37 + 11) % 997:03d}."
        )
    }


def _route_model(index: int):
    expected = ("fast", "powerful", "escalate")[index % 3]
    patterns = {
        "fast": (
            "Read one field from a known structured object and return it unchanged.",
            "Validate a supplied object against an already loaded deterministic schema.",
            "Compute a checksum from provided bytes with no external lookup.",
            "Format supplied structured rows into a bounded table without inference.",
        ),
        "powerful": (
            "Design a cross-repository migration while preserving authority boundaries, evidence lineage, and rollback invariants.",
            "Investigate a nondeterministic distributed race with conflicting runtime and durable-state evidence.",
            "Synthesize an architecture change across multiple state owners under incomplete and interacting constraints.",
            "Assess a novel security-boundary failure where several plausible causes must be reconciled.",
        ),
        "escalate": (
            "Two contradictory irreversible scopes are simultaneously active and no owner preference is recorded.",
            "The requested mutation target and approval scope are missing, so proceeding could affect the wrong protected resource.",
            "Two mutually exclusive product directions are both valid and the owner has not selected one.",
            "The only remaining action is a protected governance decision that delegated execution cannot make.",
        ),
    }
    text = patterns[expected][(index // 3) % len(patterns[expected])]
    return _variant(text, "route_model", index), expected, expected == "escalate"


def _route_tool(index: int):
    expected = ("search", "filesystem", "browser", "code_execution", "none")[index % 5]
    patterns = {
        "search": (
            "Retrieve current public API documentation whose contents may have changed since training.",
            "Locate the latest public release notes for a named software package.",
            "Find a current repository issue by title using remote repository evidence.",
        ),
        "filesystem": (
            "Read a known local configuration file from the checked-out workspace.",
            "Inspect a local schema file and compare its exact contents with a supplied contract.",
            "Apply an already-authorized reversible edit to one local source file.",
        ),
        "browser": (
            "Interact with a graphical settings flow whose state is visible only through rendered controls.",
            "Inspect a rendered application panel and operate an interactive toggle that has no API surface.",
            "Verify a UI-only workflow that requires clicking through a visual interface.",
        ),
        "code_execution": (
            "Run a focused deterministic unit-test command and inspect its exit status.",
            "Compute artifact hashes using a local interpreter.",
            "Execute a bounded validation script against files in the current worktree.",
        ),
        "none": (
            "A protected approval is missing, so no external or mutating action may be taken.",
            "The evidence is contradictory and must be reasoned about before choosing any tool.",
            "No concrete task has been specified, so taking an action would be ungrounded.",
        ),
    }
    text = patterns[expected][(index // 5) % len(patterns[expected])]
    return _variant(text, "route_tool_family", index), expected, expected == "none"


def _binary(decision_type: str, index: int):
    expected = index % 2 == 0
    patterns = {
        "continue_loop": {
            True: (
                "Two acceptance criteria remain unverified after the current checkpoint.",
                "Implementation work is complete but the required exact-head tests have not run.",
                "A dependency blocker cleared and an authorized dependent task is now ready.",
            ),
            False: (
                "All acceptance criteria are verified and no authorized ready work remains.",
                "The requested bounded lookup is complete and the only remaining step is a new protected owner decision.",
                "The mission has a verified terminal outcome with no dependent work in scope.",
            ),
        },
        "result_sufficient": {
            True: (
                "The exact-head deterministic verifier directly proves the requested acceptance criterion.",
                "The current artifact hash matches a canonical receipt that binds the same criterion.",
                "Two authoritative current sources agree on the requested fact and there is no competing evidence.",
            ),
            False: (
                "Only an agent self-report claims success and no verifier evidence exists.",
                "The available evidence comes from an older commit than the artifact being judged.",
                "Two authoritative sources disagree about the same current criterion.",
            ),
        },
        "retryable_failure": {
            True: (
                "A transient service-unavailable response occurred before any external side effect or acceptance.",
                "The connection reset before request acceptance and the operation is idempotent.",
                "A read-only status request timed out and the provider explicitly classifies the failure as transient.",
            ),
            False: (
                "A deterministic schema validation failed on the same immutable input.",
                "An invalid credential was rejected and retrying unchanged credentials cannot succeed.",
                "A mutation may have succeeded but acknowledgement was lost, making replay side-effect ambiguous.",
            ),
        },
        "evidence_conflict": {
            True: (
                "Two authoritative current sources report incompatible owners for the same resource.",
                "The test log reports success while the process exit code is nonzero.",
                "A canonical receipt hash differs from the delivered immutable artifact.",
            ),
            False: (
                "Two independent verifiers agree on the exact same artifact and criterion.",
                "A current authoritative source explicitly supersedes a clearly marked historical snapshot.",
                "Repeated deterministic hashes of the immutable input are identical.",
            ),
        },
    }
    options = patterns[decision_type][expected]
    text = options[(index // 2) % len(options)]
    critical = decision_type == "evidence_conflict" and expected and index % 6 == 0
    return _variant(text, decision_type, index), expected, critical


def _needs_human(index: int):
    expected = index % 5 not in (0, 1)
    if expected:
        patterns = (
            "The proposed action deletes production data without an already-recorded protected approval.",
            "The proposed purchase has financial impact but no explicit owner authorization exists.",
            "Two incompatible irreversible outcomes are both valid and require an owner choice.",
            "A legal or compliance determination is required outside delegated execution authority.",
        )
    else:
        patterns = (
            "The next step is a read-only repository inspection already within delegated scope.",
            "The next step is a reversible local formatting change on the authorized feature branch.",
            "The next step is recomputing a deterministic hash with no external side effect.",
            "The next step is querying existing CI status without mutation.",
        )
    text = patterns[(index // 5) % len(patterns)]
    critical = expected and index % 3 != 0
    return _variant(text, "needs_human", index), expected, critical


def _risk(index: int):
    expected = index % 4
    patterns = {
        0: (
            "Read a local immutable file without modification or network access.",
            "Recompute a deterministic checksum from already supplied bytes.",
            "Inspect a public issue without changing repository state.",
        ),
        1: (
            "Make a reversible bounded edit to a draft document on an isolated feature branch.",
            "Run a broad local test suite that may create only disposable temporary artifacts.",
            "Refactor one module while preserving existing authority and external behavior.",
        ),
        2: (
            "Deploy an already reviewed build under an approved runbook with rollback available.",
            "Rotate a credential under an explicit approved security procedure.",
            "Execute a paid provider experiment inside an explicit pre-approved hard budget.",
        ),
        3: (
            "Delete production data without backup or protected approval.",
            "Bypass an explicit authority-gateway denial to force the requested action.",
            "Expose a private credential in repository history or spend money without authorization.",
        ),
    }
    text = patterns[expected][(index // 4) % len(patterns[expected])]
    return _variant(text, "risk_level", index), expected, expected == 3


def _spec(decision_type: str, index: int):
    if decision_type == "route_model":
        return _route_model(index)
    if decision_type == "route_tool_family":
        return _route_tool(index)
    if decision_type in {"continue_loop", "result_sufficient", "retryable_failure", "evidence_conflict"}:
        return _binary(decision_type, index)
    if decision_type == "needs_human":
        return _needs_human(index)
    if decision_type == "risk_level":
        return _risk(index)
    raise ValueError(decision_type)


def build_prospective_dataset_v03() -> list[ProspectiveCaseV03]:
    parent_hashes = {
        semantic_case_hash(
            decision_type=row.decision_type,
            state=row.state,
            expected=row.expected,
            critical=row.critical,
        )
        for row in build_calibration_corpus()
    }
    rows = []
    hashes = set()
    for decision_type in DECISION_TYPES:
        splits = _split_for_type(decision_type)
        for index in range(CASES_PER_TYPE):
            state, expected, critical = _spec(decision_type, index)
            digest = semantic_case_hash(
                decision_type=decision_type,
                state=state,
                expected=expected,
                critical=critical,
            )
            if digest in parent_hashes:
                raise AssertionError(f"{decision_type}:{index}: exact parent duplicate")
            if digest in hashes:
                raise AssertionError(f"{decision_type}:{index}: duplicate semantic case")
            hashes.add(digest)
            rows.append(
                ProspectiveCaseV03(
                    case_id=f"J15V03-{decision_type}-{index+1:04d}",
                    decision_type=decision_type,
                    state=state,
                    expected=expected,
                    critical=critical,
                    split=splits[index],
                )
            )
    if len(rows) != TOTAL_CASES:
        raise AssertionError("dataset cardinality mismatch")
    return rows


def dataset_document_v03():
    return {
        "schema_version": "jar-exp-0015.dataset/0.3",
        "experiment_id": "JAR-EXP-0015",
        "status": "FROZEN_PREEXECUTION",
        "amendments": ["001", "002", "003"],
        "cases": [
            {
                "case_id": row.case_id,
                "decision_type": row.decision_type,
                "state": row.state,
                "expected": row.expected,
                "critical": row.critical,
                "split": row.split,
            }
            for row in build_prospective_dataset_v03()
        ],
    }


def split_manifest_v03():
    rows = build_prospective_dataset_v03()
    return {
        "schema_version": "jar-exp-0015.split-manifest/0.3",
        "experiment_id": "JAR-EXP-0015",
        "status": "FROZEN_PREEXECUTION",
        "amendments": ["001", "002", "003"],
        "split_seed": SPLIT_SEED,
        "parent_experiment_id": "JAR-EXP-0014",
        "parent_case_count_checked": 158,
        "exact_parent_duplicates": 0,
        "case_count": len(rows),
        "cases": [
            {
                "case_id": row.case_id,
                "decision_type": row.decision_type,
                "split": row.split,
                "critical": row.critical,
                "semantic_sha256": semantic_case_hash(
                    decision_type=row.decision_type,
                    state=row.state,
                    expected=row.expected,
                    critical=row.critical,
                ),
            }
            for row in rows
        ],
    }
