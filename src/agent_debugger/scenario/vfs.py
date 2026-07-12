"""Virtual filesystem namespace for simulated repositories (PRD §20).

All agent paths are normalized and constrained here. Absolute host paths,
traversal, null bytes, and oversized files are rejected. Nothing in this
module ever touches the host filesystem.
"""
from __future__ import annotations

import fnmatch
import re

from agent_debugger.domain.errors import AgentDebuggerError, ErrorCategory
from agent_debugger.domain.model import sha256_hex

MAX_FILE_BYTES = 1_000_000
MAX_FILE_COUNT = 5_000


class PathViolation(AgentDebuggerError):
    """Unsafe virtual path proposed by an agent. Attributed to the agent."""

    def __init__(self, message: str, path: str) -> None:
        super().__init__(
            message,
            category=ErrorCategory.AGENT_BEHAVIOR,
            actor="agent",
            details={"path": path},
        )


def normalize_path(path: str) -> str:
    """Normalize a virtual path; raise PathViolation for unsafe input."""
    if not isinstance(path, str) or path == "":
        raise PathViolation("Empty path", path=str(path))
    if "\x00" in path:
        raise PathViolation("Null byte in path", path=repr(path))
    candidate = path.replace("\\", "/")
    if candidate.startswith("/") or candidate.startswith("~"):
        raise PathViolation("Absolute or home-relative paths are not allowed", path=path)
    if re.match(r"^[A-Za-z]:", candidate):
        raise PathViolation("Host drive paths are not allowed", path=path)
    parts: list[str] = []
    for part in candidate.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise PathViolation("Path traversal is not allowed", path=path)
        parts.append(part)
    if not parts:
        return "."
    return "/".join(parts)


class VirtualFileSystem:
    """Immutable-friendly in-memory file tree: path -> text content."""

    def __init__(self, files: dict[str, str] | None = None) -> None:
        self._files: dict[str, str] = {}
        for path, content in (files or {}).items():
            self.write(path, content)

    # -- queries ---------------------------------------------------------
    def exists(self, path: str) -> bool:
        return normalize_path(path) in self._files

    def read(self, path: str) -> str:
        norm = normalize_path(path)
        if norm not in self._files:
            raise FileNotFoundError(norm)
        return self._files[norm]

    def paths(self) -> list[str]:
        return sorted(self._files)

    def list_dir(self, path: str = ".") -> list[dict[str, object]]:
        norm = normalize_path(path)
        prefix = "" if norm == "." else norm + "/"
        seen: dict[str, dict[str, object]] = {}
        for p in self._files:
            if not p.startswith(prefix):
                continue
            rest = p[len(prefix):]
            if "/" in rest:
                name = rest.split("/", 1)[0]
                seen.setdefault(name, {"name": name, "type": "dir"})
            else:
                seen[rest] = {"name": rest, "type": "file", "size": len(self._files[p])}
        if not seen and norm != "." and norm not in self._files:
            raise FileNotFoundError(norm)
        return [seen[k] for k in sorted(seen)]

    def search(
        self, query: str, glob: str | None = None, regex: bool = False, max_results: int = 200
    ) -> list[dict[str, object]]:
        matcher = re.compile(query) if regex else None
        results: list[dict[str, object]] = []
        for path in self.paths():
            if glob and not fnmatch.fnmatch(path, glob):
                continue
            for line_no, line in enumerate(self._files[path].splitlines(), start=1):
                hit = matcher.search(line) if matcher else (query in line)
                if hit:
                    results.append({"path": path, "line": line_no, "text": line.rstrip()})
                    if len(results) >= max_results:
                        return results
        return results

    # -- mutations -------------------------------------------------------
    def write(self, path: str, content: str) -> str:
        norm = normalize_path(path)
        if len(content.encode("utf-8", errors="replace")) > MAX_FILE_BYTES:
            raise PathViolation("File exceeds size limit", path=norm)
        if norm not in self._files and len(self._files) >= MAX_FILE_COUNT:
            raise PathViolation("File count limit exceeded", path=norm)
        self._files[norm] = content
        return norm

    def delete(self, path: str) -> str:
        norm = normalize_path(path)
        if norm not in self._files:
            raise FileNotFoundError(norm)
        del self._files[norm]
        return norm

    # -- hashing / snapshot ----------------------------------------------
    def digests(self) -> dict[str, str]:
        return {p: sha256_hex(c) for p, c in self._files.items()}

    def to_dict(self) -> dict[str, str]:
        return dict(self._files)

    @classmethod
    def from_dict(cls, files: dict[str, str]) -> "VirtualFileSystem":
        return cls(files)
