"""OpenRouter provider gateway for the review dashboard (key + model catalog).

The API key set through the dashboard lives ONLY in this process's
environment (`os.environ`) — never in configs, the database, event payloads,
API responses, or exception messages. Adapters resolve `env:OPENROUTER_API_KEY`
live per request (util/secrets.resolve_secret_ref), so a key installed here
takes effect immediately for new and in-flight runs alike. Single-process
assumption: `agent-debugger serve` runs one uvicorn worker.
"""
from __future__ import annotations

import os
import re
import time
from typing import Any

import httpx

from agent_debugger.domain.errors import ConfigurationError, DependencyError

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
KEY_ENV = "OPENROUTER_API_KEY"
KEY_PATTERN = re.compile(r"^sk-or-[A-Za-z0-9_\-]{20,}$")


class OpenRouterGateway:
    def __init__(
        self,
        base_url: str = OPENROUTER_BASE,
        cache_ttl_seconds: float = 300.0,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.cache_ttl_seconds = cache_ttl_seconds
        self.timeout_seconds = timeout_seconds
        self._client = client
        self._session_set = False
        self._models_cache: tuple[float, list[dict[str, Any]]] | None = None

    # -- key lifecycle ------------------------------------------------------
    @staticmethod
    def mask(key: str) -> str:
        return f"sk-or-…{key[-4:]}" if len(key) >= 4 else "sk-or-…"

    def status(self) -> dict[str, Any]:
        key = os.environ.get(KEY_ENV)
        if not key:
            return {"configured": False, "source": None, "masked": None}
        return {
            "configured": True,
            "source": "session" if self._session_set else "env",
            "masked": self.mask(key),
        }

    async def verify_key(self, key: str) -> bool:
        """True if OpenRouter accepts the key; False if it rejects it.

        Transport problems raise DependencyError (callers may proceed
        unverified). The key value must never appear in errors or logs.
        """
        client = self._client or httpx.AsyncClient(timeout=self.timeout_seconds)
        try:
            response = await client.get(
                f"{self.base_url}/key",
                headers={"Authorization": f"Bearer {key}"},
            )
        except httpx.HTTPError as exc:
            raise DependencyError(
                f"Could not reach OpenRouter to verify the key: {type(exc).__name__}"
            ) from exc
        finally:
            if self._client is None:
                await client.aclose()
        if response.status_code in (401, 403):
            return False
        return response.status_code < 400

    async def set_key(self, key: str) -> dict[str, Any]:
        key = key.strip()
        if not KEY_PATTERN.match(key):
            raise ConfigurationError(
                "That does not look like an OpenRouter key (expected sk-or-…)"
            )
        verified: bool | None
        try:
            if not await self.verify_key(key):
                raise ConfigurationError("OpenRouter rejected this key")
            verified = True
        except DependencyError:
            verified = False  # network hiccup: accept unverified rather than block
        os.environ[KEY_ENV] = key
        self._session_set = True
        return {**self.status(), "verified": verified}

    def clear_key(self) -> dict[str, Any]:
        os.environ.pop(KEY_ENV, None)
        self._session_set = False
        return self.status()

    # -- model catalog ------------------------------------------------------
    async def list_models(self, refresh: bool = False) -> dict[str, Any]:
        now = time.monotonic()
        if (
            not refresh
            and self._models_cache is not None
            and now - self._models_cache[0] < self.cache_ttl_seconds
        ):
            return {"cached": True, "models": self._models_cache[1]}
        client = self._client or httpx.AsyncClient(timeout=self.timeout_seconds)
        try:
            response = await client.get(f"{self.base_url}/models")
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            if self._models_cache is not None:  # serve stale on failure
                return {"cached": True, "stale": True, "models": self._models_cache[1]}
            raise DependencyError(
                f"Could not fetch the OpenRouter model list: {type(exc).__name__}"
            ) from exc
        finally:
            if self._client is None:
                await client.aclose()
        models = [
            {
                "id": entry.get("id"),
                "name": entry.get("name"),
                "context_length": entry.get("context_length"),
                "pricing": entry.get("pricing"),
            }
            for entry in data.get("data", [])
            if entry.get("id")
        ]
        self._models_cache = (now, models)
        return {"cached": False, "models": models}
