from __future__ import annotations

import json
import math
from typing import Any

import httpx

from .jev_client import SystemOneResponse, Usage


class OpenAIDecisionError(RuntimeError):
    """Raised when the OpenAI decision backend cannot produce valid typed answers."""


class OpenAIDecisionBackend:
    """Use an OpenAI frontier model as the typed Jev-style decision plane.

    This preserves the Choice/Score/Noul interface used by DecisionEngine while
    removing the requirement for a separate Jev service. The model is forced to
    call one strict `submit_decisions` function whose schema is synthesized from
    the requested typed questions.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-5.6-sol",
        base_url: str = "https://api.openai.com/v1",
        reasoning_effort: str | None = "high",
        timeout: float = 120.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI API key is required")
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.reasoning_effort = reasoning_effort
        self._client = httpx.Client(
            timeout=timeout,
            transport=transport,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "aftergraph-jev-engineering/1.6",
            },
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "OpenAIDecisionBackend":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @staticmethod
    def _confidence_schema() -> dict[str, Any]:
        return {"type": "number", "minimum": 0.0, "maximum": 1.0}

    @classmethod
    def _answer_schema(cls, key: str, question: dict[str, Any]) -> dict[str, Any]:
        kind = str(question.get("type") or "").casefold()
        if kind == "noul":
            return {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["noul"]},
                    "noul": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "confidence": cls._confidence_schema(),
                },
                "required": ["type", "noul", "confidence"],
                "additionalProperties": False,
            }
        if kind == "choice":
            criteria = question.get("criteria") or {}
            if isinstance(criteria, dict):
                options = [str(x) for x in criteria]
            else:
                options = [str(x) for x in criteria]
            if not options:
                raise OpenAIDecisionError(f"Choice question {key!r} has no criteria")
            return {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["choice"]},
                    "choice": {"type": "string", "enum": options},
                    "confidence": cls._confidence_schema(),
                },
                "required": ["type", "choice", "confidence"],
                "additionalProperties": False,
            }
        if kind == "score":
            criteria = question.get("criteria") or []
            score_schema: dict[str, Any] = {"type": "number"}
            if isinstance(criteria, list) and criteria:
                score_schema.update({"minimum": 0.0, "maximum": float(len(criteria) - 1)})
            return {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["score"]},
                    "score": score_schema,
                    "confidence": cls._confidence_schema(),
                },
                "required": ["type", "score", "confidence"],
                "additionalProperties": False,
            }
        raise OpenAIDecisionError(f"Unsupported typed decision {kind!r} for {key!r}")

    @classmethod
    def _parameters_schema(cls, questions: dict[str, dict[str, Any]]) -> dict[str, Any]:
        properties = {
            str(key): cls._answer_schema(str(key), question)
            for key, question in questions.items()
        }
        required = list(properties)
        return {
            "type": "object",
            "properties": {
                "answers": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False,
                }
            },
            "required": ["answers"],
            "additionalProperties": False,
        }

    @staticmethod
    def _validate_answers(
        questions: dict[str, dict[str, Any]], answers: dict[str, Any]
    ) -> dict[str, dict[str, Any]]:
        expected = set(questions)
        actual = set(answers)
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            raise OpenAIDecisionError(
                f"Typed decision keys mismatch; missing={missing}, extra={extra}"
            )
        validated: dict[str, dict[str, Any]] = {}
        for key, question in questions.items():
            answer = answers.get(key)
            if not isinstance(answer, dict):
                raise OpenAIDecisionError(f"Answer {key!r} is not an object")
            kind = str(question.get("type") or "").casefold()
            if str(answer.get("type") or "").casefold() != kind:
                raise OpenAIDecisionError(f"Answer {key!r} has wrong type")
            confidence = float(answer.get("confidence", 0.0))
            if not 0.0 <= confidence <= 1.0 or not math.isfinite(confidence):
                raise OpenAIDecisionError(f"Answer {key!r} has invalid confidence")
            if kind == "noul":
                value = float(answer.get("noul"))
                if not 0.0 <= value <= 1.0 or not math.isfinite(value):
                    raise OpenAIDecisionError(f"Answer {key!r} has invalid noul")
            elif kind == "choice":
                criteria = question.get("criteria") or {}
                options = [str(x) for x in criteria]
                choice = str(answer.get("choice") or "")
                if choice not in options:
                    raise OpenAIDecisionError(
                        f"Answer {key!r} choice {choice!r} is outside configured criteria"
                    )
            elif kind == "score":
                value = float(answer.get("score"))
                if not math.isfinite(value):
                    raise OpenAIDecisionError(f"Answer {key!r} has invalid score")
            else:
                raise OpenAIDecisionError(f"Unsupported typed decision {kind!r}")
            validated[key] = dict(answer)
        return validated

    def system_one(
        self,
        *,
        state: Any,
        questions: dict[str, dict[str, Any]],
        model: str | None = None,
    ) -> SystemOneResponse:
        if not questions:
            raise OpenAIDecisionError("At least one typed question is required")
        chosen_model = model or self.model
        parameters = self._parameters_schema(questions)
        body: dict[str, Any] = {
            "model": chosen_model,
            "instructions": (
                "You are the typed decision plane for a governed coding system. "
                "Answer every requested Choice, Score, or Noul exactly once. "
                "Use the supplied state only. Calibrate probabilities conservatively. "
                "Do not propose code or actions; submit only the typed decisions."
            ),
            "input": [
                {
                    "role": "user",
                    "content": json.dumps(
                        {"state": state, "questions": questions},
                        ensure_ascii=False,
                        separators=(",", ":"),
                        default=str,
                    ),
                }
            ],
            "tools": [
                {
                    "type": "function",
                    "name": "submit_decisions",
                    "description": "Submit all requested typed decisions.",
                    "parameters": parameters,
                    "strict": True,
                }
            ],
            "tool_choice": {"type": "function", "name": "submit_decisions"},
            "parallel_tool_calls": False,
            "store": False,
        }
        if self.reasoning_effort:
            body["reasoning"] = {"effort": self.reasoning_effort}

        response = self._client.post(f"{self.base_url}/responses", json=body)
        try:
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise OpenAIDecisionError(f"OpenAI decision request failed: {exc}") from exc
        if not isinstance(payload, dict):
            raise OpenAIDecisionError("OpenAI returned a non-object response")

        selected_call: dict[str, Any] | None = None
        for item in payload.get("output") or []:
            if (
                isinstance(item, dict)
                and item.get("type") == "function_call"
                and item.get("name") == "submit_decisions"
            ):
                selected_call = item
                break
        if selected_call is None:
            raise OpenAIDecisionError("OpenAI did not call submit_decisions")
        raw_arguments = selected_call.get("arguments") or "{}"
        try:
            arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
        except json.JSONDecodeError as exc:
            raise OpenAIDecisionError("submit_decisions emitted invalid JSON") from exc
        if not isinstance(arguments, dict) or not isinstance(arguments.get("answers"), dict):
            raise OpenAIDecisionError("submit_decisions is missing answers")
        answers = self._validate_answers(questions, dict(arguments["answers"]))

        usage_payload = payload.get("usage") or {}
        usage = Usage(
            input_tokens=int(usage_payload.get("input_tokens", 0) or 0),
            output_tokens=int(usage_payload.get("output_tokens", 0) or 0),
        )
        request_ids: list[str] = []
        for header in ("x-request-id", "x-trace-id", "request-id"):
            value = response.headers.get(header)
            if value and value not in request_ids:
                request_ids.append(value)
        payload_id = payload.get("id")
        if payload_id and str(payload_id) not in request_ids:
            request_ids.append(str(payload_id))
        return SystemOneResponse(
            model=str(payload.get("model") or chosen_model),
            answers=answers,
            usage=usage,
            raw=payload,
            request_ids=tuple(request_ids),
        )