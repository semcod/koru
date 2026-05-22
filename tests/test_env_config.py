"""Regression tests for koru.env_config (system-config dashboard tab)."""

from __future__ import annotations

from pathlib import Path

import pytest

from koru.env_config import (
    KORU_ENV_KEYS,
    env_config_payload,
    write_env_config,
)


def test_known_keys_include_vision_interval() -> None:
    names = {spec.name for spec in KORU_ENV_KEYS}
    assert "KORU_VISION_INTERVAL" in names
    assert "KORU_VISION_PROVIDER" in names
    assert "KORU_VISION_INTERVAL_MIN" in names


def test_env_config_payload_reads_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".env").write_text(
        "# header\nKORU_VISION_INTERVAL=45\nKORU_VISION_PROVIDER=portal_screencast\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("KORU_VISION_INTERVAL", raising=False)
    monkeypatch.setenv("KORU_VISION_SCALE", "0.4")
    payload = env_config_payload(tmp_path)
    assert payload["exists"] is True
    by_name = {row["name"]: row for row in payload["keys"]}
    assert by_name["KORU_VISION_INTERVAL"]["file_value"] == "45"
    assert by_name["KORU_VISION_INTERVAL"]["in_file"] is True
    assert by_name["KORU_VISION_PROVIDER"]["file_value"] == "portal_screencast"
    assert by_name["KORU_VISION_SCALE"]["env_value"] == "0.4"
    assert by_name["KORU_VISION_SCALE"]["in_file"] is False


def test_write_env_config_preserves_unrelated_lines(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "# top comment\n"
        "OPENROUTER_API_KEY=abc\n"
        "KORU_VISION_INTERVAL=60\n"
        "PFIX_ENABLED=true\n",
        encoding="utf-8",
    )
    write_env_config(tmp_path, {"KORU_VISION_INTERVAL": "45", "KORU_VISION_PROVIDER": "mss"})
    text = env_path.read_text(encoding="utf-8")
    assert "# top comment" in text
    assert "OPENROUTER_API_KEY=abc" in text
    assert "PFIX_ENABLED=true" in text
    assert "KORU_VISION_INTERVAL=45" in text
    assert "KORU_VISION_PROVIDER=mss" in text


def test_write_env_config_creates_file_when_missing(tmp_path: Path) -> None:
    write_env_config(tmp_path, {"KORU_VISION_INTERVAL": "30"})
    text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "KORU_VISION_INTERVAL=30" in text
