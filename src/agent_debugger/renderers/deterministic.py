"""Deterministic template renderer (FR-010, NFR-012 offline operation).

Formats authoritative transition results as plain terminal-style text.
Identical input produces identical output; no network, no randomness.
"""
from __future__ import annotations

from agent_debugger.renderers.base import RenderRequest, RenderResult


class DeterministicRenderer:
    name = "deterministic"
    revision = "0.1.0"

    async def render(self, request: RenderRequest) -> RenderResult:
        return RenderResult(body=render_deterministic(request), source="deterministic")


def render_deterministic(request: RenderRequest) -> str:
    action = request.action
    data = request.result_data

    if not request.ok:
        error = request.error or {"code": "error", "message": "action failed"}
        return f"ERROR [{error.get('code', 'error')}]: {error.get('message', '')}"

    t = action.action_type
    if t == "fs.list":
        lines = [
            f"{e['type']:<4} {e['name']}" + (f" ({e['size']} bytes)" if e.get("size") is not None else "")
            for e in data.get("entries", [])
        ]
        return f"Contents of {data.get('path', '.')}:\n" + ("\n".join(lines) if lines else "(empty)")
    if t == "fs.read":
        start = data.get("start_line", 1)
        numbered = [
            f"{i:>5}| {line}"
            for i, line in enumerate(data.get("content", "").splitlines(), start=start)
        ]
        header = f"File: {data.get('path')} ({data.get('total_lines', 0)} lines)"
        return header + "\n" + "\n".join(numbered)
    if t == "fs.search":
        matches = data.get("matches", [])
        if not matches:
            return f"No matches for {data.get('query')!r}."
        lines = [f"{m['path']}:{m['line']}: {m['text']}" for m in matches]
        return f"{len(matches)} match(es) for {data.get('query')!r}:\n" + "\n".join(lines)
    if t == "fs.patch":
        return f"Patched {data.get('path')} (mode={data.get('mode')})."
    if t == "fs.delete":
        return f"Deleted {data.get('path')}."
    if t == "shell.run":
        stdout = data.get("stdout", "")
        return f"$ {data.get('command')}\n{stdout}\n(exit code {data.get('exit_code', 0)})"
    if t == "test.run":
        results = data.get("results", {})
        summary = "\n".join(f"{suite}: {status.upper()}" for suite, status in sorted(results.items()))
        return f"{data.get('output', '')}\n\n{summary}"
    if t == "log.read":
        return f"--- log: {data.get('name')} ---\n{data.get('content', '')}"
    if t == "git.diff":
        diff = data.get("diff", "")
        return diff if diff else "No changes."
    if t == "git.status":
        status = data.get("status", {})
        lines = []
        for kind in ("modified", "created", "deleted"):
            for path in status.get(kind, []):
                lines.append(f"{kind}: {path}")
        return "Working tree status:\n" + ("\n".join(lines) if lines else "clean")
    if t == "env.get":
        if data.get("set"):
            return f"{data.get('name')}={data.get('value')}"
        return f"{data.get('name')} is not set in scope {data.get('scope')}"
    if t == "env.set":
        return f"Set {data.get('name')} in scope {data.get('scope')}."
    if t == "agent.hypothesis":
        return "Hypothesis recorded."
    if t == "agent.submit":
        return "Submission received. Evaluating final state."
    if t == "agent.give_up":
        return "Run ended: agent gave up."
    return str(data)
