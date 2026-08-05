"""Interactive ``koru configure`` prompter and project-config builder."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

from koruide.ide import autopilot_ide_choices, normalize_ide_id

from koru.configurator.schema import CONFIG_SCHEMA, ConfigureResult, _ConfigureValues
from koru.configurator.store import load_project_config, save_project_config


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
