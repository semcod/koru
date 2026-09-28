"""Unit tests for DockerSandboxRunner."""

from pathlib import Path

from koru.autonomy.docker_sandbox import DockerSandboxRunner, SandboxConfig
from koru.autonomy.process_uri import ProcessUri


def test_build_docker_cmd_defaults():
    runner = DockerSandboxRunner()
    cmd = runner.build_docker_cmd(["echo", "hello"])
    assert cmd[0] == "docker"
    assert cmd[1] == "run"
    assert "--rm" in cmd
    assert "--memory=1g" in cmd
    assert "--cpus=2.0" in cmd
    assert "python:3.12-slim" in cmd
    assert cmd[-2:] == ["echo", "hello"]


def test_build_docker_cmd_with_mount_and_env():
    config = SandboxConfig(network_enabled=False, memory_limit="512m")
    runner = DockerSandboxRunner(config)
    mount = Path("/tmp/test-mount")
    cmd = runner.build_docker_cmd(
        "ls -la",
        workspace_mount=mount,
        env_vars={"API_KEY": "secret123"},
    )
    assert "--network=none" in cmd
    assert "--memory=512m" in cmd
    assert "-v" in cmd
    assert "-e" in cmd
    assert "API_KEY=secret123" in cmd


def test_execute_uri_sandbox_dry_run():
    runner = DockerSandboxRunner()
    uri = ProcessUri.parse("sandbox://run?cmd=pytest")
    res = runner.execute_uri(uri, dry_run=True)
    assert res.exit_code == 0
    assert "[dry-run]" in res.stdout
    assert "pytest" in res.command


def test_execute_uri_pypi_dry_run():
    runner = DockerSandboxRunner()
    uri = ProcessUri.parse("pypi://ruff/check")
    res = runner.execute_uri(uri, {"args": "--fix"}, dry_run=True)
    assert res.exit_code == 0
    assert "[dry-run]" in res.stdout
    assert any("pip install --no-cache-dir ruff && check --fix" in arg for arg in res.command)
