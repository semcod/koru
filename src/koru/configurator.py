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


CONFIG_SCHEMA_V1 = "koru.config/v1"
CONFIG_SCHEMA_V2 = "koru.config/v2"
CONFIG_SCHEMA = CONFIG_SCHEMA_V1
CONFIG_REL_PATH = Path(".koru") / "config.json"


@dataclass(frozen=True)
class ConfigureResult:
    project: Path
    path: Path
    config: dict[str, Any]


@dataclass(frozen=True)
class _ConfigureValues:
    workspace: str
    ide: str
    queue_name: str
    host: str
    port: int
    lan: bool
    auto_port: bool


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


def default_v2_feature_sections() -> dict[str, Any]:
    """Disabled-by-default sections for observation mesh (schema v2)."""
    return {
        "vision": {
            "enabled": False,
            "interval_seconds": 30,
            "format": "webp",
            "monitors": "all",
            "windows": [],
            "redact": [r"Bearer\s+\S+", r"sk-[A-Za-z0-9]{20,}"],
        },
        "mesh": {
            "enabled": False,
            "role": "peer",
            "expose": "loopback",
            "psk_path": ".koru/keys/mesh.hmac",
            "relay_url": None,
            "discovery": "mdns",
        },
        "browse": {
            "enabled": False,
            "targets": [],
            "autoinstall": True,
            "native_messaging_host": ".koru/keys/native-host.json",
        },
        "delegate": {
            "accept": [],
            "policy_path": ".koru/policies/delegate.yaml",
        },
        "sandbox": {
            "enabled": False,
            "engine": "clonebox",
            "profile": "browse-chrome",
        },
    }


def merge_v2_feature_sections(config: dict[str, Any]) -> dict[str, Any]:
    """Return *config* with v2 feature keys filled from defaults (no overwrite)."""
    merged = dict(config)
    for key, defaults in default_v2_feature_sections().items():
        if key not in merged:
            merged[key] = defaults
            continue
        current = merged.get(key)
        if not isinstance(current, dict):
            merged[key] = defaults
            continue
        section = dict(defaults)
        section.update(current)
        merged[key] = section
    return merged


def migrate_project_config(project: Path) -> ConfigureResult:
    """Upgrade ``.koru/config.json`` to schema v2 (idempotent, no side effects)."""
    project = project.expanduser().resolve()
    previous = load_project_config(project)
    if not previous:
        msg = "no .koru/config.json — run koru configure first"
        raise ValueError(msg)
    now = datetime.now(UTC).isoformat()
    config = merge_v2_feature_sections(previous)
    config["schema"] = CONFIG_SCHEMA_V2
    config["updated_at"] = now
    path = save_project_config(project, config)
    return ConfigureResult(project=project, path=path, config=config)


_TOGGLEABLE_FEATURES: tuple[str, ...] = ("vision", "mesh", "browse", "sandbox")


def toggle_feature_sections(
    project: Path,
    *,
    enable: tuple[str, ...] = (),
    disable: tuple[str, ...] = (),
) -> ConfigureResult:
    """Flip ``enabled`` on/off for v2 feature sections (vision/mesh/browse/sandbox)."""
    project = project.expanduser().resolve()
    previous = load_project_config(project)
    if not previous:
        msg = "no .koru/config.json — run koru configure first"
        raise ValueError(msg)
    config = merge_v2_feature_sections(previous)
    config["schema"] = CONFIG_SCHEMA_V2
    for name in enable:
        if name not in _TOGGLEABLE_FEATURES:
            msg = f"unknown feature {name!r}; expected one of {_TOGGLEABLE_FEATURES}"
            raise ValueError(msg)
        config[name] = {**config.get(name, {}), "enabled": True}
    for name in disable:
        if name not in _TOGGLEABLE_FEATURES:
            msg = f"unknown feature {name!r}; expected one of {_TOGGLEABLE_FEATURES}"
            raise ValueError(msg)
        config[name] = {**config.get(name, {}), "enabled": False}
    config["updated_at"] = datetime.now(UTC).isoformat()
    path = save_project_config(project, config)
    return ConfigureResult(project=project, path=path, config=config)


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


def _previous_serve_config(previous: dict[str, Any]) -> dict[str, Any]:
    serve = previous.get("serve")
    return serve if isinstance(serve, dict) else {}


def _default_workspace_value(
    *,
    project: Path,
    previous: dict[str, Any],
    workspace: Path | None,
) -> str:
    raw = workspace or Path(str(previous.get("workspace") or project.parent))
    return str(raw.expanduser().resolve())


def _default_serve_values(
    *,
    previous_serve: dict[str, Any],
    host: str | None,
    port: int | None,
    lan: bool | None,
    auto_port: bool | None,
) -> tuple[str, int, bool, bool]:
    lan_value = bool(previous_serve.get("lan")) if lan is None else lan
    host_default = str(previous_serve.get("host") or ("0.0.0.0" if lan_value else "127.0.0.1"))
    port_value = int(port if port is not None else previous_serve.get("port") or 8765)
    auto_port_value = bool(previous_serve.get("auto_port", True)) if auto_port is None else auto_port
    return host or host_default, port_value, lan_value, auto_port_value


