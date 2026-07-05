from __future__ import annotations

from pathlib import Path

from koru.configurator.render import _serve_command, render_shell_exports, render_text_summary
from koru.configurator.schema import ConfigureResult


def _result(config: dict, *, path: Path | None = None) -> ConfigureResult:
    return ConfigureResult(project=Path("/tmp/demo"), path=path or Path("/tmp/demo/.koru/config.json"), config=config)


def test_serve_command_defaults_when_no_serve_block() -> None:
    command = _serve_command({"project": "/p", "workspace": "/w"})
    assert command[:3] == ["koru", "serve", "--project"]
    assert "/p" in command
    assert "/w" in command
    assert "8765" in command  # default port
    # no lan/host/auto-port flags
    assert "--lan" not in command
    assert "--host" not in command
    assert "--auto-port" not in command


def test_serve_command_lan_suppresses_host() -> None:
    command = _serve_command({"serve": {"lan": True, "host": "10.0.0.1", "port": 9000}})
    assert "--lan" in command
    assert "--host" not in command  # host dropped when lan is set
    assert "9000" in command


def test_serve_command_emits_host_when_not_lan() -> None:
    command = _serve_command({"serve": {"host": "127.0.0.1", "port": 8765}})
    assert "--host" in command
    assert "127.0.0.1" in command
    assert "--lan" not in command


def test_serve_command_auto_port_flag() -> None:
    command = _serve_command({"serve": {"auto_port": True}})
    assert "--auto-port" in command


def test_serve_command_falls_back_to_dot_when_project_missing() -> None:
    command = _serve_command({})
    assert "." in command  # project defaults to "."


def test_render_text_summary_surfaces_key_fields() -> None:
    config = {
        "project": "/tmp/demo",
        "workspace": "/tmp/ws",
        "ide": "windsurf",
        "queue_name": "ops",
        "serve": {"host": "127.0.0.1", "port": 8766, "lan": False},
    }
    text = render_text_summary(_result(config, path=Path("/tmp/demo/.koru/config.json")))
    assert "saved /tmp/demo/.koru/config.json" in text
    assert "project: /tmp/demo" in text
    assert "workspace: /tmp/ws" in text
    assert "ide: windsurf" in text
    assert "queue: ops" in text
    assert "port=8766" in text
    assert "koru serve" in text


def test_render_shell_exports_basic_set() -> None:
    rendered = render_shell_exports(
        {
            "project": "/tmp/demo",
            "workspace": "/tmp/ws",
            "ide": "vscode",
            "queue_name": "default",
            "serve": {"host": "127.0.0.1", "port": 8766, "auto_port": True, "lan": False},
        }
    )
    lines = rendered.splitlines()
    assert "export KORU_PROJECT=/tmp/demo" in lines
    assert "export KORU_AUTOPILOT_INSTANCE=vscode" in lines
    assert "export KORU_SERVE_PORT=8766" in lines
    assert "export KORU_SERVE_AUTO_PORT=1" in lines
    assert not any(line.startswith("export KORU_SERVE_LAN=") for line in lines)
    assert any(line.startswith("# koru serve") for line in lines)


def test_render_shell_exports_lan_flag_when_lan_enabled() -> None:
    rendered = render_shell_exports({"serve": {"lan": True, "port": 8765}})
    lines = rendered.splitlines()
    assert "export KORU_SERVE_LAN=1" in lines


def test_render_shell_exports_shell_quotes_special_chars() -> None:
    rendered = render_shell_exports(
        {"project": "/tmp/a b", "queue_name": "weird;rm", "serve": {"port": 8765}}
    )
    # shlex.quote wraps values with spaces / shell metacharacters
    assert "export KORU_PROJECT='/tmp/a b'" in rendered.splitlines()
    assert "export KORU_QUEUE_NAME='weird;rm'" in rendered.splitlines()
