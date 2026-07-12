"""Command-line interface (PRD §10.1). Presentation only; the core does the work.

Exit codes follow PRD §22: 0 ok, 10 benchmark regression, 11 safety regression,
20 invalid configuration/scenario, 21 incompatible versions, 30 dependency
unavailable, 31 infrastructure failure, 40 canceled.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sys
from pathlib import Path

from agent_debugger import __version__
from agent_debugger.application import services
from agent_debugger.domain.errors import (
    AgentDebuggerError,
    ConfigurationError,
    DependencyError,
    ErrorCategory,
)
from agent_debugger.persistence.workspace import Workspace
from agent_debugger.reports.compare import (
    EXIT_CANCELED,
    EXIT_DEPENDENCY_UNAVAILABLE,
    EXIT_INFRASTRUCTURE,
    EXIT_INVALID_CONFIG,
    EXIT_OK,
    compare_run_sets,
    evaluate_regression,
)
from agent_debugger.reports.exporters import run_report_html, run_report_markdown
from agent_debugger.reports.run_report import build_run_report, report_to_json
from agent_debugger.scenario.package import load_package, scaffold_scenario, validate_package

_ERROR_EXIT = {
    ErrorCategory.CONFIGURATION: EXIT_INVALID_CONFIG,
    ErrorCategory.SCENARIO_DEFECT: EXIT_INVALID_CONFIG,
    ErrorCategory.DEPENDENCY: EXIT_DEPENDENCY_UNAVAILABLE,
    ErrorCategory.INFRASTRUCTURE: EXIT_INFRASTRUCTURE,
}


def _print(data, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, indent=2, default=str))
    elif isinstance(data, dict):
        for key, value in data.items():
            print(f"{key}: {value}")
    else:
        print(data)


def _workspace(args) -> Workspace:
    return Workspace.find(getattr(args, "workspace", None) or ".")


# -- commands ----------------------------------------------------------------
def cmd_init(args) -> int:
    ws = Workspace.init(args.directory)
    print(f"Initialized workspace at {ws.root}")
    print("Next: agent-debugger doctor && agent-debugger scenario add <package-dir>")
    return EXIT_OK


def cmd_doctor(args) -> int:
    import importlib

    checks: list[tuple[str, bool, str]] = []
    checks.append(("python", sys.version_info >= (3, 11), sys.version.split()[0]))
    for module in ("pydantic", "yaml", "fastapi", "uvicorn", "httpx"):
        try:
            importlib.import_module(module)
            checks.append((f"dependency:{module}", True, "importable"))
        except ImportError as exc:
            checks.append((f"dependency:{module}", False, str(exc)))
    try:
        ws = Workspace.find(args.workspace or ".")
        checks.append(("workspace", True, str(ws.root)))
        ws.db()
        checks.append(("database", True, "sqlite ok"))
        ws.close()
    except ConfigurationError as exc:
        checks.append(("workspace", False, exc.user_message))
    runtime = shutil.which("docker") or shutil.which("podman")
    checks.append(
        ("container_runtime", runtime is not None,
         runtime or "not found — real validation disabled (optional)")
    )
    import os

    base_url = os.environ.get("AGENTWORLD_BASE_URL")
    checks.append(
        ("world_model_endpoint", base_url is not None,
         base_url or "AGENTWORLD_BASE_URL unset — deterministic renderer only (optional)")
    )
    width = max(len(name) for name, _, _ in checks)
    failures = 0
    for name, ok, detail in checks:
        status = "OK  " if ok else "MISS"
        optional = name in ("container_runtime", "world_model_endpoint")
        if not ok and not optional:
            failures += 1
        print(f"[{status}] {name:<{width}}  {detail}")
    return EXIT_OK if failures == 0 else EXIT_DEPENDENCY_UNAVAILABLE


def cmd_scenario_new(args) -> int:
    path = scaffold_scenario(Path(args.directory), args.scenario_id)
    print(f"Scaffolded scenario at {path}. Edit manifest.yaml, then run scenario validate.")
    return EXIT_OK


def cmd_scenario_validate(args) -> int:
    package = load_package(args.directory)
    report = validate_package(package)
    _print(
        {"scenario_id": package.scenario_id, "digest": package.digest, **report},
        args.json,
    )
    return EXIT_OK if not report["errors"] else EXIT_INVALID_CONFIG


def cmd_scenario_test(args) -> int:
    """Run declared fixture trajectories against the deterministic engine (§11.1)."""
    package = load_package(args.directory)
    report = validate_package(package)
    if report["errors"]:
        _print(report, args.json)
        return EXIT_INVALID_CONFIG

    from agent_debugger.protocol.actions import normalize_action
    from agent_debugger.scenario.engine import StateEngine
    from agent_debugger.policy.engine import PolicyEngine, record_attempt_flags
    from agent_debugger.domain.model import PolicyDecision

    results = {}
    ok = True
    for name in package.manifest.trajectories:
        state = package.build_initial_state()
        engine = StateEngine(package.manifest, state, seed=0)
        policy = PolicyEngine(package.manifest)
        for turn, raw in enumerate(package.load_trajectory(name), start=1):
            action = normalize_action(raw)
            decision = policy.evaluate(action)
            if decision.decision is not PolicyDecision.ALLOW:
                record_attempt_flags(state, decision.action_class)
                continue
            engine.apply(action, turn)
        outcome = (
            "failure_predicate"
            if engine.failure_satisfied()
            else "success" if engine.success_satisfied() else "not_solved"
        )
        deterministic = services.scenario_determinism_check(package, name)
        expected_success = name.startswith("known_good")
        case_ok = deterministic and (
            (outcome == "success") == expected_success if name.startswith("known_") else True
        )
        ok = ok and case_ok
        results[name] = {"outcome": outcome, "deterministic": deterministic, "ok": case_ok}
    _print({"scenario_id": package.scenario_id, "trajectories": results}, args.json)
    return EXIT_OK if ok else EXIT_INVALID_CONFIG


def cmd_scenario_add(args) -> int:
    ws = _workspace(args)
    package = load_package(args.directory)
    report = validate_package(package)
    if report["errors"]:
        _print(report, args.json)
        return EXIT_INVALID_CONFIG
    services.register_scenario(ws, package)
    print(f"Registered {package.scenario_id} v{package.version} (digest {package.digest[:16]}…)")
    ws.close()
    return EXIT_OK


def cmd_scenario_list(args) -> int:
    ws = _workspace(args)
    rows = ws.db().list_scenarios(tag=args.tag, difficulty=args.difficulty)
    _print(rows if args.json else {r["scenario_id"]: r["title"] for r in rows}, args.json)
    ws.close()
    return EXIT_OK


def cmd_agent_add(args) -> int:
    ws = _workspace(args)
    config = services.load_agent_config(args.config)
    revision = services.register_agent(ws, config)

    from agent_debugger.adapters.registry import build_adapter
    from agent_debugger.sdk.conformance import run_conformance

    conformance = asyncio.run(run_conformance(build_adapter(revision)))
    _print(
        {
            "revision_id": revision.revision_id,
            "name": revision.name,
            "adapter": revision.adapter_id,
            "conformance_passed": conformance["passed"],
            "cases": conformance["cases"] if args.json else
            f"{sum(c['passed'] for c in conformance['cases'])}/{len(conformance['cases'])} passed",
        },
        args.json,
    )
    ws.close()
    return EXIT_OK if conformance["passed"] else EXIT_INVALID_CONFIG


def cmd_agent_list(args) -> int:
    ws = _workspace(args)
    _print(ws.db().list_agents(), True)
    ws.close()
    return EXIT_OK


def cmd_run(args) -> int:
    ws = _workspace(args)
    package = services.resolve_package(ws, args.scenario)
    revision = services.get_agent(ws, args.agent)
    result = asyncio.run(
        services.execute_run(
            ws,
            package,
            revision,
            seed=args.seed,
            renderer_override=args.renderer,
            trajectory=args.trajectory,
            operator=args.operator,
        )
    )
    summary = {
        "run_id": result.run_id,
        "status": result.status.value,
        "terminal_reason": result.terminal_reason.value if result.terminal_reason else None,
        "overall_score": result.scorecard.overall_score if result.scorecard else None,
        "metrics": result.metrics,
    }
    _print(summary, args.json)
    ws.close()
    if result.status.value == "failed":
        return EXIT_INFRASTRUCTURE
    if result.status.value == "canceled":
        return EXIT_CANCELED
    return EXIT_OK


def cmd_suite(args) -> int:
    ws = _workspace(args)
    from agent_debugger.orchestration.suite import run_suite

    packages = [services.resolve_package(ws, ref) for ref in args.scenarios]
    revision = services.get_agent(ws, args.agent)
    seeds = [int(s) for s in args.seeds.split(",")] if args.seeds else [0]
    outcome = asyncio.run(
        run_suite(
            ws,
            packages,
            revision,
            renderer_factory=lambda pkg: services.build_renderer(ws, pkg, args.renderer),
            seeds=seeds,
            max_concurrency=args.concurrency,
            labels={"label": args.label} if args.label else {},
        )
    )
    _print(outcome["summary"], args.json)
    ws.close()
    return EXIT_OK


def cmd_replay(args) -> int:
    ws = _workspace(args)
    from agent_debugger.orchestration.replay import replay_run

    run = ws.db().get_run(args.run_id)
    if run is None:
        raise ConfigurationError(f"Unknown run: {args.run_id}")
    package = services.resolve_package(ws, run["scenario_id"])
    report = replay_run(ws.run_dir(args.run_id), package)
    _print(report, args.json)
    ws.close()
    return EXIT_OK if report["match"] else EXIT_INFRASTRUCTURE


def cmd_report(args) -> int:
    ws = _workspace(args)
    run = ws.db().get_run(args.run_id)
    if run is None:
        raise ConfigurationError(f"Unknown run: {args.run_id}")
    report = build_run_report(ws.run_dir(args.run_id), run)
    if args.format == "json":
        output = report_to_json(report)
    elif args.format == "markdown":
        output = run_report_markdown(report)
    elif args.format == "html":
        output = run_report_html(report)
    else:  # jsonl — raw event export
        output = (ws.run_dir(args.run_id) / "events.jsonl").read_text(encoding="utf-8")
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(output)
    ws.close()
    return EXIT_OK


def cmd_compare(args) -> int:
    ws = _workspace(args)
    db = ws.db()
    baseline = db.list_runs(suite_id=args.baseline) or db.list_runs(agent_revision_id=args.baseline)
    candidate = db.list_runs(suite_id=args.candidate) or db.list_runs(agent_revision_id=args.candidate)
    if not baseline or not candidate:
        raise ConfigurationError("Baseline or candidate run set is empty")
    comparison = compare_run_sets(baseline, candidate, args.baseline, args.candidate)
    thresholds = (ws.config().get("ci", {}) or {}).get("fail_on")
    regression = evaluate_regression(comparison, thresholds)
    _print(regression if args.gate else comparison, args.json)
    ws.close()
    return regression["exit_code"] if args.gate else EXIT_OK


def cmd_promote(args) -> int:
    ws = _workspace(args)
    import json as _json

    from agent_debugger.validation.real import run_real_validation

    run = ws.db().get_run(args.run_id)
    if run is None:
        raise ConfigurationError(f"Unknown run: {args.run_id}")
    package = services.resolve_package(ws, run["scenario_id"])
    events = (ws.run_dir(args.run_id) / "events.jsonl").read_text(encoding="utf-8")
    terminal = None
    for line in events.splitlines():
        event = _json.loads(line)
        if event["event_type"] == "run.terminal":
            terminal = event["payload"]
    if terminal is None:
        raise ConfigurationError("Run has no terminal event")
    snapshot_digest = terminal["final_snapshot"]
    snapshot = _json.loads(ws.artifacts().get_text(snapshot_digest))
    report = run_real_validation(
        package,
        changed_files=terminal.get("changed_files", {}),
        final_files=snapshot["files"],
        simulated_success=terminal.get("reason") == "success",
    )
    out = ws.reports_dir() / f"real-validation-{args.run_id}.json"
    out.write_text(_json.dumps(report, indent=2), encoding="utf-8")
    _print(
        {
            "real_success": report["real_success"],
            "simulated_success": report["simulated_success"],
            "outcome_agreement": report["outcome_agreement"],
            "evidence": str(out),
        },
        args.json,
    )
    ws.close()
    return EXIT_OK


def cmd_serve(args) -> int:
    import uvicorn

    from agent_debugger.api.app import create_app

    ws = _workspace(args)
    app = create_app(ws)
    print(f"Serving Agent Debugger dashboard on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return EXIT_OK


# -- parser --------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-debugger",
        description="Reproducible evaluation of AI coding-agent debugging behavior.",
    )
    parser.add_argument("--version", action="version", version=f"agent-debugger {__version__}")
    parser.add_argument("--workspace", help="workspace directory (default: search upward)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="create a new workspace")
    p.add_argument("directory", nargs="?", default=".")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("doctor", help="check environment and optional dependencies")
    p.set_defaults(func=cmd_doctor)

    ps = sub.add_parser("scenario", help="scenario authoring and registry")
    pss = ps.add_subparsers(dest="scenario_command", required=True)
    p = pss.add_parser("new", help="scaffold a scenario package")
    p.add_argument("scenario_id")
    p.add_argument("directory")
    p.set_defaults(func=cmd_scenario_new)
    p = pss.add_parser("validate", help="validate a scenario package")
    p.add_argument("directory")
    p.set_defaults(func=cmd_scenario_validate)
    p = pss.add_parser("test", help="run scenario fixture trajectories + determinism check")
    p.add_argument("directory")
    p.set_defaults(func=cmd_scenario_test)
    p = pss.add_parser("add", help="validate and register a scenario in the workspace")
    p.add_argument("directory")
    p.set_defaults(func=cmd_scenario_add)
    p = pss.add_parser("list", help="list registered scenarios")
    p.add_argument("--tag")
    p.add_argument("--difficulty")
    p.set_defaults(func=cmd_scenario_list)

    pa = sub.add_parser("agent", help="agent registration")
    pas = pa.add_subparsers(dest="agent_command", required=True)
    p = pas.add_parser("add", help="register an agent config and run conformance")
    p.add_argument("config")
    p.set_defaults(func=cmd_agent_add)
    p = pas.add_parser("list", help="list agent revisions")
    p.set_defaults(func=cmd_agent_list)

    p = sub.add_parser("run", help="execute one simulated debugging session")
    p.add_argument("scenario", help="scenario package dir or registered id")
    p.add_argument("--agent", required=True)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--renderer", choices=["deterministic", "qwen-agentworld", "hybrid"])
    p.add_argument("--trajectory", help="scripted adapter: trajectory name from the manifest")
    p.add_argument("--operator")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("suite", help="run multiple scenarios concurrently")
    p.add_argument("scenarios", nargs="+")
    p.add_argument("--agent", required=True)
    p.add_argument("--seeds", default="0")
    p.add_argument("--renderer", choices=["deterministic", "qwen-agentworld", "hybrid"])
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--label")
    p.set_defaults(func=cmd_suite)

    p = sub.add_parser("replay", help="replay a run and verify state hashes")
    p.add_argument("run_id")
    p.set_defaults(func=cmd_replay)

    p = sub.add_parser("report", help="export a run report")
    p.add_argument("run_id")
    p.add_argument("--format", choices=["json", "jsonl", "markdown", "html"], default="markdown")
    p.add_argument("--output", "-o")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("compare", help="compare two run sets (by suite id or agent revision)")
    p.add_argument("--baseline", required=True)
    p.add_argument("--candidate", required=True)
    p.add_argument("--gate", action="store_true", help="apply CI thresholds and exit codes")
    p.set_defaults(func=cmd_compare)

    p = sub.add_parser("promote", help="promote a run's patch to isolated real validation")
    p.add_argument("run_id")
    p.set_defaults(func=cmd_promote)

    p = sub.add_parser("serve", help="start the local API + review dashboard")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8321)
    p.set_defaults(func=cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except DependencyError as exc:
        print(f"error [dependency]: {exc.user_message}", file=sys.stderr)
        return EXIT_DEPENDENCY_UNAVAILABLE
    except AgentDebuggerError as exc:
        print(f"error [{exc.category.value}]: {exc.user_message}", file=sys.stderr)
        return _ERROR_EXIT.get(exc.category, EXIT_INFRASTRUCTURE)
    except KeyboardInterrupt:
        print("canceled", file=sys.stderr)
        return EXIT_CANCELED


if __name__ == "__main__":
    sys.exit(main())
