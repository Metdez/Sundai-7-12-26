"""Local workspace layout, configuration, and backups (FR-031, PRD §16)."""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from agent_debugger.domain.errors import ConfigurationError
from agent_debugger.persistence.artifacts import ArtifactStore
from agent_debugger.persistence.db import MetadataDB

CONFIG_FILENAME = "agent-debugger.yaml"

DEFAULT_CONFIG: dict[str, Any] = {
    "version": 1,
    "workspace": {
        "artifact_dir": ".agent-debugger/artifacts",
        "runs_dir": ".agent-debugger/runs",
        "database": ".agent-debugger/workspace.db",
    },
    "execution": {
        "max_concurrent_runs": 4,
        "default_action_limit": 80,
        "default_timeout_minutes": 20,
    },
    "providers": {
        "world_model": {
            "type": "openai-compatible",
            "base_url": "${AGENTWORLD_BASE_URL}",
            "model": "Qwen/Qwen-AgentWorld-35B-A3B",
            "api_key_ref": "env:AGENTWORLD_API_KEY",
            "timeout_seconds": 120,
        },
        "fallback_renderer": {"type": "deterministic"},
    },
    "security": {
        "outbound_network": "deny_by_default",
        "approval_required": ["destructive", "external", "privileged"],
    },
    "reporting": {"formats": ["json", "markdown", "html"]},
    "ci": {"fail_on": {"success_rate_drop_percent": 3, "new_safety_violations": 1}},
}


class Workspace:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.config_path = self.root / CONFIG_FILENAME
        self.state_dir = self.root / ".agent-debugger"
        self._db: MetadataDB | None = None
        self._config: dict[str, Any] | None = None

    # -- lifecycle ----------------------------------------------------------
    @classmethod
    def init(cls, root: str | Path) -> "Workspace":
        ws = cls(root)
        ws.root.mkdir(parents=True, exist_ok=True)
        if ws.config_path.exists():
            raise ConfigurationError(f"Workspace already initialized: {ws.config_path}")
        for sub in ("artifacts", "runs", "backups", "reports"):
            (ws.state_dir / sub).mkdir(parents=True, exist_ok=True)
        (ws.root / "scenarios").mkdir(exist_ok=True)
        (ws.root / "configs" / "agents").mkdir(parents=True, exist_ok=True)
        ws.config_path.write_text(
            yaml.safe_dump(DEFAULT_CONFIG, sort_keys=False), encoding="utf-8"
        )
        ws.db()  # create schema
        return ws

    @classmethod
    def find(cls, start: str | Path = ".") -> "Workspace":
        current = Path(start).resolve()
        for candidate in [current, *current.parents]:
            if (candidate / CONFIG_FILENAME).exists():
                return cls(candidate)
        raise ConfigurationError(
            f"No {CONFIG_FILENAME} found from {current}; run `agent-debugger init` first"
        )

    @property
    def is_initialized(self) -> bool:
        return self.config_path.exists()

    def config(self) -> dict[str, Any]:
        if self._config is None:
            if not self.config_path.exists():
                raise ConfigurationError(f"Workspace not initialized at {self.root}")
            self._config = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        return self._config

    # -- components -----------------------------------------------------------
    def db(self) -> MetadataDB:
        if self._db is None:
            path = self.state_dir / "workspace.db"
            path.parent.mkdir(parents=True, exist_ok=True)
            self._db = MetadataDB(path)
        return self._db

    def artifacts(self) -> ArtifactStore:
        return ArtifactStore(self.state_dir / "artifacts")

    def run_dir(self, run_id: str) -> Path:
        return self.state_dir / "runs" / run_id

    def reports_dir(self) -> Path:
        path = self.state_dir / "reports"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def close(self) -> None:
        """Release the database handle (needed for Windows file cleanup)."""
        if self._db is not None:
            self._db.close()
            self._db = None

    def backup(self) -> Path:
        """Copy the metadata database into backups/ before schema changes."""
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = self.state_dir / "backups" / f"workspace-{stamp}.db"
        target.parent.mkdir(parents=True, exist_ok=True)
        source = self.state_dir / "workspace.db"
        if source.exists():
            if self._db is not None:
                self._db.close()
                self._db = None
            shutil.copy2(source, target)
        return target
