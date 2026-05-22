"""Interactive shell configurator for project-local Koru details."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

from koruide.ide import autopilot_ide_choices, normalize_ide_id


CONFIG_SCHEMA = "koru.config/v1"
CONFIG_REL_PATH = Path(".koru") / "config.json"


@dataclass(frozen=True)
class ConfigureResult:
    project: Path
    path: Path
    config: dict[str, Any]


class ShellPrompter:
    """Small stdin/stdout prompter used by ``koru configure``."""

    def __init__(self, *, stream_in: TextIO = sys.stdin, stream_out: TextIO = sys.stdout) -> None:
        self._in = stream_in
        self._out = stream_out

    def _line(self, text: str) -> None:
        print(text, file=self._out, flush=True)

    def ask_text(self, prompt: str, *, default: str) -> str:
        suffix = f" [{default}]" if default else ""
        self._line(f"{prompt}{suffix}: ")
        raw = self._in.readline()
        if not raw:
            raise EOFError("configure cancelled (EOF on stdin)")
        value = raw.strip()
        return value or default

    def ask_yes_no(self, prompt: str, *, default: bool) -> bool:
        suffix = "[Y/n]" if default else "[y/N]"
        while True:
            self._line(f"{prompt} {suffix}: ")
            raw = self._in.readline()
            if not raw:
                raise EOFError("configure cancelled (EOF on stdin)")
            value = raw.strip().lower()
            if not value:
                return default
            if value in {"y", "yes", "t", "tak", "true", "1"}:
                return True
            if value in {"n", "no", "nie", "false", "0"}:
                return False
            self._line("  ! answer with y/n")

    def ask_choice(self, prompt: str, *, choices: tuple[str, ...], default: str) -> str:
        rendered = ", ".join(choices)
        while True:
            value = self.ask_text(f"{prompt} ({rendered})", default=default)
            normalized = normalize_ide_id(value) or value
            if normalized in choices:
                return normalized
            self._line(f"  ! choose one of: {rendered}")


def _config_path(project: Path) -> Path:
    return project.resolve() / CONFIG_REL_PATH


def load_project_config(project: Path) -> dict[str, Any]:
    path = _config_path(project)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_project_config(project: Path, config: dict[str, Any]) -> Path:
    path = _config_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _serve_command(config: dict[str, Any]) -> list[str]:
    serve = config.get("serve") if isinstance(config.get("serve"), dict) else {}
    command = [
        "koru",
        "serve",
        "--project",
        str(config.get("project") or "."),
        "--workspace",
        str(config.get("workspace") or "."),
        "--port",
        str(serve.get("port") or 8765),
    ]
    if serve.get("lan"):
        command.append("--lan")
    elif serve.get("host"):
        command.extend(["--host", str(serve.get("host"))])
    if serve.get("auto_port"):
        command.append("--auto-port")
    return command


def render_text_summary(result: ConfigureResult) -> str:
    serve = result.config.get("serve") if isinstance(result.config.get("serve"), dict) else {}
    command = " ".join(shlex.quote(part) for part in _serve_command(result.config))
    return "\n".join(
        [
            f"koru configure: saved {result.path}",
            f"  project: {result.config.get('project')}",
            f"  workspace: {result.config.get('workspace')}",
            f"  ide: {result.config.get('ide')}",
            f"  queue: {result.config.get('queue_name')}",
            f"  dashboard: host={serve.get('host')} port={serve.get('port')} lan={serve.get('lan')}",
            f"  run: {command}",
        ]
    )


def render_shell_exports(config: dict[str, Any]) -> str:
    serve = config.get("serve") if isinstance(config.get("serve"), dict) else {}
    values = {
        "KORU_PROJECT": str(config.get("project") or ""),
        "KORU_WORKSPACE": str(config.get("workspace") or ""),
        "KORU_AUTOPILOT_INSTANCE": str(config.get("ide") or "auto"),
        "KORU_QUEUE_NAME": str(config.get("queue_name") or "default"),
        "KORU_SERVE_HOST": str(serve.get("host") or "127.0.0.1"),
        "KORU_SERVE_PORT": str(serve.get("port") or 8765),
        "KORU_SERVE_AUTO_PORT": "1" if serve.get("auto_port") else "0",
    }
    if serve.get("lan"):
        values["KORU_SERVE_LAN"] = "1"
    lines = [f"export {key}={shlex.quote(value)}" for key, value in values.items()]
    lines.append("# " + " ".join(shlex.quote(part) for part in _serve_command(config)))
    return "\n".join(lines)


def configure_project(
    *,
    project: Path,
    workspace: Path | None = None,
    ide: str | None = None,
    queue_name: str | None = None,
    host: str | None = None,
    port: int | None = None,
    lan: bool | None = None,
    auto_port: bool | None = None,
    interactive: bool = True,
    stream_in: TextIO = sys.stdin,
    stream_out: TextIO = sys.stdout,
) -> ConfigureResult:
    project = project.expanduser().resolve()
    previous = load_project_config(project)
    previous_serve = previous.get("serve") if isinstance(previous.get("serve"), dict) else {}
    prompter = ShellPrompter(stream_in=stream_in, stream_out=stream_out)

    workspace_value = str(
        (workspace or Path(str(previous.get("workspace") or project.parent))).expanduser().resolve()
    )
    ide_value = normalize_ide_id(ide or str(previous.get("ide") or "auto")) or "auto"
    queue_value = queue_name or str(previous.get("queue_name") or "default")
    lan_value = bool(previous_serve.get("lan")) if lan is None else lan
    host_default = str(previous_serve.get("host") or ("0.0.0.0" if lan_value else "127.0.0.1"))
    host_value = host or host_default
    port_value = int(port if port is not None else previous_serve.get("port") or 8765)
    auto_port_value = bool(previous_serve.get("auto_port", True)) if auto_port is None else auto_port

    if interactive:
        workspace_value = str(Path(prompter.ask_text("Workspace root", default=workspace_value)).expanduser().resolve())
        ide_value = prompter.ask_choice(
            "IDE lane",
            choices=autopilot_ide_choices(),
            default=ide_value if ide_value in autopilot_ide_choices() else "auto",
        )
        queue_value = prompter.ask_text("Default queue", default=queue_value)
        lan_value = prompter.ask_yes_no("Expose dashboard on LAN", default=lan_value)
        host_value = prompter.ask_text("Dashboard host", default="0.0.0.0" if lan_value else host_value)
        raw_port = prompter.ask_text("Dashboard port", default=str(port_value))
        port_value = int(raw_port)
        auto_port_value = prompter.ask_yes_no("Auto-pick next port when busy", default=auto_port_value)

    now = datetime.now(UTC).isoformat()
    config = {
        "schema": CONFIG_SCHEMA,
        "project": str(project),
        "workspace": workspace_value,
        "ide": ide_value,
        "queue_name": queue_value,
        "serve": {
            "host": host_value,
            "port": port_value,
            "lan": bool(lan_value),
            "auto_port": bool(auto_port_value),
        },
        "created_at": previous.get("created_at") or now,
        "updated_at": now,
    }
    path = save_project_config(project, config)
    return ConfigureResult(project=project, path=path, config=config)


def build_configure_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru configure",
        description="Configure project-local Koru defaults from an interactive shell prompt.",
    )
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root to configure.")
    parser.add_argument("--workspace", type=Path, default=None, help="Workspace root for project discovery.")
    parser.add_argument("--ide", choices=autopilot_ide_choices(), default=None, help="Default IDE lane.")
    parser.add_argument("--queue-name", default=None, help="Default planfile queue name.")
    parser.add_argument("--host", default=None, help="Default dashboard bind host.")
    parser.add_argument("--port", type=int, default=None, help="Default dashboard port.")
    lan_group = parser.add_mutually_exclusive_group()
    lan_group.add_argument("--lan", dest="lan", action="store_true", default=None, help="Expose dashboard on LAN.")
    lan_group.add_argument("--no-lan", dest="lan", action="store_false", help="Keep dashboard local-only.")
    port_group = parser.add_mutually_exclusive_group()
    port_group.add_argument("--auto-port", dest="auto_port", action="store_true", default=None, help="Auto-pick a free dashboard port.")
    port_group.add_argument("--no-auto-port", dest="auto_port", action="store_false", help="Fail if dashboard port is busy.")
    parser.add_argument("--non-interactive", action="store_true", help="Write defaults/flags without prompting.")
    parser.add_argument("--format", choices=("text", "json", "shell"), default="text")
    return parser


def configure_main(argv: list[str] | None = None) -> int:
    args = build_configure_parser().parse_args(argv)
    try:
        result = configure_project(
            project=args.project,
            workspace=args.workspace,
            ide=args.ide,
            queue_name=args.queue_name,
            host=args.host,
            port=args.port,
            lan=args.lan,
            auto_port=args.auto_port,
            interactive=not args.non_interactive,
        )
    except (EOFError, ValueError) as exc:
        print(f"koru configure: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(result.config, ensure_ascii=False, indent=2, sort_keys=True))
    elif args.format == "shell":
        print(render_shell_exports(result.config))
    else:
        print(render_text_summary(result))
    return 0


__all__ = [
    "CONFIG_REL_PATH",
    "CONFIG_SCHEMA",
    "ConfigureResult",
    "ShellPrompter",
    "build_configure_parser",
    "configure_main",
    "configure_project",
    "load_project_config",
    "render_shell_exports",
    "render_text_summary",
    "save_project_config",
]