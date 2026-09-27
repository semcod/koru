from __future__ import annotations

import json
from pathlib import Path

from koru.configurator import (
    CONFIG_SCHEMA_V2,
    apply_nl_config_command,
    configure_main,
    normalize_nl_text,
    render_config_table,
)


def _sample_config(project: Path) -> dict:
    return {
        "schema": CONFIG_SCHEMA_V2,
        "project": str(project),
        "workspace": str(project.parent),
        "ide": "windsurf",
        "queue_name": "default",
        "serve": {
            "host": "127.0.0.1",
            "port": 8765,
            "lan": False,
            "auto_port": True,
        },
        "vision": {"enabled": False},
        "mesh": {"enabled": False},
        "browse": {"enabled": False},
        "sandbox": {"enabled": False},
    }


def test_normalize_nl_text() -> None:
    assert normalize_nl_text("Zmień IDE na Cursor!") == "zmien ide na cursor"
    assert normalize_nl_text("Włącz LAN...") == "wlacz lan"
    assert normalize_nl_text("  port   na  9000  ") == "port na 9000"


def test_render_config_table(tmp_path: Path) -> None:
    cfg = _sample_config(tmp_path)
    table = render_config_table(cfg)
    assert "KORU CONFIGURATION" in table
    assert "windsurf" in table
    assert "8765" in table
    assert "127.0.0.1" in table
    assert "default" in table
    assert "vision: off" in table


def test_apply_nl_command_ide(tmp_path: Path) -> None:
    cfg = _sample_config(tmp_path)
    res = apply_nl_config_command(cfg, "zmień ide na cursor", tmp_path)
    assert res.success is True
    assert res.updated is True
    assert cfg["ide"] == "cursor"
    assert "cursor" in res.message


def test_apply_nl_command_port_and_host(tmp_path: Path) -> None:
    cfg = _sample_config(tmp_path)
    res_port = apply_nl_config_command(cfg, "port na 9090", tmp_path)
    assert res_port.success is True
    assert cfg["serve"]["port"] == 9090

    res_host = apply_nl_config_command(cfg, "host na 0.0.0.0", tmp_path)
    assert res_host.success is True
    assert cfg["serve"]["host"] == "0.0.0.0"


def test_apply_nl_command_lan_and_autoport(tmp_path: Path) -> None:
    cfg = _sample_config(tmp_path)
    res_lan = apply_nl_config_command(cfg, "włącz lan", tmp_path)
    assert res_lan.success is True
    assert cfg["serve"]["lan"] is True

    res_autoport = apply_nl_config_command(cfg, "wylacz auto-port", tmp_path)
    assert res_autoport.success is True
    assert cfg["serve"]["auto_port"] is False


def test_apply_nl_command_feature_toggle(tmp_path: Path) -> None:
    cfg = _sample_config(tmp_path)
    # Save seed config
    (tmp_path / ".koru").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".koru" / "config.json").write_text(json.dumps(cfg), encoding="utf-8")

    res_mesh = apply_nl_config_command(cfg, "wlacz mesh", tmp_path)
    assert res_mesh.success is True
    assert res_mesh.updated is True
    assert "+mesh" in res_mesh.message

    saved = json.loads((tmp_path / ".koru" / "config.json").read_text(encoding="utf-8"))
    assert saved["mesh"]["enabled"] is True


def test_cli_table_flag(tmp_path: Path, capsys) -> None:
    cfg = _sample_config(tmp_path)
    (tmp_path / ".koru").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".koru" / "config.json").write_text(json.dumps(cfg), encoding="utf-8")

    rc = configure_main(["--project", str(tmp_path), "--table"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "KORU CONFIGURATION" in out
    assert "windsurf" in out


def test_config_completer_candidates() -> None:
    from koru.configurator.shell_history import ConfigCompleter

    completer = ConfigCompleter()
    # Test base commands
    matches_ide = completer.get_candidates("ide")
    assert "ide na " in matches_ide

    # Test IDE lane candidates
    matches_cursor = completer.get_candidates("ide na cur")
    assert "ide na cursor" in matches_cursor

    # Test toggle candidates
    matches_toggle = completer.get_candidates("wlacz m")
    assert "wlacz mesh" in matches_toggle


def test_setup_config_shell_readline(tmp_path: Path) -> None:
    from koru.configurator.shell_history import setup_config_shell_readline

    cleanup = setup_config_shell_readline(tmp_path)
    # Even in headless/mock environments, returns a callable or None without raising
    if cleanup is not None:
        cleanup()


def test_apply_nl_multi_intent_batching(tmp_path: Path) -> None:
    cfg = _sample_config(tmp_path)
    command = "port na 9000 i ide na cursor i wlacz lan"
    res = apply_nl_config_command(cfg, command, tmp_path)

    assert res.success is True
    assert res.updated is True
    assert cfg["serve"]["port"] == 9000
    assert cfg["ide"] == "cursor"
    assert cfg["serve"]["lan"] is True
    assert "9000" in res.message
    assert "cursor" in res.message


def test_apply_nl_command_models(tmp_path: Path) -> None:
    cfg = _sample_config(tmp_path)
    res_def = apply_nl_config_command(cfg, "model na anthropic/claude-3.7-sonnet", tmp_path)
    assert res_def.success is True
    assert cfg["models"]["default"] == "anthropic/claude-3.7-sonnet"

    res_simple = apply_nl_config_command(cfg, "prosty model na glm5.3-flash", tmp_path)
    assert res_simple.success is True
    assert cfg["models"]["simple"] == "glm5.3-flash"
    assert "Flash" in res_simple.message



