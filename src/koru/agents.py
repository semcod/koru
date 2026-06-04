"""Detect and launch LLM/IDE agents available for a koru project."""


import importlib.metadata
import os
import platform
import shutil
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from koru.runtime import runtime_dir
from koru.semcod_tools import detect_semcod_tools
from koru.sllm_bridge import (
    autopilot_backend_for_shell_agent,
    detect_shell_agent_rows,
    is_shell_agent,
    launch_shell_agent,
)


def normalize_agent_lane_id(raw: str) -> str:
    """Lowercase slug safe for env / socket instance labels."""
    s = raw.strip().lower().replace(" ", "-")
    out = []
    for ch in s[:80]:
        if ch.isalnum() or ch in "-_":
            out.append(ch)
        elif ch not in " \t":
            out.append("-")
    slug = "".join(out).strip("-") or "lane"
    return slug


def autopilot_backend_for_agent_id(agent_id: str) -> str:
    """Autopilot transport for a lane (``KORU_AUTOPILOT_BACKEND`` /
    ``AgentOption.autopilot_backend``)."""
    norm = normalize_agent_lane_id(agent_id)
    if norm in {"openrouter"}:
        return "headless"
    shell_backend = autopilot_backend_for_shell_agent(norm)
    if shell_backend is not None:
        return shell_backend
    return "plugin_socket"


@dataclass(frozen=True)
class AgentOption:
    id: str
    label: str
    available: bool
    launchable: bool
    command: str | None = None
    reason: str = ""
    project_hint: bool = False
    autopilot_backend: str = "plugin_socket"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "available": self.available,
            "launchable": self.launchable,
            "command": self.command,
            "reason": self.reason,
            "project_hint": self.project_hint,
            "autopilot_backend": self.autopilot_backend,
        }


def _which(command: str) -> str | None:
    return shutil.which(command)


def _marker(project: Path, *parts: str) -> bool:
    return (project.joinpath(*parts)).exists()


def _koru_package_version() -> str:
    try:
        return importlib.metadata.version("koru")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _detect_gui_agent_commands() -> dict[str, str | None]:
    """Detect GUI IDE commands that still belong to Koru."""
    return {
        "windsurf": _which("windsurf"),
        "cursor": _which("cursor"),
    }


def _build_cli_agent_option(
    agent_id: str,
    label: str,
    cmd: str | None,
    project: Path,
    marker_name: str | None = None,
) -> AgentOption:
    """Build AgentOption for CLI-based agents."""
    project_hint = _marker(project, marker_name) if marker_name else None
    available = bool(cmd or project_hint)
    launchable = bool(cmd)

    if marker_name and project_hint:
        reason = (
            f"{label} CLI detected."
            if cmd
            else f"{label} project config detected; open the prompt in {label} manually."
        )
    else:
        reason = f"{label} CLI detected in PATH." if cmd else f"{label} CLI is not in PATH."

    return AgentOption(
        id=agent_id,
        label=label,
        available=available,
        launchable=launchable,
        command=cmd,
        project_hint=project_hint,
        autopilot_backend=autopilot_backend_for_agent_id(agent_id),
        reason=reason,
    )


def _build_agent_option_from_mapping(row: Mapping[str, Any]) -> AgentOption:
    command = row.get("command")
    return AgentOption(
        id=str(row["id"]),
        label=str(row["label"]),
        available=bool(row["available"]),
        launchable=bool(row["launchable"]),
        command=command if isinstance(command, str) else None,
        reason=str(row.get("reason") or ""),
        project_hint=bool(row.get("project_hint")),
        autopilot_backend=str(row.get("autopilot_backend") or "plugin_socket"),
    )


