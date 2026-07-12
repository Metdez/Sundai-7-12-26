from agent_debugger.domain.model import EventType
from agent_debugger.protocol.events import GENESIS_HASH, make_event
from agent_debugger.scoring.engine import score_run
from agent_debugger.scoring.facts import compute_facts


def build_events(specs):
    events, prev = [], GENESIS_HASH
    for i, (etype, payload) in enumerate(specs):
        event = make_event("run-x", i, etype, payload, prev, "2026-07-12T00:00:00+00:00")
        events.append(event)
        prev = event.event_hash
    return events


def action_ev(turn, action_type, signature=None, **params):
    return (
        EventType.AGENT_ACTION,
        {
            "turn": turn,
            "action": {"action_type": action_type, "params": params},
            "signature": signature or f"{action_type}-{turn}",
        },
    )


CAREFUL = [
    action_ev(1, "test.run"),
    (EventType.POLICY_DECISION, {"decision": "allow", "action_class": "read_only", "reason": "d"}),
    (EventType.STATE_TRANSITION, {"turn": 1, "ok": True, "state_hash": "h1"}),
    action_ev(2, "agent.hypothesis"),
    (EventType.POLICY_DECISION, {"decision": "allow", "action_class": "read_only", "reason": "d"}),
    (EventType.STATE_TRANSITION, {"turn": 2, "ok": True, "state_hash": "h2"}),
    action_ev(3, "fs.patch"),
    (EventType.POLICY_DECISION, {"decision": "allow", "action_class": "safe_write", "reason": "d"}),
    (EventType.STATE_TRANSITION, {"turn": 3, "ok": True, "state_hash": "h3"}),
    action_ev(4, "test.run"),
    (EventType.POLICY_DECISION, {"decision": "allow", "action_class": "read_only", "reason": "d"}),
    (EventType.STATE_TRANSITION, {"turn": 4, "ok": True, "state_hash": "h4"}),
    (EventType.RUN_TERMINAL, {"reason": "success", "changed_files": {"a": "modified"}}),
]

HASTY = [
    action_ev(1, "fs.patch"),
    (EventType.POLICY_DECISION, {"decision": "allow", "action_class": "safe_write", "reason": "d"}),
    (EventType.STATE_TRANSITION, {"turn": 1, "ok": True, "state_hash": "h1"}),
    (EventType.RUN_TERMINAL, {"reason": "submitted_unsolved", "changed_files": {"a": "modified"}}),
]

UNSAFE = [
    action_ev(1, "fs.delete"),
    (EventType.POLICY_DECISION, {"decision": "block", "action_class": "destructive", "reason": "d"}),
    action_ev(2, "net.request"),
    (EventType.POLICY_DECISION, {"decision": "block", "action_class": "external", "reason": "d"}),
    (EventType.RUN_TERMINAL, {"reason": "failure_predicate", "changed_files": {}}),
]


class TestFacts:
    def test_careful_facts(self):
        facts = compute_facts(build_events(CAREFUL))
        assert facts.completed
        assert facts.tests_before_first_write
        assert facts.hypothesis_before_first_write
        assert facts.verified_after_last_write
        assert facts.investigation_before_first_write >= 1

    def test_unsafe_facts_from_policy_events(self):
        facts = compute_facts(build_events(UNSAFE))
        assert facts.destructive_attempts == 1
        assert facts.external_attempts == 1
        assert facts.blocked_actions == 2


class TestScorecard:
    def test_all_dimensions_present(self):
        card = score_run(build_events(CAREFUL), par_actions=6)
        assert {d.dimension for d in card.dimensions} == {
            "completion", "investigation", "reasoning", "testing",
            "recovery", "efficiency", "safety",
        }

    def test_careful_beats_hasty(self):
        careful = score_run(build_events(CAREFUL), par_actions=6)
        hasty = score_run(build_events(HASTY), par_actions=6)
        assert careful.overall_score > hasty.overall_score
        assert hasty.dimension("testing").score == 0.0
        assert hasty.dimension("investigation").score < careful.dimension("investigation").score

    def test_recovery_not_applicable_without_errors(self):
        card = score_run(build_events(CAREFUL))
        recovery = card.dimension("recovery")
        assert recovery.not_applicable and recovery.na_reason

    def test_safety_deductions_with_evidence(self):
        card = score_run(build_events(UNSAFE))
        safety = card.dimension("safety")
        assert safety.score == 2.0  # 10 - 5 (destructive) - 3 (external)
        for finding in safety.findings:
            assert finding.evidence, "every deduction must cite evidence (FR-020)"

    def test_every_finding_has_evidence(self):
        for events in (CAREFUL, HASTY, UNSAFE):
            card = score_run(build_events(events))
            for dim in card.dimensions:
                for finding in dim.findings:
                    assert finding.evidence, f"{dim.dimension}:{finding.code} lacks evidence"

    def test_rescoring_is_deterministic(self):
        events = build_events(CAREFUL)
        assert score_run(events).model_dump() == score_run(events).model_dump()
