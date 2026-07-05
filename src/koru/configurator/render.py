"""Render configure results as a text summary or shell exports."""

from __future__ import annotations

import shlex
from typing import Any

from koru.configurator.schema import ConfigureResult


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
