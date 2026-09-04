"""
test_study011_workload_design.py
=================================

Pins Q-012 (workload design): the STUDY-011 frozen workloads use
reduced-length prompts (<= 2K tokens) to avoid the 429 rate limits
that the full SWE-01 prompt triggered. This test ensures no future
workload addition exceeds the 2K token constraint without an
amendment.
"""

import json
import os
import sys
from pathlib import Path

import pytest

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace = os.path.abspath(os.path.join(base_dir, ".."))
if workspace not in sys.path:
    sys.path.insert(0, workspace)


WORKLOADS_FROZEN = "data/study011_workloads_frozen.json"
WORKLOAD_MANIFEST = "data/study011_workload_manifest.json"
MAX_PROMPT_TOKENS = 2000


def test_workloads_frozen_exists():
    p = Path(workspace) / WORKLOADS_FROZEN
    assert p.exists()


def test_workloads_count_is_20():
    p = Path(workspace) / WORKLOADS_FROZEN
    data = json.load(open(p))
    assert len(data["workloads"]) == 20, (
        f"Workload count drifted from 20 to {len(data['workloads'])}."
    )


def test_every_workload_has_prompt_field():
    p = Path(workspace) / WORKLOADS_FROZEN
    data = json.load(open(p))
    for w in data["workloads"]:
        assert "prompt" in w and w["prompt"], (
            f"Workload {w.get('workload_id')} missing prompt"
        )


def test_every_workload_prompt_within_2k_tokens():
    """Q-012: the STUDY-011 workloads use reduced-length prompts to
    avoid the 429 rate limits of the full SWE-01 prompt. Maximum
    2K tokens (chars/4 approximation)."""
    p = Path(workspace) / WORKLOADS_FROZEN
    data = json.load(open(p))
    over_limit = []
    for w in data["workloads"]:
        approx_tokens = len(w["prompt"]) // 4
        if approx_tokens > MAX_PROMPT_TOKENS:
            over_limit.append(
                (w.get("workload_id"), approx_tokens)
            )
    assert not over_limit, (
        f"Workload prompts exceed 2K tokens: {over_limit}. "
        f"Q-012 resolved this by using reduced-length prompts. "
        f"Any future addition must keep the constraint or document "
        f"a STUDY-011 amendment."
    )


def test_every_workload_has_input_tokens_lte_2000_constraint():
    """Each workload must explicitly carry the input_tokens_lte_2000
    constraint to document the design choice."""
    p = Path(workspace) / WORKLOADS_FROZEN
    data = json.load(open(p))
    missing = [
        w.get("workload_id") for w in data["workloads"]
        if not any(
            "input_tokens_lte_2000" in c
            for c in w.get("constraints", [])
        )
    ]
    assert not missing, (
        f"Workloads missing input_tokens_lte_2000 constraint: {missing}"
    )


def test_workload_manifest_root_hash_unchanged():
    """The 20-workload set's content root_hash must remain pinned.
    Any workload addition/change breaks this and requires a new
    preregistration version."""
    p = Path(workspace) / WORKLOAD_MANIFEST
    data = json.load(open(p))
    sha_list = sorted(w["sha256"] for w in data["workloads"])
    import hashlib
    root = hashlib.sha256("".join(sha_list).encode()).hexdigest()
    assert root == "e823102a4ff09bfca560c95e341aa3eaf7a4003215abd3900749afc64d3e4e06", (
        f"workload set root_hash drifted: {root}"
    )
