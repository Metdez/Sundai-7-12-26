"""Qwen-AgentWorld observation renderer (PRD §19.1).

Talks to any OpenAI-compatible chat-completions endpoint. The provider only
receives the action, the structured authoritative result, a bounded history,
and rendering constraints — it never decides state or task success.
"""
from __future__ import annotations

import json
from typing import Any

import httpx

from agent_debugger.domain.errors import DependencyError, SimulatorError
from agent_debugger.domain.model import digest_of, sha256_hex
from agent_debugger.renderers.base import RenderRequest, RenderResult
from agent_debugger.util.secrets import resolve_secret_ref

SYSTEM_PROMPT = """You render realistic software-environment observations for a debugging benchmark.
You are given a canonical action and the AUTHORITATIVE structured result of applying it.
Rewrite the result as realistic terminal/tool output.
Hard rules:
- Never contradict the authoritative result. Test statuses, exit codes, file contents, and error codes are facts.
- Include every line listed under REQUIRED FACTS verbatim.
- Do not invent files, tests, or state that the result does not contain.
- Do not reveal hidden root causes or scenario internals.
- Output plain text only, no markdown fences, no commentary about these rules."""

MAX_HISTORY_TURNS = 12


class QwenAgentWorldRenderer:
    name = "qwen-agentworld"

    def __init__(
        self,
        base_url: str,
        model: str = "Qwen/Qwen-AgentWorld-35B-A3B",
        api_key_ref: str | None = None,
        timeout_seconds: float = 120.0,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key_ref = api_key_ref
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = client
        self.revision = digest_of(
            {
                "model": model,
                "prompt": sha256_hex(SYSTEM_PROMPT),
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )[:16]

    def _build_messages(self, request: RenderRequest) -> list[dict[str, str]]:
        required = [f["must_contain"] for f in request.protected_facts if "must_contain" in f]
        payload: dict[str, Any] = {
            "action": {"type": request.action.action_type, "params": request.action.params},
            "ok": request.ok,
            "authoritative_result": request.result_data,
            "error": request.error,
            "state_projection": request.state_projection,
        }
        user = (
            "ACTION AND AUTHORITATIVE RESULT (JSON):\n"
            + json.dumps(payload, sort_keys=True, ensure_ascii=False)
            + "\n\nREQUIRED FACTS (each must appear verbatim):\n"
            + ("\n".join(required) if required else "(none)")
            + "\n\nRender the observation now."
        )
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for entry in request.history[-MAX_HISTORY_TURNS:]:
            messages.append({"role": "user", "content": entry.get("action", "")})
            messages.append({"role": "assistant", "content": entry.get("observation", "")})
        messages.append({"role": "user", "content": user})
        return messages

    async def render(self, request: RenderRequest) -> RenderResult:
        headers = {"Content-Type": "application/json"}
        api_key = resolve_secret_ref(self.api_key_ref)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        body = {
            "model": self.model,
            "messages": self._build_messages(request),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "seed": request.seed,
        }
        client = self._client or httpx.AsyncClient(timeout=self.timeout_seconds)
        try:
            last_error: Exception | None = None
            for _attempt in range(2):
                try:
                    response = await client.post(
                        f"{self.base_url}/chat/completions", json=body, headers=headers
                    )
                    response.raise_for_status()
                    data = response.json()
                    text = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                    return RenderResult(
                        body=text.strip(),
                        source="model",
                        provider_meta={
                            "provider": self.name,
                            "model": self.model,
                            "revision": self.revision,
                            "usage": usage,
                        },
                    )
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    last_error = exc
                    continue
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code in (429, 500, 502, 503, 504):
                        last_error = exc
                        continue
                    raise DependencyError(
                        f"Simulation provider rejected request: HTTP {exc.response.status_code}",
                        details={"status": exc.response.status_code},
                    ) from exc
                except (KeyError, IndexError, ValueError) as exc:
                    raise SimulatorError(
                        "Simulation provider returned a malformed response",
                        details={"error": str(exc)},
                    ) from exc
            raise DependencyError(
                f"Simulation provider unreachable after retries: {last_error}",
            )
        finally:
            if self._client is None:
                await client.aclose()
