"""Execute the generated CI command with controlled tools, never host runners."""
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from koru.init import POLICY_STUB

pytestmark = pytest.mark.skipif(shutil.which("sh") is None, reason="POSIX shell required")


def tool(directory: Path, name: str, code: int = 0) -> None:
    path = directory / name
    path.write_text(f"#!/bin/sh\nprintf '%s\\n' {name} >> calls\nexit {code}\n")
    path.chmod(0o755)


def run_policy(root: Path, tools: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [shutil.which("sh"), "-c", yaml.safe_load(POLICY_STUB)["ci"]["command"]],
        cwd=root, env={"PATH": str(tools)}, capture_output=True, text=True, timeout=5,
    )


def test_missing_verifier_fails(tmp_path):
    tools = tmp_path / "tools"
    tools.mkdir()
    result = run_policy(tmp_path, tools)
    assert result.returncode == 2
    assert "configure ci.command" in result.stderr
    assert "Quality Gates Complete" not in result.stdout


@pytest.mark.parametrize("name,descriptor", [
    ("task", "Taskfile.yml"), ("pytest", "pyproject.toml"),
    ("npm", "package.json"), ("make", "Makefile"),
])
@pytest.mark.parametrize("code", [0, 7])
def test_selected_runner_exit_is_preserved(tmp_path, name, descriptor, code):
    tools = tmp_path / "tools"
    tools.mkdir()
    (tmp_path / descriptor).write_text("")
    tool(tools, name, code)
    result = run_policy(tmp_path, tools)
    assert result.returncode == code
    assert (tmp_path / "calls").read_text().splitlines() == [name]
    assert ("Quality Gates Complete" in result.stdout) == (code == 0)


def test_failed_task_does_not_fall_back_to_passing_npm(tmp_path):
    tools = tmp_path / "tools"
    tools.mkdir()
    (tmp_path / "Taskfile.yml").write_text("")
    (tmp_path / "package.json").write_text("{}")
    tool(tools, "task", 9)
    tool(tools, "npm")
    assert run_policy(tmp_path, tools).returncode == 9
    assert (tmp_path / "calls").read_text().splitlines() == ["task"]


@pytest.mark.parametrize("name,config", [("wup", "wup.yaml"), ("regix", "regix.yaml")])
def test_executed_optional_gate_failure_is_not_hidden(tmp_path, name, config):
    tools = tmp_path / "tools"
    tools.mkdir()
    (tmp_path / "pyproject.toml").write_text("")
    (tmp_path / config).write_text("")
    tool(tools, "pytest")
    tool(tools, name, 8)
    result = run_policy(tmp_path, tools)
    assert result.returncode != 0
    assert "Quality Gates Complete" not in result.stdout
    assert (tmp_path / "calls").read_text().splitlines() == ["pytest", name]


def test_plugin_failure_is_not_hidden(tmp_path):
    tools = tmp_path / "tools"
    tools.mkdir()
    (tmp_path / "pyproject.toml").write_text("")
    plugin = tmp_path / "plugins/koru-autopilot-vscode"
    plugin.mkdir(parents=True)
    (plugin / "package.json").write_text("{}")
    tool(tools, "pytest")
    tool(tools, "npm", 8)
    assert run_policy(tmp_path, tools).returncode != 0


def test_testql_failure_is_not_hidden(tmp_path):
    tools = tmp_path / "tools"
    tools.mkdir()
    (tmp_path / "pyproject.toml").write_text("")
    tool(tools, "pytest")
    tool(tools, "testql", 8)
    for name in ["find", "head"]:
        tool(tools, name)
    assert run_policy(tmp_path, tools).returncode != 0