def _default_configure_values(
    *,
    project: Path,
    previous: dict[str, Any],
    workspace: Path | None,
    ide: str | None,
    queue_name: str | None,
    host: str | None,
    port: int | None,
    lan: bool | None,
    auto_port: bool | None,
) -> _ConfigureValues:
    previous_serve = _previous_serve_config(previous)
    workspace_value = _default_workspace_value(project=project, previous=previous, workspace=workspace)
    ide_value = normalize_ide_id(ide or str(previous.get("ide") or "auto")) or "auto"
    queue_value = queue_name or str(previous.get("queue_name") or "default")
    host_value, port_value, lan_value, auto_port_value = _default_serve_values(
        previous_serve=previous_serve,
        host=host,
        port=port,
        lan=lan,
        auto_port=auto_port,
    )
    return _ConfigureValues(
        workspace=workspace_value,
        ide=ide_value,
        queue_name=queue_value,
        host=host_value,
        port=port_value,
        lan=lan_value,
        auto_port=auto_port_value,
    )


def _prompt_configure_values(
    values: _ConfigureValues,
    prompter: ShellPrompter,
) -> _ConfigureValues:
    workspace_value = str(Path(prompter.ask_text("Workspace root", default=values.workspace)).expanduser().resolve())
    ide_choices = autopilot_ide_choices()
    ide_value = prompter.ask_choice(
        "IDE lane",
        choices=ide_choices,
        default=values.ide if values.ide in ide_choices else "auto",
    )
    queue_value = prompter.ask_text("Default queue", default=values.queue_name)
    lan_value = prompter.ask_yes_no("Expose dashboard on LAN", default=values.lan)
    host_value = prompter.ask_text("Dashboard host", default="0.0.0.0" if lan_value else values.host)
    raw_port = prompter.ask_text("Dashboard port", default=str(values.port))
    auto_port_value = prompter.ask_yes_no("Auto-pick next port when busy", default=values.auto_port)
    return _ConfigureValues(
        workspace=workspace_value,
        ide=ide_value,
        queue_name=queue_value,
        host=host_value,
        port=int(raw_port),
        lan=lan_value,
        auto_port=auto_port_value,
    )


def _build_project_config(
    *,
    project: Path,
    previous: dict[str, Any],
    values: _ConfigureValues,
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    return {
        "schema": CONFIG_SCHEMA,
        "project": str(project),
        "workspace": values.workspace,
        "ide": values.ide,
        "queue_name": values.queue_name,
        "serve": {
            "host": values.host,
            "port": values.port,
            "lan": bool(values.lan),
            "auto_port": bool(values.auto_port),
        },
        "created_at": previous.get("created_at") or now,
        "updated_at": now,
    }


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
    prompter = ShellPrompter(stream_in=stream_in, stream_out=stream_out)
    values = _default_configure_values(
        project=project,
        previous=previous,
        workspace=workspace,
        ide=ide,
        queue_name=queue_name,
        host=host,
        port=port,
        lan=lan,
        auto_port=auto_port,
    )

    if interactive:
        values = _prompt_configure_values(values, prompter)

    config = _build_project_config(project=project, previous=previous, values=values)
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
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Upgrade existing .koru/config.json to schema v2 (adds disabled feature sections).",
    )
    parser.add_argument(
        "--enable",
        action="append",
        default=[],
        help="Enable a v2 feature section (vision, mesh, browse, sandbox). Repeatable.",
    )
    parser.add_argument(
        "--disable",
        action="append",
        default=[],
        help="Disable a v2 feature section. Repeatable.",
    )
    parser.add_argument("--format", choices=("text", "json", "shell"), default="text")
    return parser


def _split_feature_list(values: list[str]) -> tuple[str, ...]:
    out: list[str] = []
    for raw in values:
        for item in str(raw).split(","):
            stripped = item.strip().lower()
            if stripped:
                out.append(stripped)
    return tuple(out)


def _emit_configure_output(result: ConfigureResult, fmt: str, *, text: str | None = None) -> None:
    if fmt == "json":
        print(json.dumps(result.config, ensure_ascii=False, indent=2, sort_keys=True))
        return
    if fmt == "shell":
        print(render_shell_exports(result.config))
        return
    print(text or render_text_summary(result))


def _configure_migrate(args: argparse.Namespace) -> int:
    try:
        result = migrate_project_config(args.project)
    except ValueError as exc:
        print(f"koru configure: {exc}", file=sys.stderr)
        return 2
    summary = f"koru configure: migrated {result.path} -> {CONFIG_SCHEMA_V2}"
    _emit_configure_output(result, args.format, text=summary)
    return 0


def _configure_toggle(args: argparse.Namespace) -> int:
    enable = _split_feature_list(args.enable)
    disable = _split_feature_list(args.disable)
    try:
        result = toggle_feature_sections(args.project, enable=enable, disable=disable)
    except ValueError as exc:
        print(f"koru configure: {exc}", file=sys.stderr)
        return 2
    changed = ", ".join(
        f"+{name}" for name in enable
    ) + (", " if enable and disable else "") + ", ".join(f"-{name}" for name in disable)
    summary = f"koru configure: features {changed} in {result.path}"
    _emit_configure_output(result, args.format, text=summary)
    return 0


def _configure_write(args: argparse.Namespace) -> int:
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
    _emit_configure_output(result, args.format)
    return 0


def configure_main(argv: list[str] | None = None) -> int:
    args = build_configure_parser().parse_args(argv)
    if args.migrate:
        return _configure_migrate(args)
    if args.enable or args.disable:
        return _configure_toggle(args)
    return _configure_write(args)


__all__ = [
    "CONFIG_REL_PATH",
    "CONFIG_SCHEMA",
    "CONFIG_SCHEMA_V1",
    "CONFIG_SCHEMA_V2",
    "ConfigureResult",
    "ShellPrompter",
    "build_configure_parser",
    "configure_main",
    "configure_project",
    "default_v2_feature_sections",
    "load_project_config",
    "merge_v2_feature_sections",
    "migrate_project_config",
    "render_shell_exports",
    "render_text_summary",
    "save_project_config",
    "toggle_feature_sections",
]
