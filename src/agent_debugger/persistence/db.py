"""SQLite metadata repositories (ADR: SQLite first, PostgreSQL optional).

Only portable SQL is used so a PostgreSQL backend can be added behind the
same repository interface without changing core queries (NFR-009).
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from agent_debugger.domain.errors import ConfigurationError
from agent_debugger.domain.model import (
    VALID_STATUS_TRANSITIONS,
    AgentRevision,
    RunManifest,
    RunStatus,
)

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS agents (
    revision_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    config_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scenarios (
    scenario_id TEXT NOT NULL,
    version TEXT NOT NULL,
    digest TEXT NOT NULL,
    root_path TEXT NOT NULL,
    title TEXT NOT NULL,
    difficulty TEXT,
    tags_json TEXT NOT NULL,
    registered_at TEXT NOT NULL,
    PRIMARY KEY (scenario_id, version)
);
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    scenario_id TEXT NOT NULL,
    scenario_version TEXT NOT NULL,
    agent_revision_id TEXT NOT NULL,
    status TEXT NOT NULL,
    terminal_reason TEXT,
    seed INTEGER NOT NULL,
    suite_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    manifest_json TEXT NOT NULL,
    metrics_json TEXT,
    scorecard_json TEXT,
    error_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_runs_scenario ON runs (scenario_id, scenario_version);
CREATE INDEX IF NOT EXISTS idx_runs_agent ON runs (agent_revision_id);
CREATE INDEX IF NOT EXISTS idx_runs_suite ON runs (suite_id);
"""


class MetadataDB:
    def __init__(self, path: Path | str) -> None:
        self.path = str(path)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.execute(
            "INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # -- agents -----------------------------------------------------------
    def save_agent(self, revision: AgentRevision, created_at: str) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO agents (revision_id, name, config_json, created_at) VALUES (?,?,?,?)",
            (revision.revision_id, revision.name, revision.model_dump_json(), created_at),
        )
        self._conn.commit()

    def get_agent(self, revision_id: str) -> AgentRevision | None:
        row = self._conn.execute(
            "SELECT config_json FROM agents WHERE revision_id = ?", (revision_id,)
        ).fetchone()
        if row is None:
            # allow lookup by name -> newest revision
            row = self._conn.execute(
                "SELECT config_json FROM agents WHERE name = ? ORDER BY created_at DESC LIMIT 1",
                (revision_id,),
            ).fetchone()
        return AgentRevision.model_validate_json(row["config_json"]) if row else None

    def list_agents(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT revision_id, name, created_at FROM agents ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    # -- scenarios ----------------------------------------------------------
    def register_scenario(
        self,
        scenario_id: str,
        version: str,
        digest: str,
        root_path: str,
        title: str,
        difficulty: str | None,
        tags: list[str],
        registered_at: str,
    ) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO scenarios "
            "(scenario_id, version, digest, root_path, title, difficulty, tags_json, registered_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (scenario_id, version, digest, root_path, title, difficulty, json.dumps(tags), registered_at),
        )
        self._conn.commit()

    def list_scenarios(
        self, tag: str | None = None, difficulty: str | None = None
    ) -> list[dict[str, Any]]:
        rows = self._conn.execute("SELECT * FROM scenarios ORDER BY scenario_id").fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["tags"] = json.loads(item.pop("tags_json"))
            if tag and tag not in item["tags"]:
                continue
            if difficulty and item.get("difficulty") != difficulty:
                continue
            result.append(item)
        return result

    def get_scenario(self, scenario_id: str, version: str | None = None) -> dict[str, Any] | None:
        if version:
            row = self._conn.execute(
                "SELECT * FROM scenarios WHERE scenario_id=? AND version=?",
                (scenario_id, version),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT * FROM scenarios WHERE scenario_id=? ORDER BY version DESC LIMIT 1",
                (scenario_id,),
            ).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["tags"] = json.loads(item.pop("tags_json"))
        return item

    # -- runs ----------------------------------------------------------------
    def create_run(self, manifest: RunManifest, suite_id: str | None = None) -> None:
        self._conn.execute(
            "INSERT INTO runs (run_id, scenario_id, scenario_version, agent_revision_id, status, "
            "seed, suite_id, created_at, updated_at, manifest_json) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                manifest.run_id,
                manifest.scenario_id,
                manifest.scenario_version,
                manifest.agent_revision_id,
                RunStatus.QUEUED.value,
                manifest.seed,
                suite_id,
                manifest.created_at,
                manifest.created_at,
                manifest.model_dump_json(),
            ),
        )
        self._conn.commit()

    def set_run_status(
        self,
        run_id: str,
        status: RunStatus,
        updated_at: str,
        terminal_reason: str | None = None,
        metrics: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        row = self._conn.execute("SELECT status FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            raise ConfigurationError(f"Unknown run: {run_id}")
        current = RunStatus(row["status"])
        if status is not current and status not in VALID_STATUS_TRANSITIONS[current]:
            raise ConfigurationError(
                f"Invalid run lifecycle transition {current.value} -> {status.value}"
            )
        self._conn.execute(
            "UPDATE runs SET status=?, updated_at=?, "
            "terminal_reason=COALESCE(?, terminal_reason), "
            "metrics_json=COALESCE(?, metrics_json), "
            "error_json=COALESCE(?, error_json) WHERE run_id=?",
            (
                status.value,
                updated_at,
                terminal_reason,
                json.dumps(metrics) if metrics is not None else None,
                json.dumps(error) if error is not None else None,
                run_id,
            ),
        )
        self._conn.commit()

    def save_scorecard(self, run_id: str, scorecard_json: str, updated_at: str) -> None:
        self._conn.execute(
            "UPDATE runs SET scorecard_json=?, updated_at=? WHERE run_id=?",
            (scorecard_json, updated_at, run_id),
        )
        self._conn.commit()

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        return self._row_to_run(row) if row else None

    def list_runs(
        self,
        scenario_id: str | None = None,
        agent_revision_id: str | None = None,
        suite_id: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM runs WHERE 1=1"
        params: list[Any] = []
        if scenario_id:
            query += " AND scenario_id=?"
            params.append(scenario_id)
        if agent_revision_id:
            query += " AND agent_revision_id=?"
            params.append(agent_revision_id)
        if suite_id:
            query += " AND suite_id=?"
            params.append(suite_id)
        if status:
            query += " AND status=?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        return [self._row_to_run(r) for r in self._conn.execute(query, params).fetchall()]

    @staticmethod
    def _row_to_run(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["manifest"] = json.loads(item.pop("manifest_json"))
        metrics_json = item.pop("metrics_json", None)
        scorecard_json = item.pop("scorecard_json", None)
        error_json = item.pop("error_json", None)
        item["metrics"] = json.loads(metrics_json) if metrics_json else None
        item["scorecard"] = json.loads(scorecard_json) if scorecard_json else None
        item["error"] = json.loads(error_json) if error_json else None
        return item
