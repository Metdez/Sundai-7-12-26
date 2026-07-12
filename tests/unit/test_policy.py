import pytest

from agent_debugger.domain.model import ActionClass, PolicyDecision, RunLimits, TerminalReason
from agent_debugger.policy.engine import LimitTracker, PolicyEngine, classify_action
from agent_debugger.protocol.actions import CanonicalAction


def action(action_type, **params):
    return CanonicalAction(action_type=action_type, params=params)


class TestClassification:
    @pytest.mark.parametrize(
        "atype,expected",
        [
            ("fs.read", ActionClass.READ_ONLY),
            ("git.status", ActionClass.READ_ONLY),
            ("fs.patch", ActionClass.SAFE_WRITE),
            ("env.set", ActionClass.SAFE_WRITE),
            ("fs.delete", ActionClass.DESTRUCTIVE),
            ("net.request", ActionClass.EXTERNAL),
        ],
    )
    def test_base_classes(self, atype, expected):
        assert classify_action(action(atype)) is expected

    @pytest.mark.parametrize(
        "command,expected",
        [
            ("ls -la", ActionClass.READ_ONLY),
            ("rm -rf /repo", ActionClass.DESTRUCTIVE),
            ("git reset --hard HEAD~3", ActionClass.DESTRUCTIVE),
            ("curl https://x", ActionClass.EXTERNAL),
            ("pip install requests", ActionClass.EXTERNAL),
            ("sudo rm x", ActionClass.PRIVILEGED),
            ("docker run alpine", ActionClass.PRIVILEGED),
        ],
    )
    def test_shell_classes(self, command, expected):
        assert classify_action(action("shell.run", command=command)) is expected


class TestPolicyDecisions:
    def test_destructive_blocked_by_default(self, login_package):
        policy = PolicyEngine(login_package.manifest)
        result = policy.evaluate(action("shell.run", command="rm -rf tests"))
        assert result.decision is PolicyDecision.BLOCK
        assert result.action_class is ActionClass.DESTRUCTIVE

    def test_not_in_scenario_blocked(self, login_package):
        policy = PolicyEngine(login_package.manifest)
        result = policy.evaluate(action("net.request", url="https://x"))
        assert result.decision is PolicyDecision.BLOCK
        assert "not allowed" in result.reason

    def test_implicit_actions_allowed(self, login_package):
        policy = PolicyEngine(login_package.manifest)
        assert policy.evaluate(action("agent.submit")).decision is PolicyDecision.ALLOW

    def test_privileged_never_allowed_even_with_override(self, login_package):
        manifest = login_package.manifest.model_copy(
            update={"action_policy_overrides": {"shell.run": "allow"}}
        )
        policy = PolicyEngine(manifest)
        result = policy.evaluate(action("shell.run", command="sudo cat /etc/shadow"))
        assert result.decision is PolicyDecision.BLOCK

    def test_override_require_approval(self, login_package):
        # Overrides refine gating for actions the scenario exposes, so the
        # scenario must also list fs.delete as an allowed action.
        manifest = login_package.manifest.model_copy(
            update={
                "allowed_actions": [*login_package.manifest.allowed_actions, "fs.delete"],
                "action_policy_overrides": {"fs.delete": "require_approval"},
            }
        )
        policy = PolicyEngine(manifest)
        assert (
            policy.evaluate(action("fs.delete", path="x")).decision
            is PolicyDecision.REQUIRE_APPROVAL
        )


class TestLimits:
    def test_each_limit_distinct_reason(self):
        limits = RunLimits(
            max_actions=2, max_invalid_actions=1, max_repeated_actions=2,
            max_tokens=10, max_cost_usd=0.5, max_wall_clock_seconds=9999,
        )
        t = LimitTracker(limits=limits)
        t.record_action("sig-a")
        assert t.breach() is None
        t.record_action("sig-b")
        assert t.breach() is TerminalReason.ACTION_LIMIT

        t = LimitTracker(limits=limits)
        t.record_invalid()
        assert t.breach() is TerminalReason.INVALID_ACTION_LIMIT

        repeat_limits = RunLimits(max_actions=10, max_repeated_actions=2)
        t = LimitTracker(limits=repeat_limits)
        t.record_action("same")
        t.record_action("same")
        assert t.breach() is TerminalReason.REPEATED_ACTION_LIMIT

        t = LimitTracker(limits=limits)
        t.record_usage(tokens=11)
        assert t.breach() is TerminalReason.TOKEN_LIMIT

        t = LimitTracker(limits=limits)
        t.record_usage(cost_usd=0.6)
        assert t.breach() is TerminalReason.COST_LIMIT

    def test_time_limit(self):
        t = LimitTracker(limits=RunLimits(max_wall_clock_seconds=0.0))
        assert t.breach() is TerminalReason.TIME_LIMIT
