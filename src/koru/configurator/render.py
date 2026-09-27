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


def render_config_table(config: dict[str, Any]) -> str:
    """Render an ASCII/Unicode table showing current project configuration."""
    serve = config.get("serve") if isinstance(config.get("serve"), dict) else {}
    
    # Feature states
    features: list[str] = []
    for feat in ("vision", "mesh", "browse", "sandbox"):
        val = config.get(feat)
        is_on = val.get("enabled", False) if isinstance(val, dict) else False
        features.append(f"{feat}: {'ON' if is_on else 'off'}")
    features_str = ", ".join(features)

    models = config.get("models") if isinstance(config.get("models"), dict) else {}
    model_default = str(models.get("default") or "auto")
    model_simple = str(models.get("simple") or "glm5.3-flash")

    rows = [
        ("project", str(config.get("project") or ".")),
        ("workspace", str(config.get("workspace") or ".")),
        ("ide", str(config.get("ide") or "auto")),
        ("llm default", model_default),
        ("llm simple (flash)", model_simple),
        ("queue", str(config.get("queue_name") or "default")),
        ("dashboard host", str(serve.get("host") or "127.0.0.1")),
        ("dashboard port", str(serve.get("port") or 8765)),
        ("lan", "True" if serve.get("lan") else "False"),
        ("auto_port", "True" if serve.get("auto_port") else "False"),
        ("schema", str(config.get("schema") or "koru.config/v1")),
        ("features (v2)", features_str),
    ]

    max_key_len = max(len(r[0]) for r in rows)
    max_val_len = max(len(r[1]) for r in rows)
    width = max(max_key_len + max_val_len + 7, 44)

    border_top = "┌" + "─" * (width - 2) + "┐"
    border_mid = "├" + "─" * (max_key_len + 2) + "┬" + "─" * (width - max_key_len - 5) + "┤"
    border_bot = "└" + "─" * (max_key_len + 2) + "┴" + "─" * (width - max_key_len - 5) + "┘"
    title_line = f"│ {'KORU CONFIGURATION':^{width - 4}} │"

    lines = [border_top, title_line, border_mid]
    for key, val in rows:
        val_padded = val.ljust(width - max_key_len - 6)
        lines.append(f"│ {key:<{max_key_len}} │ {val_padded} │")
    lines.append(border_bot)
    return "\n".join(lines)
