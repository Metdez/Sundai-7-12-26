import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from agent_debugger.domain.model import AgentRevision, RunLimits  # noqa: E402
from agent_debugger.persistence.workspace import Workspace  # noqa: E402
from agent_debugger.scenario.package import load_package  # noqa: E402


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def login_package():
    return load_package(REPO_ROOT / "scenarios" / "login-env-var")


@pytest.fixture(scope="session")
def dependency_package():
    return load_package(REPO_ROOT / "scenarios" / "missing-dependency")


@pytest.fixture()
def workspace(tmp_path):
    ws = Workspace.init(tmp_path / "ws")
    yield ws
    ws.close()


@pytest.fixture()
def scripted_revision():
    return AgentRevision(
        revision_id="agent-test-scripted",
        name="test-scripted",
        adapter_id="scripted",
        adapter_version="0.1.0",
        model_identifier="none",
        prompt_digest="0",
        limits=RunLimits(max_actions=25),
    )
