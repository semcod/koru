"""Detect and launch LLM/IDE agents available for a koru project."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .runtime import runtime_dir
from .semcod_tools import detect_semcod_tools


@dataclass(frozen=True)
class AgentOption:
    id: str
    label: str
    available: bool
    launchable: bool
    command: str | None = None
    reason: str = ""
    project_hint: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "available": self.available,
            "launchable": self.launchable,
            "command": self.command,
            "reason": self.reason,
            "project_hint": self.project_hint,
        }


def _which(command: str) -> str | None:
    return shutil.which(command)


def _marker(project: Path, *parts: str) -> bool:
    return (project.joinpath(*parts)).exists()


def detect_agent_options(project: Path) -> list[AgentOption]:
    """Return known LLM/IDE lanes ordered by koru preference."""
    project = project.resolve()
    windsurf_cmd = _which("windsurf")
    cursor_cmd = _which("cursor")
    claude_cmd = _which("claude")
    aider_cmd = _which("aider")
    codex_cmd = _which("codex")
    openrouter_ready = bool(os.getenv("OPENROUTER_API_KEY"))
    antigravity_ready = bool(os.getenv("ANTIGRAVITY_AGENT"))

    return [
        AgentOption(
            id="antigravity",
            label="Antigravity Agent",
            available=antigravity_ready,
            launchable=False,
            command=None,
            reason=(
                "Antigravity runtime detected; operating natively within context."
                if antigravity_ready
                else "Antigravity environment not found."
            ),
        ),
        AgentOption(
            id="claude-code",
            label="Claude Code",
            available=bool(claude_cmd),
            launchable=bool(claude_cmd),
            command=claude_cmd,
            reason=(
                "Claude Code CLI detected in PATH."
                if claude_cmd
                else "Install Claude Code CLI to launch it from koru."
            ),
        ),
        AgentOption(
            id="codex",
            label="Codex CLI",
            available=bool(codex_cmd),
            launchable=bool(codex_cmd),
            command=codex_cmd,
            reason="Codex CLI detected in PATH." if codex_cmd else "Codex CLI is not in PATH.",
        ),
        AgentOption(
            id="cursor",
            label="Cursor",
            available=bool(cursor_cmd or _marker(project, ".cursor")),
            launchable=bool(cursor_cmd),
            command=cursor_cmd,
            project_hint=_marker(project, ".cursor"),
            reason=(
                "Cursor CLI detected."
                if cursor_cmd
                else "Cursor project config detected; open the prompt in Cursor manually."
            ),
        ),
        AgentOption(
            id="windsurf",
            label="Windsurf",
            available=bool(windsurf_cmd or _marker(project, ".windsurf")),
            launchable=bool(windsurf_cmd),
            command=windsurf_cmd,
            project_hint=_marker(project, ".windsurf"),
            reason=(
                "Windsurf CLI detected."
                if windsurf_cmd
                else "Windsurf project rules detected; paste the prompt into Windsurf."
            ),
        ),
        AgentOption(
            id="aider",
            label="aider",
            available=bool(aider_cmd),
            launchable=bool(aider_cmd),
            command=aider_cmd,
            reason="aider detected in PATH." if aider_cmd else "aider is not in PATH.",
        ),
        AgentOption(
            id="openrouter",
            label="OpenRouter automation lane",
            available=openrouter_ready,
            launchable=False,
            command=None,
            reason=(
                "OPENROUTER_API_KEY is set; executor.kind=llm can run headless."
                if openrouter_ready
                else "OPENROUTER_API_KEY is not set."
            ),
        ),
    ]


def detect_project_environment(project: Path) -> dict[str, Any]:
    """Best-effort, read-only fingerprint of the current project."""
    project = project.resolve()
    markers = {
        "git": _marker(project, ".git"),
        "planfile": _marker(project, ".planfile", "config.yaml"),
        "koru_policy": _marker(project, ".planfile", ".koru", "policy.yaml"),
        "pyproject": _marker(project, "pyproject.toml"),
        "package_json": _marker(project, "package.json"),
        "taskfile": _marker(project, "Taskfile.yml") or _marker(project, "Taskfile.yaml"),
        "makefile": _marker(project, "Makefile"),
        "docker_compose": any(project.glob("docker-compose*.yml"))
        or any(project.glob("docker-compose*.yaml")),
        "windsurf_rules": _marker(project, ".windsurf", "rules.md"),
        "cursor_rules": _marker(project, ".cursor"),
        # On-change gate triad — surfaced in the brief's "On-change gates"
        # section so the agent immediately sees which packages are wired
        # to validate the project on every file save / pre-complete check.
        "wup_yaml": _marker(project, "wup.yaml"),
        "regix_yaml": _marker(project, "regix.yaml"),
        "testql_scenarios": (
            _marker(project, "testql-testing", "scenarios")
            or _marker(project, "testql-scenarios")
        ),
    }
    return {
        "cwd": str(project),
        "name": project.name,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "markers": markers,
    }


def detect_agent_environment(project: Path) -> dict[str, Any]:
    """Combined environment block embedded in the LLM handoff."""
    agents = detect_agent_options(project)
    recommended = next((agent for agent in agents if agent.available), None)
    semcod_tools = detect_semcod_tools(project)
    return {
        "project": detect_project_environment(project),
        "llm_agents": [agent.to_dict() for agent in agents],
        "recommended_agent": recommended.to_dict() if recommended else None,
        "semcod_tools": [tool.to_dict() for tool in semcod_tools],
    }


def select_agent(
    agents: list[AgentOption],
    *,
    agent_id: str | None = None,
    interactive: bool = True,
) -> AgentOption | None:
    candidates = [agent for agent in agents if agent.available]
    if agent_id:
        return next((agent for agent in agents if agent.id == agent_id), None)
    if not candidates:
        return None
    launchable = [agent for agent in candidates if agent.launchable]
    if len(launchable) <= 1 or not interactive:
        return (launchable or candidates)[0]

    print("Multiple launchable agents detected:")
    for index, agent in enumerate(launchable, start=1):
        print(f"  {index}. {agent.label} ({agent.id})")
    choice = input("Select agent number: ").strip()
    try:
        return launchable[int(choice) - 1]
    except (ValueError, IndexError):
        return None


def save_agent_prompt(project: Path, prompt: str) -> Path:
    prompts = runtime_dir(project) / "prompts"
    prompts.mkdir(parents=True, exist_ok=True)
    path = prompts / "latest-agent-prompt.md"
    path.write_text(prompt, encoding="utf-8")
    return path


def launch_agent(agent: AgentOption, project: Path, prompt: str) -> int:
    """Launch an agent CLI from the project root after saving the prompt."""
    prompt_path = save_agent_prompt(project, prompt)
    if not agent.launchable or not agent.command:
        print(f"koru agent: {agent.label} is not launchable from PATH.")
        print(f"Prompt saved: {prompt_path}")
        return 2
    print(f"koru agent: launching {agent.label}")
    print(f"Prompt saved: {prompt_path}")
    print("Open that prompt in the agent if its CLI starts an interactive session.")
    try:
        return subprocess.call([agent.command], cwd=project)
    except OSError as exc:
        print(f"koru agent: failed to launch {agent.label}: {exc}")
        return 1
