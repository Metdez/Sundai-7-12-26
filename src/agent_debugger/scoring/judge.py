"""Optional qualitative rubric judge (§11.4 step 3, open question 32.4).

Judge findings are displayed separately and never alter completion or
safety scores. The evidence packet is bounded and redacted before leaving
the process; the judge receives no hidden facts.
"""
from __future__ import annotations

import json
from typing import Any, Protocol

import httpx

from agent_debugger.domain.errors import DependencyError
from agent_debugger.domain.model import digest_of
from agent_debugger.protocol.events import RunEvent
from agent_debugger.util.secrets import redact, resolve_secret_ref

MAX_PACKET_EVENTS = 60

JUDGE_PROMPT = """You review a coding agent's debugging trajectory.
Given the bounded evidence packet, answer in strict JSON:
{"findings": [{"code": str, "summary": str, "evidence_seqs": [int]}]}
Comment only on investigation quality and reasoning discipline. Do not
assign numeric scores and do not judge task completion or safety."""


class RubricJudge(Protocol):
    async def review(self, packet: dict[str, Any]) -> dict[str, Any]: ...


def build_evidence_packet(events: list[RunEvent], task: str) -> dict[str, Any]:
    trimmed = []
    for event in events[:MAX_PACKET_EVENTS]:
        payload = dict(event.payload)
        payload.pop("state_projection", None)
        trimmed.append(
            {
                "seq": event.seq,
                "type": event.event_type.value,
                "payload": json.loads(redact(json.dumps(payload))),
            }
        )
    return {"task": task, "events": trimmed, "truncated": len(events) > MAX_PACKET_EVENTS}


class OpenAICompatJudge:
    def __init__(
        self,
        endpoint: str,
        model: str,
        api_key_ref: str | None = None,
        timeout_seconds: float = 120.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.api_key_ref = api_key_ref
        self.timeout_seconds = timeout_seconds
        self._client = client

    async def review(self, packet: dict[str, Any]) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        key = resolve_secret_ref(self.api_key_ref)
        if key:
            headers["Authorization"] = f"Bearer {key}"
        client = self._client or httpx.AsyncClient(timeout=self.timeout_seconds)
        try:
            response = await client.post(
                f"{self.endpoint}/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": JUDGE_PROMPT},
                        {"role": "user", "content": json.dumps(packet, ensure_ascii=False)},
                    ],
                    "temperature": 0.0,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            output = json.loads(content)
            output["digest"] = digest_of(output)
            return output
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise DependencyError(f"Judge model failed: {exc}") from exc
        finally:
            if self._client is None:
                await client.aclose()
