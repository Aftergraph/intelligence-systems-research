from __future__ import annotations

import math
import re
from typing import Any

from .jev_client import SystemOneResponse, Usage


_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_./-]{1,}")


class LocalDecisionBackend:
    """Explicit offline fallback that mimics Jev's typed *shape*, not Jev's model.

    It exists for local smoke tests and demos. It must never be represented as a
    Jev inference or used as evidence about Jev quality/calibration.
    """

    def system_one(self, *, state: Any, questions: dict[str, dict[str, Any]], model: str | None = None) -> SystemOneResponse:
        answers: dict[str, dict[str, Any]] = {}
        state_text = self._state_text(state)
        for key, q in questions.items():
            kind = str(q.get("type", "")).lower()
            instructions = str(q.get("instructions", ""))
            if kind == "noul":
                answers[key] = {"type": "noul", "noul": self._noul(key, instructions, state_text)}
            elif kind == "choice":
                criteria = q.get("criteria") or {}
                keys = list(criteria) if isinstance(criteria, dict) else [str(x) for x in criteria]
                choice = self._choice(key, instructions, state_text, keys, criteria)
                probs = {k: (0.8 if k == choice else (0.2 / max(1, len(keys) - 1))) for k in keys}
                answers[key] = {"type": "choice", "choice": choice, "confidence": probs.get(choice, 0.0), "probabilities": probs}
            elif kind == "score":
                score = self._score(key, instructions, state_text, q)
                answers[key] = {"type": "score", "score": score, "confidence": 0.55}
            else:
                raise ValueError(f"Unsupported local decision type: {kind!r}")
        return SystemOneResponse(model="local-heuristic-not-jev", answers=answers, usage=Usage(), raw={"offline": True})

    @staticmethod
    def _state_text(state: Any) -> str:
        return str(state).lower()

    def _noul(self, key: str, instructions: str, state: str) -> float:
        key_norm = key.lower()
        words = set(re.findall(r"[a-z_]+", instructions.lower()))
        destructive_words = [
            "rm -rf", "delete", "drop table", "format", "shutdown",
            "push --force", "reset --hard", "credential", ".ssh", ".env",
        ]
        if key_norm == "destructive" or "irreversible" in words or "destructive" in words:
            return 0.98 if any(w in state for w in destructive_words) else 0.04
        if key_norm in {"needs_human", "human", "approval"} or "human" in words:
            return 0.9 if any(
                w in state for w in ["production", "deploy", "credential", "secret", "delete", "payment"]
            ) else 0.08
        if key_norm == "done" or "finished" in words:
            return 0.98 if (
                "verification_exit_code': 0" in state or '"verification_exit_code": 0' in state
            ) else 0.15
        if key_norm == "judgeable" or "judge" in words:
            return 0.95 if "verification_output" in state else 0.5
        if key_norm == "looping" or "repeating" in words:
            return 0.2
        return 0.5

    def _choice(self, key: str, instructions: str, state: str, keys: list[str], criteria: Any) -> str:
        if not keys:
            raise ValueError("choice requires at least one criterion")
        probe = f"{key} {instructions}".lower()
        if "gate" in probe or set(keys) >= {"allow", "confirm", "block"}:
            if any(w in state for w in ["rm -rf /", "drop table", "format ", "push --force"]):
                return "block" if "block" in keys else keys[0]
            if any(w in state for w in ["production", "credential", ".ssh", ".env"]):
                return "confirm" if "confirm" in keys else keys[0]
            return "allow" if "allow" in keys else keys[0]
        # Prefer options whose descriptive text contains frontier/high-risk language.
        if isinstance(criteria, dict):
            ranked = []
            for option in keys:
                desc = f"{option} {criteria.get(option, '')}".lower()
                bonus = 1 if "frontier" in desc else 0
                overlap = len(set(_TOKEN.findall(state)) & set(_TOKEN.findall(desc)))
                ranked.append((bonus, overlap, option))
            ranked.sort(reverse=True)
            return ranked[0][2]
        return keys[0]

    def _score(self, key: str, instructions: str, state: str, q: dict[str, Any]) -> float:
        probe = f"{key} {instructions}".lower()
        # Scope calls embed task and excerpt in state. Estimate relevance lexically.
        task = ""
        excerpt = state
        if "task" in state and "excerpt" in state:
            task = state.split("task", 1)[1].split("excerpt", 1)[0]
            excerpt = state.split("excerpt", 1)[1]
        task_terms = set(_TOKEN.findall(task))
        excerpt_terms = set(_TOKEN.findall(excerpt))
        if task_terms:
            ratio = len(task_terms & excerpt_terms) / max(1, len(task_terms))
            return min(4.0, 0.4 + ratio * 3.6)
        if "retain" in probe or "keep" in probe or "relevance" in probe:
            important = any(x in state for x in ["error", "fail", "test", "evidence", "diff", "traceback"])
            return 1.9 if important else 1.0
        return 1.0
