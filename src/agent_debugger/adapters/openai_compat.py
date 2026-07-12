"""OpenAI-compatible tool-loop adapter (FR-009).

Drives any hosted or local model that speaks the OpenAI chat-completions
tool-calling dialect (vLLM, SGLang, llama.cpp server, OpenAI, etc.).
"""
from __future__ import annotations

import json
from typing import Any

import httpx

from agent_debugger.adapters.base import AgentContext
from agent_debugger.domain.errors import DependencyError
from agent_debugger.protocol.actions import Observation
from agent_debugger.util.secrets import resolve_secret_ref


def _tools_for_openai(tool_contract: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tools = []
    for tool in tool_contract:
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool["name"].replace(".", "__"),
                    "description": f"Canonical action {tool['name']}",
                    "parameters": tool["parameters"],
                },
            }
        )
    return tools


class OpenAICompatAdapter:
    adapter_id = "openai-compat"
    adapter_version = "0.1.0"

    def __init__(
        self,
        endpoint: str,
        model: str,
        system_prompt: str,
        api_key_ref: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1200,
        timeout_seconds: float = 120.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.system_prompt = system_prompt
        self.api_key_ref = api_key_ref
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        self._client = client
        self._messages: list[dict[str, Any]] = []
        self._tools: list[dict[str, Any]] = []
        self._canceled = False
        self._tokens = 0
        self._pending_tool_call_id: str | None = None

    async def start(self, context: AgentContext) -> None:
        self._messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": (
                    f"Task: {context.task}\n\n"
                    "Work through the debugging task using the provided tools. "
                    "Call agent__submit when the fix is verified, or agent__give_up if stuck."
                ),
            },
        ]
        self._tools = _tools_for_openai(context.tool_contract)

    async def next_action(self, observation: Observation | None) -> dict[str, Any]:
        if self._canceled:
            return {"action_type": "agent.give_up", "params": {"reason": "canceled"}}
        if observation is not None and self._pending_tool_call_id is not None:
            self._messages.append(
                {
                    "role": "tool",
                    "tool_call_id": self._pending_tool_call_id,
                    "content": observation.body,
                }
            )
            self._pending_tool_call_id = None

        headers = {"Content-Type": "application/json"}
        api_key = resolve_secret_ref(self.api_key_ref)
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        client = self._client or httpx.AsyncClient(timeout=self.timeout_seconds)
        try:
            response = await client.post(
                f"{self.endpoint}/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": self._messages,
                    "tools": self._tools,
                    "tool_choice": "required",
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise DependencyError(f"Agent model endpoint failed: {exc}") from exc
        finally:
            if self._client is None:
                await client.aclose()

        self._tokens += int(data.get("usage", {}).get("total_tokens", 0))
        message = data["choices"][0]["message"]
        self._messages.append(message)
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            # A plain text answer is treated as a submission summary.
            return {
                "action_type": "agent.submit",
                "params": {"summary": (message.get("content") or "")[:2000]},
            }
        call = tool_calls[0]
        self._pending_tool_call_id = call.get("id")
        name = call["function"]["name"].replace("__", ".")
        try:
            params = json.loads(call["function"].get("arguments") or "{}")
        except json.JSONDecodeError:
            params = {"_raw": call["function"].get("arguments")}
        return {
            "action_type": name,
            "params": params,
            "thought": message.get("content"),
        }

    async def cancel(self) -> None:
        self._canceled = True

    def usage(self) -> dict[str, float]:
        return {"tokens": self._tokens, "cost_usd": 0.0}
