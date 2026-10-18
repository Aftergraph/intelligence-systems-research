from __future__ import annotations

from jev_engineering.decisions import DecisionEngine
from jev_engineering.testing import ScriptedDecisionBackend
from jev_engineering.types import CandidateFile, ModelProfile


def test_scope_ranks_files_from_score_answers() -> None:
    backend = ScriptedDecisionBackend(
        [
            {
                "answers": {
                    "f0": {"type": "score", "score": 3.8, "confidence": 0.9},
                    "f1": {"type": "score", "score": 0.2, "confidence": 0.9},
                }
            }
        ]
    )
    engine = DecisionEngine(backend)
    ranked = engine.scope(
        task="fix auth bug",
        candidates=[
            CandidateFile("src/auth.py", "def login(): ..."),
            CandidateFile("README.md", "docs"),
        ],
        top_k=1,
    )
    assert [item.path for item in ranked] == ["src/auth.py"]


def test_choose_model_only_sees_frontier_models_when_frontier_required() -> None:
    backend = ScriptedDecisionBackend(
        [
            {
                "answers": {
                    "model": {
                        "type": "choice",
                        "choice": "astra",
                        "confidence": 0.75,
                        "probabilities": {"astra": 0.75},
                    }
                }
            }
        ]
    )
    engine = DecisionEngine(backend)
    models = [
        ModelProfile(alias="astra", provider="openai", model="gpt-5.6-sol", tier="frontier"),
        ModelProfile(alias="cheap", provider="mock", model="tiny", tier="fast"),
    ]
    chosen = engine.choose_model("hard coding task", models, frontier_required=True)
    assert chosen.alias == "astra"
    request = backend.requests[0]
    assert set(request["questions"]["model"]["criteria"]) == {"astra"}


def test_safety_gate_blocks_high_destructive_probability() -> None:
    backend = ScriptedDecisionBackend(
        [
            {
                "answers": {
                    "destructive": {"type": "noul", "noul": 0.95},
                    "needs_human": {"type": "noul", "noul": 0.88},
                }
            }
        ]
    )
    engine = DecisionEngine(backend)
    decision = engine.safe_to_run(
        task="refactor",
        command="rm -rf build",
        policy={"destructive_block_threshold": 0.8, "human_threshold": 0.7},
    )
    assert decision.action == "block"


def test_done_requires_fresh_evidence_and_judgeability() -> None:
    backend = ScriptedDecisionBackend(
        [
            {
                "answers": {
                    "done": {"type": "noul", "noul": 0.93},
                    "judgeable": {"type": "noul", "noul": 0.96},
                }
            }
        ]
    )
    engine = DecisionEngine(backend)
    verdict = engine.done(
        task="fix tests",
        evidence={"verification_exit_code": 0, "verification_output": "12 passed", "evidence_fresh": True},
    )
    assert verdict.verified is True


def test_retention_uses_drop_truncate_keep_without_lossy_summary() -> None:
    backend = ScriptedDecisionBackend(
        [
            {
                "answers": {
                    "r0": {"type": "score", "score": 0.1, "confidence": 0.9},
                    "r1": {"type": "score", "score": 1.1, "confidence": 0.9},
                    "r2": {"type": "score", "score": 1.9, "confidence": 0.9},
                }
            }
        ]
    )
    engine = DecisionEngine(backend)
    decisions = engine.retention(
        task="debug",
        outputs=["old noise", "long-ish maybe", "important exact evidence"],
    )
    assert decisions == ["drop", "truncate", "keep"]
