import pytest

from agent_debugger.domain.errors import ConfigurationError, IntegrityError
from agent_debugger.domain.model import EventType
from agent_debugger.protocol.events import GENESIS_HASH, make_event, verify_chain
from agent_debugger.util.secrets import REDACTED, redact, resolve_secret_ref


def chain(n=3):
    events, prev = [], GENESIS_HASH
    for i in range(n):
        event = make_event("r", i, EventType.AGENT_ACTION, {"i": i}, prev, f"t{i}")
        events.append(event)
        prev = event.event_hash
    return events


class TestHashChain:
    def test_valid_chain_verifies(self):
        verify_chain(chain())

    def test_payload_tamper_detected(self):
        events = chain()
        events[1] = events[1].model_copy(update={"payload": {"i": 999}})
        with pytest.raises(IntegrityError):
            verify_chain(events)

    def test_reorder_detected(self):
        events = chain()
        events[1], events[2] = events[2], events[1]
        with pytest.raises(IntegrityError):
            verify_chain(events)

    def test_dropped_event_detected(self):
        events = chain()
        del events[1]
        with pytest.raises(IntegrityError):
            verify_chain(events)


class TestSecrets:
    def test_resolve_env(self, monkeypatch):
        monkeypatch.setenv("MY_TOKEN", "abc123")
        assert resolve_secret_ref("env:MY_TOKEN") == "abc123"

    def test_resolve_missing_env_raises(self, monkeypatch):
        monkeypatch.delenv("NOPE_TOKEN", raising=False)
        with pytest.raises(ConfigurationError):
            resolve_secret_ref("env:NOPE_TOKEN")

    def test_unsupported_scheme(self):
        with pytest.raises(ConfigurationError):
            resolve_secret_ref("vault://secret")

    @pytest.mark.parametrize(
        "text",
        [
            "key sk-abcdefghijklmnopqrstuvwxyz123456 done",
            "AKIAIOSFODNN7EXAMPLE",
            "Authorization: Bearer abcdef1234567890abcdef",
            'api_key="super-secret-value-42"',
            "password: hunter2hunter2",
        ],
    )
    def test_redacts_secret_shapes(self, text):
        assert REDACTED in redact(text)

    def test_redacts_known_values(self):
        assert redact("the secret is XYZZY", extra_values=["XYZZY"]) == f"the secret is {REDACTED}"

    def test_leaves_normal_text(self):
        text = "tests/test_login.py::test_login FAILED"
        assert redact(text) == text
