import pytest

from agent_debugger.protocol.actions import CanonicalAction
from agent_debugger.scenario.engine import StateEngine


@pytest.fixture()
def engine(login_package):
    return StateEngine(login_package.manifest, login_package.build_initial_state(), seed=42)


def act(engine, action_type, turn=1, **params):
    return engine.apply(CanonicalAction(action_type=action_type, params=params), turn)


class TestHandlers:
    def test_fs_read_window(self, engine):
        result = act(engine, "fs.read", path="src/auth.py", start_line=1, end_line=3)
        assert result.ok and result.data["start_line"] == 1
        assert "Token creation" in result.data["content"]

    def test_fs_patch_mismatch_is_error(self, engine):
        result = act(engine, "fs.patch", path="src/auth.py",
                     edits=[{"old_text": "NOT PRESENT", "new_text": "x"}])
        assert not result.ok and result.error["code"] == "patch_mismatch"

    def test_fs_patch_create_and_conflict(self, engine):
        assert act(engine, "fs.patch", path="notes.md", mode="create", content="hi").ok
        result = act(engine, "fs.patch", path="notes.md", mode="create", content="again")
        assert not result.ok and result.error["code"] == "already_exists"

    def test_shell_allowlisted_template(self, engine):
        result = act(engine, "shell.run", command="cat .env.example")
        assert result.ok and "JWT_SECRET=dev-secret-change-me" in result.data["stdout"]

    def test_shell_not_allowlisted(self, engine):
        result = act(engine, "shell.run", command="python -c 'import os'")
        assert not result.ok and result.error["code"] == "command_not_allowlisted"

    def test_test_run_fail_then_pass(self, engine):
        first = act(engine, "test.run", turn=1)
        assert first.data["results"]["tests/test_login.py"] == "fail"
        act(engine, "env.set", turn=2, name="JWT_SECRET", value="s", scope="test")
        second = act(engine, "test.run", turn=3)
        assert second.data["results"]["tests/test_login.py"] == "pass"
        assert engine.success_satisfied()

    def test_git_diff_and_status(self, engine):
        act(engine, "fs.patch", path="README.md",
            edits=[{"old_text": "demo-webapp", "new_text": "demo-webapp-2"}])
        status = act(engine, "git.status", turn=2)
        assert status.data["status"]["modified"] == ["README.md"]
        diff = act(engine, "git.diff", turn=3)
        assert "-# demo-webapp" in diff.data["diff"] and "+# demo-webapp-2" in diff.data["diff"]

    def test_unknown_action(self, engine):
        result = act(engine, "fs.teleport")
        assert not result.ok and result.error["code"] == "unknown_action"

    def test_terminal_hints(self, engine):
        assert act(engine, "agent.submit", summary="done").terminal_hint == "submit"
        assert act(engine, "agent.give_up", reason="stuck").terminal_hint == "give_up"


class TestPerturbations:
    def test_same_seed_same_schedule(self, dependency_package):
        def schedule(seed):
            engine = StateEngine(
                dependency_package.manifest, dependency_package.build_initial_state(), seed=seed
            )
            return [
                engine._perturbation_for("fs.search", turn) is not None for turn in range(40)
            ]

        assert schedule(7) == schedule(7)
        assert any(schedule(7))  # probability 0.4 over 40 turns

    def test_different_seed_differs(self, dependency_package):
        def hits(seed):
            engine = StateEngine(
                dependency_package.manifest, dependency_package.build_initial_state(), seed=seed
            )
            return tuple(
                engine._perturbation_for("fs.search", turn) is not None for turn in range(60)
            )

        assert hits(1) != hits(2)

    def test_perturbed_action_fails_cleanly(self, dependency_package):
        engine = StateEngine(
            dependency_package.manifest, dependency_package.build_initial_state(), seed=7
        )
        perturbed_turn = next(
            turn for turn in range(40) if engine._perturbation_for("fs.search", turn)
        )
        result = engine.apply(
            CanonicalAction(action_type="fs.search", params={"query": "requests"}), perturbed_turn
        )
        assert not result.ok and result.perturbed and result.error["code"] == "tool_failure"
