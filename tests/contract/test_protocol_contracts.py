"""Contract tests: versioned public schemas (NFR-010, §21)."""
import pytest

from agent_debugger.domain.errors import ProtocolError
from agent_debugger.domain.model import SCHEMA_VERSIONS
from agent_debugger.protocol.actions import (
    ACTION_TYPES,
    PROTOCOL_VERSION,
    CanonicalAction,
    Observation,
    normalize_action,
    tool_contract,
)


class TestActionContract:
    def test_protocol_version_pinned(self):
        assert PROTOCOL_VERSION == SCHEMA_VERSIONS["action_protocol"] == "0.1.0"

    def test_tool_contract_covers_all_actions(self):
        tools = tool_contract()
        assert {t["name"] for t in tools} == set(ACTION_TYPES)
        for tool in tools:
            assert tool["protocol_version"] == PROTOCOL_VERSION
            assert tool["parameters"]["type"] == "object"

    @pytest.mark.parametrize(
        "raw",
        [
            {"action_type": "fs.read", "params": {"path": "a.py"}},
            {"action_type": "fs.patch", "params": {"path": "a.py", "mode": "create", "content": "x"}},
            {"action_type": "shell.run", "params": {"command": "ls"}},
            {"action_type": "test.run", "params": {}},
            {"action_type": "agent.hypothesis", "params": {"statement": "because"}},
        ],
    )
    def test_valid_actions_normalize(self, raw):
        action = normalize_action(raw)
        assert action.protocol_version == PROTOCOL_VERSION
        assert action.signature()

    @pytest.mark.parametrize(
        "raw",
        [
            "not a dict",
            {"params": {}},
            {"action_type": "fs.read", "params": {"path": 42}},
            {"action_type": "fs.search", "params": {"query": ""}},
            {"action_type": "fs.patch", "params": {"path": "a", "mode": "sideways"}},
            {"action_type": "shell.run", "params": {}},
        ],
    )
    def test_invalid_actions_raise_protocol_error(self, raw):
        with pytest.raises(ProtocolError):
            normalize_action(raw)

    def test_unknown_action_type_is_envelope_valid(self):
        # Unknown types flow to policy/state so framework quirks are measurable.
        action = normalize_action({"action_type": "fs.teleport", "params": {"x": 1}})
        assert action.action_type == "fs.teleport"

    def test_signature_stable_and_param_sensitive(self):
        a = CanonicalAction(action_type="fs.read", params={"path": "a"})
        b = CanonicalAction(action_type="fs.read", params={"path": "a"})
        c = CanonicalAction(action_type="fs.read", params={"path": "b"})
        assert a.signature() == b.signature() != c.signature()

    def test_observation_schema(self):
        obs = Observation(turn=1, action_type="fs.read", body="x")
        data = obs.model_dump()
        assert {"turn", "action_type", "status", "source", "body", "data", "protocol_version"} <= set(data)
