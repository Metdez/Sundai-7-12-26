import pytest

from agent_debugger.domain.errors import ScenarioError
from agent_debugger.scenario.conditions import evaluate_condition
from agent_debugger.scenario.state import AuthoritativeState
from agent_debugger.scenario.vfs import VirtualFileSystem


def make_state(**kw):
    return AuthoritativeState(
        files=VirtualFileSystem(kw.get("files", {"src/a.py": "x = 1\n"})),
        env=kw.get("env", {"test": {"APP_ENV": "test"}}),
        test_suites=kw.get("suites", ["tests/t.py"]),
    )


class TestStateHash:
    def test_deterministic(self):
        assert make_state().state_hash() == make_state().state_hash()

    def test_changes_on_file_edit(self):
        s1, s2 = make_state(), make_state()
        s2.files.write("src/a.py", "x = 2\n")
        s2.transition_counter = s1.transition_counter
        assert s1.state_hash() != s2.state_hash()

    def test_changes_on_attempt_flags(self):
        s1, s2 = make_state(), make_state()
        s2.destructive_attempted = True
        assert s1.state_hash() != s2.state_hash()

    def test_snapshot_roundtrip(self):
        state = make_state()
        state.env_set("K", "v")
        state.files.write("new.txt", "n")
        restored = AuthoritativeState.from_snapshot(state.snapshot())
        assert restored.state_hash() == state.state_hash()
        assert restored.changed_files() == {"new.txt": "created"}


class TestChangedFiles:
    def test_kinds(self):
        state = make_state(files={"keep.py": "k", "mod.py": "old", "gone.py": "g"})
        state.files.write("mod.py", "new")
        state.files.write("added.py", "a")
        state.files.delete("gone.py")
        assert state.changed_files() == {
            "mod.py": "modified",
            "added.py": "created",
            "gone.py": "deleted",
        }


class TestConditions:
    def test_env_var_set(self):
        state = make_state()
        assert not evaluate_condition({"env_var_set": {"name": "JWT", "scope": "test"}}, state)
        state.env_set("JWT", "x")
        assert evaluate_condition({"env_var_set": {"name": "JWT", "scope": "test"}}, state)

    def test_file_conditions(self):
        state = make_state()
        assert evaluate_condition({"file_exists": {"path": "src/a.py"}}, state)
        assert evaluate_condition({"file_contains": {"path": "src/a.py", "text": "x = 1"}}, state)
        assert evaluate_condition({"file_regex": {"path": "src/a.py", "pattern": r"x\s*=\s*\d"}}, state)
        assert evaluate_condition({"file_absent": {"path": "nope"}}, state)
        assert not evaluate_condition({"file_contains": {"path": "nope", "text": "x"}}, state)

    def test_combinators(self):
        state = make_state()
        cond = {
            "all_of": [
                {"file_exists": {"path": "src/a.py"}},
                {"not": {"file_exists": {"path": "nope"}}},
                {"any_of": [{"file_exists": {"path": "nope"}}, {"file_exists": {"path": "src/a.py"}}]},
            ]
        }
        assert evaluate_condition(cond, state)

    def test_test_suite_status(self):
        state = make_state()
        assert not evaluate_condition(
            {"test_suite_status": {"suite": "tests/t.py", "status": "pass"}}, state
        )
        state.test_state["tests/t.py"] = {"status": "pass", "last_run_turn": 3}
        assert evaluate_condition(
            {"test_suite_status": {"suite": "tests/t.py", "status": "pass"}}, state
        )

    def test_unknown_condition_raises(self):
        with pytest.raises(ScenarioError):
            evaluate_condition({"who_knows": {}}, make_state())
