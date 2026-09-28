"""Behavior tests for NL config control (PLF-099)."""

from __future__ import annotations

from pathlib import Path

from koru.configurator import (
    CONFIG_SCHEMA_V2,
    apply_nl_config_command,
    normalize_nl_text,
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
        "models": {
            "default": "gemini-3.8-flash",
            "simple": "gemini-2.5-flash",
        },
        "vision": {"enabled": False},
        "mesh": {"enabled": False},
        "browse": {"enabled": False},
        "sandbox": {"enabled": False},
    }


def test_normalize_nl_text_clean() -> None:
    assert normalize_nl_text("Zmień IDE na Cursor!") == "zmien ide na cursor"
    assert normalize_nl_text("Włącz LAN...") == "wlacz lan"
    assert normalize_nl_text("  port   na  9000  ") == "port na 9000"


def test_apply_single_ide_command(tmp_path: Path) -> None:
    cfg = _sample_config(tmp_path)
    res = apply_nl_config_command(cfg, "ide na cursor", tmp_path)
    assert res.success is True
    assert res.updated is True
    assert cfg["ide"] == "cursor"


def test_apply_single_port_and_host_commands(tmp_path: Path) -> None:
    cfg = _sample_config(tmp_path)
    res = apply_nl_config_command(cfg, "port na 9090", tmp_path)
    assert res.success is True
    assert cfg["serve"]["port"] == 9090

    res_host = apply_nl_config_command(cfg, "host na 0.0.0.0", tmp_path)
    assert res_host.success is True
    assert cfg["serve"]["host"] == "0.0.0.0"


def test_apply_model_commands(tmp_path: Path) -> None:
    cfg = _sample_config(tmp_path)
    res_simple = apply_nl_config_command(cfg, "prosty model na glm-5.3-flash", tmp_path)
    assert res_simple.success is True
    assert cfg["models"]["simple"] == "glm-5.3-flash"

    res_main = apply_nl_config_command(cfg, "zmien glowny model na sonnet", tmp_path)
    assert res_main.success is True
    assert cfg["models"]["default"] == "sonnet"


def test_apply_multi_intent_batch(tmp_path: Path) -> None:
    cfg = _sample_config(tmp_path)
    res = apply_nl_config_command(cfg, "ide na cursor and port na 9090 oraz wlacz lan", tmp_path)
    assert res.success is True
    assert res.updated is True
    assert cfg["ide"] == "cursor"
    assert cfg["serve"]["port"] == 9090
    assert cfg["serve"]["lan"] is True


def test_multi_intent_atomic_rollback_on_failure(tmp_path: Path) -> None:
    cfg = _sample_config(tmp_path)
    # Second segment fails due to unknown IDE
    res = apply_nl_config_command(cfg, "port na 9090 and ide na non_existent_ide_xyz", tmp_path)
    assert res.success is False
    assert res.updated is False
    # Original port should be preserved
    assert cfg["serve"]["port"] == 8765
