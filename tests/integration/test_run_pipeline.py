"""Core-with-real-components integration: orchestrator + engine + stores + replay."""
import pytest

from agent_debugger.adapters.reference import ReferenceHeuristicAgent
from agent_debugger.adapters.scripted import ScriptedAgent
from agent_debugger.domain.model import RunLimits, RunStatus, TerminalReason
from agent_debugger.orchestration.replay import replay_run
from agent_debugger.orchestration.runner import RunOrchestrator
from agent_debugger.renderers.deterministic import DeterministicRenderer
from agent_debugger.reports.run_report import build_run_report


async def run_trajectory(workspace, package, revision, trajectory_name, seed=0, limits=None):
    adapter = ScriptedAgent(package.load_trajectory(trajectory_name))
    orchestrator = RunOrchestrator(
        workspace=workspace, package=package, agent_revision=revision, adapter=adapter,
        renderer=DeterministicRenderer(), seed=seed, limits=limits or RunLimits(max_actions=25),
    )
    return await orchestrator.execute()


class TestRunPipeline:
    async def test_known_good_full_pipeline(self, workspace, login_package, scripted_revision):
        result = await run_trajectory(workspace, login_package, scripted_revision, "known_good")
        assert result.terminal_reason is TerminalReason.SUCCESS
        assert result.status is RunStatus.COMPLETED
        assert result.scorecard is not None and result.scorecard.overall_score == 100.0

        replay = replay_run(workspace.run_dir(result.run_id), login_package)
        assert replay["chain_verified"] and replay["match"]
        assert replay["scenario_digest_match"]

        report = build_run_report(workspace.run_dir(result.run_id),
                                  workspace.db().get_run(result.run_id))
        assert report["outcome"]["terminal_reason"] == "success"
        assert report["provenance"]["manifest"]["scenario_digest"] == login_package.digest

    async def test_destructive_path_hits_failure_predicate(
        self, workspace, login_package, scripted_revision
    ):
        result = await run_trajectory(workspace, login_package, scripted_revision, "known_bad")
        assert result.terminal_reason is TerminalReason.FAILURE_PREDICATE
        safety = result.scorecard.dimension("safety")
        assert safety.score < 10.0

    async def test_replay_detects_tampered_scenario(
        self, workspace, login_package, scripted_revision, tmp_path
    ):
        import shutil

        from agent_debugger.scenario.package import load_package

        result = await run_trajectory(workspace, login_package, scripted_revision, "known_good")
        clone = tmp_path / "tampered"
        shutil.copytree(login_package.root, clone)
        target = clone / "fixtures" / "repository" / "src" / "auth.py"
        target.write_text(target.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
        replay = replay_run(workspace.run_dir(result.run_id), load_package(clone))
        assert not replay["scenario_digest_match"]
        assert not replay["match"] and replay["divergence"] is not None

    async def test_action_limit_terminates_run(self, workspace, login_package, scripted_revision):
        result = await run_trajectory(
            workspace, login_package, scripted_revision, "known_good",
            limits=RunLimits(max_actions=2),
        )
        assert result.terminal_reason is TerminalReason.ACTION_LIMIT

    async def test_ten_consecutive_runs_replay_identically(
        self, workspace, login_package, scripted_revision
    ):
        """Phase 1 exit criterion: repeated runs preserve authoritative consistency."""
        final_hashes = set()
        for i in range(10):
            result = await run_trajectory(
                workspace, login_package, scripted_revision, "known_good", seed=5
            )
            final_hashes.add(result.final_state_hash)
            replay = replay_run(workspace.run_dir(result.run_id), login_package)
            assert replay["match"], f"replay diverged on iteration {i}"
        assert len(final_hashes) == 1


class TestReferenceAgentBehavioralDifference:
    async def test_careful_vs_hasty(self, workspace, login_package):
        """Phase 1 dogfooding: two policies produce a detectable behavioral difference."""
        from agent_debugger.domain.model import AgentRevision

        fix = [
            {
                "action_type": "fs.patch",
                "params": {
                    "path": "tests/conftest.py",
                    "mode": "edit",
                    "edits": [
                        {
                            "old_text": 'os.environ.setdefault("APP_ENV", "test")',
                            "new_text": 'os.environ.setdefault("APP_ENV", "test")\nos.environ.setdefault("JWT_SECRET", "s")',
                        }
                    ],
                },
            }
        ]
        results = {}
        for name, behavior in (
            ("careful", {"hypothesis": "JWT_SECRET missing", "fix": fix, "verify_fix": True}),
            ("hasty", {"investigate": [], "fix": fix, "verify_fix": False}),
        ):
            revision = AgentRevision(
                revision_id=f"agent-{name}", name=name, adapter_id="reference-heuristic",
                adapter_version="0.1.0", model_identifier="heuristic", prompt_digest="0",
                behavior=behavior,
            )
            orchestrator = RunOrchestrator(
                workspace=workspace, package=login_package, agent_revision=revision,
                adapter=ReferenceHeuristicAgent(behavior), renderer=DeterministicRenderer(),
                limits=RunLimits(max_actions=25),
            )
            results[name] = await orchestrator.execute()

        assert results["careful"].terminal_reason is TerminalReason.SUCCESS
        assert results["hasty"].terminal_reason is TerminalReason.SUBMITTED_UNSOLVED
        assert (
            results["careful"].scorecard.overall_score
            > results["hasty"].scorecard.overall_score
        )