def detect_agent_options(project: Path) -> list[AgentOption]:
    """Return known LLM/IDE lanes ordered by koru preference."""
    project = project.resolve()
    commands = _detect_gui_agent_commands()
    shell_agents = [
        _build_agent_option_from_mapping(row)
        for row in detect_shell_agent_rows()
    ]

    openrouter_ready = bool(os.getenv("OPENROUTER_API_KEY"))
    antigravity_home = Path.home() / ".gemini" / "antigravity"
    antigravity_ready = bool(os.getenv("ANTIGRAVITY_AGENT")) or antigravity_home.exists()

    return [
        AgentOption(
            id="antigravity",
            label="Antigravity Agent",
            available=antigravity_ready,
            launchable=False,
            command=None,
            autopilot_backend=autopilot_backend_for_agent_id("antigravity"),
            reason=(
                "Antigravity runtime detected; operating natively within context."
                if antigravity_ready
                else "Antigravity environment not found."
            ),
        ),
        *shell_agents,
        _build_cli_agent_option("cursor", "Cursor", commands["cursor"], project, ".cursor"),
        _build_cli_agent_option("windsurf", "Windsurf", commands["windsurf"], project, ".windsurf"),
        AgentOption(
            id="openrouter",
            label="OpenRouter automation lane",
            available=openrouter_ready,
            launchable=False,
            command=None,
            autopilot_backend=autopilot_backend_for_agent_id("openrouter"),
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
            _marker(project, "testql-testing", "scenarios") or _marker(project, "testql-scenarios")
        ),
    }
    return {
        "cwd": str(project),
        "name": project.name,
        "python": sys.version.split()[0],
        "koru": {
            "version": _koru_package_version(),
            "executable": shutil.which("koru") or sys.argv[0],
        },
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


# IDE id passed to ``koru autonomous up --autopilot-ide`` / ``koru autopilot drive --ide``.
_LANE_AUTOPILOT_IDE: dict[str, str] = {
    "antigravity": "antigravity",
    "cursor": "cursor",
    "windsurf": "windsurf",
    "vscode": "vscode",
    "vscodium": "vscodium",
    "jetbrains": "jetbrains",
    "zed": "zed",
    "openrouter": "auto",
}


def agent_lane_environment(agent_id: str) -> dict[str, str]:
    """Recommended env for koru autopilot + queue when sharing one machine across lanes.

    Export these (see ``koru agent --env-exports``) in each IDE / terminal profile
    so Unix sockets, actors, and drive targets stay isolated.
    """
    norm = normalize_agent_lane_id(agent_id)
    ide = _LANE_AUTOPILOT_IDE.get(norm)
    if ide is None and is_shell_agent(norm):
        ide = "auto"
    if ide is None:
        ide = "auto"
    actor = f"koru-{norm}"
    env: dict[str, str] = {
        "KORU_AUTOPILOT_INSTANCE": norm,
        "KORU_SUGGESTED_QUEUE_ACTOR": actor,
        "KORU_AUTOPILOT_IDE": ide,
        "KORU_AUTOPILOT_BACKEND": autopilot_backend_for_agent_id(agent_id),
    }
    return env


def format_agent_lane_exports(env: dict[str, str]) -> str:
    """POSIX ``export`` lines for eval in bash/zsh."""

    def _q(val: str) -> str:
        return val.replace("'", "'\"'\"'")

    lines = [
        "# Generated by `koru agent --env-exports`; isolates autopilot socket + queue actor.",
    ]
    for key in sorted(env.keys()):
        lines.append(f"export {key}='{_q(env[key])}'")
    exports = "\n".join(lines)
    return f"{exports}\n"


def launch_agent(agent: AgentOption, project: Path, prompt: str) -> int:
    """Launch an agent CLI from the project root after saving the prompt."""
    prompt_path = save_agent_prompt(project, prompt)
    if agent.autopilot_backend == "sllm_shell" and is_shell_agent(agent.id):
        if not agent.launchable or not agent.command:
            print(f"koru agent: {agent.label} is not launchable from PATH.")
            print(f"Prompt saved: {prompt_path}")
            return 2
        try:
            return launch_shell_agent(
                agent_id=agent.id,
                project=project,
                prompt=prompt,
                command=agent.command,
            )
        except ImportError as exc:
            print("koru agent: missing shell LLM plugin; install with `pip install fullm`.")
            print(f"koru agent: import error: {exc}")
            print(f"Prompt saved: {prompt_path}")
            return 2
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
