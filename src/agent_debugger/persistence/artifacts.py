"""Content-addressed artifact store (PRD §15.7). Immutable by digest, atomic writes."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from agent_debugger.domain.errors import IntegrityError
from agent_debugger.domain.model import ArtifactMeta, sha256_hex


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, digest: str) -> Path:
        return self.root / digest[:2] / digest

    def put(
        self,
        content: str | bytes,
        media_type: str,
        logical_role: str,
        creation_event: str | None = None,
    ) -> ArtifactMeta:
        data = content.encode("utf-8") if isinstance(content, str) else content
        digest = sha256_hex(data)
        target = self._path_for(digest)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".tmp-")
            try:
                with os.fdopen(fd, "wb") as fh:
                    fh.write(data)
                os.replace(tmp, target)  # atomic on the same filesystem
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
        return ArtifactMeta(
            artifact_id=f"sha256:{digest}",
            media_type=media_type,
            digest=digest,
            size=len(data),
            logical_role=logical_role,
            creation_event=creation_event,
        )

    def get_bytes(self, digest: str) -> bytes:
        digest = digest.removeprefix("sha256:")
        path = self._path_for(digest)
        if not path.exists():
            raise IntegrityError(f"Artifact not found: {digest}")
        data = path.read_bytes()
        if sha256_hex(data) != digest:
            raise IntegrityError(f"Artifact digest mismatch for {digest}")
        return data

    def get_text(self, digest: str) -> str:
        return self.get_bytes(digest).decode("utf-8")

    def exists(self, digest: str) -> bool:
        return self._path_for(digest.removeprefix("sha256:")).exists()
