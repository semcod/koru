"""Docker Sandbox runner for isolated process execution.

Supports:
  - sandbox://run: Executes a command or script in an isolated Docker container with mounted workspace
  - pypi://<pkg>/<cmd>: Runs a package tool via uv/python in sandbox
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from koru.autonomy.process_uri import ProcessUri


@dataclass(frozen=True)
class SandboxConfig:
    """Configuration for Docker sandbox execution."""

    image: str = "python:3.12-slim"
    timeout_seconds: int = 120
    memory_limit: str = "1g"
    cpu_limit: str = "2.0"
    network_enabled: bool = True
    read_only_root: bool = False
    workdir: str = "/workspace"


@dataclass
class SandboxResult:
    """Outcome of sandbox execution."""

    exit_code: int
    stdout: str
    stderr: str
    command: list[str]
    duration_seconds: float = 0.0

    @property
    def is_success(self) -> bool:
        return self.exit_code == 0


class DockerSandboxRunner:
    """Executes tasks in ephemeral, secure Docker containers."""

    def __init__(self, default_config: SandboxConfig | None = None) -> None:
        self.config = default_config or SandboxConfig()

    def build_docker_cmd(
        self,
        command: list[str] | str,
        *,
        workspace_mount: Path | None = None,
        env_vars: dict[str, str] | None = None,
        image_override: str | None = None,
    ) -> list[str]:
        """Construct the 'docker run' argument list with security and isolation flags."""
        image = image_override or self.config.image
        cmd = [
            "docker",
            "run",
            "--rm",
            "--init",
            f"--memory={self.config.memory_limit}",
            f"--cpus={self.config.cpu_limit}",
            "-w",
            self.config.workdir,
        ]

        if not self.config.network_enabled:
            cmd.append("--network=none")

        if self.config.read_only_root:
            cmd.append("--read-only")

        if workspace_mount:
            resolved = workspace_mount.resolve()
            cmd.extend(["-v", f"{resolved}:{self.config.workdir}"])

        if env_vars:
            for k, v in env_vars.items():
                cmd.extend(["-e", f"{k}={v}"])

        cmd.append(image)

        if isinstance(command, str):
            cmd.extend(["sh", "-c", command])
        else:
            cmd.extend(command)

        return cmd

    def execute_uri(
        self,
        uri: ProcessUri,
        payload: dict[str, Any] | None = None,
        *,
        workspace_mount: Path | None = None,
        dry_run: bool = False,
    ) -> SandboxResult:
        """Execute a sandbox:// or pypi:// process URI."""
        payload = payload or {}

        if uri.scheme == "pypi":
            pkg = uri.domain
            tool = uri.action_or_resource or pkg
            extra_args = payload.get("args", "")
            # Run via uvx or python -m
            inner_cmd = f"pip install --no-cache-dir {pkg} && {tool} {extra_args}".strip()
            docker_cmd = self.build_docker_cmd(
                inner_cmd,
                workspace_mount=workspace_mount,
                env_vars=payload.get("env"),
            )
        elif uri.scheme == "sandbox":
            raw_command = payload.get("command") or uri.query_params.get("cmd") or "true"
            docker_cmd = self.build_docker_cmd(
                raw_command,
                workspace_mount=workspace_mount,
                env_vars=payload.get("env"),
                image_override=payload.get("image"),
            )
        else:
            raise ValueError(f"Unsupported sandbox scheme: '{uri.scheme}'")

        if dry_run:
            return SandboxResult(
                exit_code=0,
                stdout="[dry-run] " + " ".join(docker_cmd),
                stderr="",
                command=docker_cmd,
            )

        try:
            res = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
                check=False,
            )
            return SandboxResult(
                exit_code=res.returncode,
                stdout=res.stdout,
                stderr=res.stderr,
                command=docker_cmd,
            )
        except subprocess.TimeoutExpired as exc:
            return SandboxResult(
                exit_code=124,
                stdout=exc.stdout or "",
                stderr=f"Command timed out after {self.config.timeout_seconds}s",
                command=docker_cmd,
            )
        except Exception as exc:
            return SandboxResult(
                exit_code=1,
                stdout="",
                stderr=str(exc),
                command=docker_cmd,
            )
