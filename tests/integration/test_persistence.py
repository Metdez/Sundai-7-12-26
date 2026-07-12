import json

import pytest

from agent_debugger.domain.errors import ConfigurationError, IntegrityError
from agent_debugger.domain.model import EventType, RunLimits, RunManifest, RunStatus
from agent_debugger.persistence.artifacts import ArtifactStore
from agent_debugger.persistence.events import EventStore


def manifest(run_id="run-t1"):
    return RunManifest(
        run_id=run_id, scenario_id="s.x", scenario_version="1.0.0", scenario_digest="d",
        agent_revision_id="a", agent_config_digest="cd", renderer="deterministic",
        renderer_revision="0", scorer_revision="0.1.0", scoring_profile="p", seed=0,
        limits=RunLimits(), created_at="2026-07-12T00:00:00+00:00", product_version="0.1.0",
    )


class TestEventStore:
    def test_append_read_verify(self, tmp_path):
        store = EventStore(tmp_path / "r1", "r1")
        store.append(EventType.RUN_CREATED, {"a": 1})
        store.append(EventType.RUN_STARTED, {"b": 2})
        events = store.verify()
        assert [e.seq for e in events] == [0, 1]

    def test_resume_continues_chain(self, tmp_path):
        store = EventStore(tmp_path / "r1", "r1")
        first = store.append(EventType.RUN_CREATED, {})
        resumed = EventStore(tmp_path / "r1", "r1")
        second = resumed.append(EventType.RUN_STARTED, {})
        assert second.prev_hash == first.event_hash
        resumed.verify()

    def test_file_tamper_detected(self, tmp_path):
        store = EventStore(tmp_path / "r1", "r1")
        store.append(EventType.RUN_CREATED, {"x": 1})
        store.append(EventType.RUN_STARTED, {})
        lines = store.path.read_text(encoding="utf-8").splitlines()
        first = json.loads(lines[0])
        first["payload"]["x"] = 999
        store.path.write_text(json.dumps(first) + "\n" + lines[1] + "\n", encoding="utf-8")
        with pytest.raises(IntegrityError):
            store.verify()


class TestArtifactStore:
    def test_content_addressed_roundtrip(self, tmp_path):
        store = ArtifactStore(tmp_path / "art")
        meta = store.put("hello", "text/plain", "test")
        assert store.get_text(meta.digest) == "hello"
        again = store.put("hello", "text/plain", "test")
        assert again.digest == meta.digest  # dedup by content

    def test_corruption_detected(self, tmp_path):
        store = ArtifactStore(tmp_path / "art")
        meta = store.put("payload", "text/plain", "test")
        path = store._path_for(meta.digest)
        path.write_bytes(b"corrupted")
        with pytest.raises(IntegrityError):
            store.get_bytes(meta.digest)

    def test_missing_artifact(self, tmp_path):
        with pytest.raises(IntegrityError):
            ArtifactStore(tmp_path / "art").get_bytes("0" * 64)


class TestRunLifecycle:
    def test_valid_transitions(self, workspace):
        db = workspace.db()
        db.create_run(manifest())
        db.set_run_status("run-t1", RunStatus.RUNNING, "t1")
        db.set_run_status("run-t1", RunStatus.COMPLETED, "t2", terminal_reason="success")
        assert db.get_run("run-t1")["status"] == "completed"

    def test_invalid_transition_rejected(self, workspace):
        db = workspace.db()
        db.create_run(manifest("run-t2"))
        db.set_run_status("run-t2", RunStatus.RUNNING, "t1")
        db.set_run_status("run-t2", RunStatus.COMPLETED, "t2")
        with pytest.raises(ConfigurationError):
            db.set_run_status("run-t2", RunStatus.RUNNING, "t3")  # FR-015

    def test_queued_to_completed_rejected(self, workspace):
        db = workspace.db()
        db.create_run(manifest("run-t3"))
        with pytest.raises(ConfigurationError):
            db.set_run_status("run-t3", RunStatus.COMPLETED, "t1")


class TestWorkspace:
    def test_double_init_rejected(self, workspace, tmp_path):
        from agent_debugger.persistence.workspace import Workspace

        with pytest.raises(ConfigurationError):
            Workspace.init(workspace.root)

    def test_find_from_subdirectory(self, workspace):
        from agent_debugger.persistence.workspace import Workspace

        sub = workspace.root / "a" / "b"
        sub.mkdir(parents=True)
        assert Workspace.find(sub).root == workspace.root

    def test_backup_creates_copy(self, workspace):
        workspace.db()
        backup = workspace.backup()
        assert backup.exists() and backup.stat().st_size > 0
