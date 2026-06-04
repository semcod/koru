"""Tests for ``koru.autopilot.config`` (R7).

The config loader must:

* return safe defaults when the file is missing,
* prefer user-provided submit keys over the built-ins,
* survive a malformed TOML without crashing (warning to stderr),
* ignore non-string values inside ``[submit_keys]``,
* honour ``$XDG_CONFIG_HOME`` for ``default_config_path()``,
* memoise inside ``cached_config`` until ``clear_config_cache()``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from koru.autopilot import config as config_mod
from koru.autopilot.config import (
    AutopilotConfig,
    cached_config,
    clear_config_cache,
    default_config_path,
    load_config,
)

# ---- load_config -----------------------------------------------------------


def test_load_config_returns_defaults_when_file_missing(tmp_path: Path) -> None:
    cfg = load_config(tmp_path / "missing.toml")
    assert cfg.submit_keys["jetbrains"] == "ctrl+Return"
    assert cfg.submit_keys["windsurf"] == "Return"
    assert cfg.source is None


def test_load_config_user_keys_override_defaults(tmp_path: Path) -> None:
    path = tmp_path / "autopilot.toml"
    path.write_text(
        '[submit_keys]\nwindsurf = "ctrl+Return"\nfleet    = "alt+Return"\n',
        encoding="utf-8",
    )
    cfg = load_config(path)
    assert cfg.source == path
    assert cfg.submit_keys["windsurf"] == "ctrl+Return"  # overridden
    assert cfg.submit_keys["jetbrains"] == "ctrl+Return"  # default preserved
    assert cfg.submit_keys["fleet"] == "alt+Return"  # new IDE accepted


def test_load_config_malformed_toml_falls_back_to_defaults(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "bad.toml"
    path.write_text("this = is not = toml", encoding="utf-8")
    cfg = load_config(path)
    # Defaults kept; one stderr line printed.
    assert cfg.submit_keys["jetbrains"] == "ctrl+Return"
    assert cfg.source is None
    err = capsys.readouterr().err
    assert "ignoring malformed config" in err
    assert str(path) in err


def test_load_config_skips_non_string_entries(tmp_path: Path) -> None:
    """``submit_keys`` entries with non-string values must be ignored."""
    path = tmp_path / "autopilot.toml"
    path.write_text(
        '[submit_keys]\ngood = "Return"\nbad_int = 42\nbad_arr = ["a", "b"]\nempty   = ""\n',
        encoding="utf-8",
    )
    cfg = load_config(path)
    assert cfg.submit_keys["good"] == "Return"
    assert "bad_int" not in cfg.submit_keys
    assert "bad_arr" not in cfg.submit_keys
    assert "empty" not in cfg.submit_keys


def test_load_config_ignores_unrelated_sections(tmp_path: Path) -> None:
    """Sections other than [submit_keys] don't disturb anything."""
    path = tmp_path / "autopilot.toml"
    path.write_text(
        '[future_section]\nenabled = true\n[submit_keys]\nwindsurf = "Return"\n',
        encoding="utf-8",
    )
    cfg = load_config(path)
    assert cfg.submit_keys["windsurf"] == "Return"


# ---- AutopilotConfig.submit_key_for ----------------------------------------


def test_submit_key_for_falls_back_to_default() -> None:
    cfg = AutopilotConfig(submit_keys={"default": "Return", "jetbrains": "ctrl+Return"})
    assert cfg.submit_key_for("windsurf") == "Return"
    assert cfg.submit_key_for("jetbrains") == "ctrl+Return"


def test_submit_key_for_uses_explicit_default_when_present() -> None:
    cfg = AutopilotConfig(submit_keys={"default": "ctrl+Return"})
    assert cfg.submit_key_for("anything") == "ctrl+Return"


def test_submit_key_for_falls_back_when_no_default_key() -> None:
    cfg = AutopilotConfig(submit_keys={})
    # Hard-coded last-resort fallback inside the method.
    assert cfg.submit_key_for("anything") == "Return"


# ---- default_config_path / XDG --------------------------------------------


def test_default_config_path_uses_xdg_when_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert default_config_path() == tmp_path / "koru" / "autopilot.toml"


def test_default_config_path_falls_back_to_home(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    p = default_config_path()
    assert p.name == "autopilot.toml"
    assert p.parent.name == "koru"


# ---- cached_config memoisation --------------------------------------------


def test_cached_config_is_memoised(monkeypatch: pytest.MonkeyPatch) -> None:
    import gillm.config as gillm_config_mod

    calls = []

    def fake_load() -> AutopilotConfig:
        calls.append(None)
        return AutopilotConfig()

    monkeypatch.setattr(gillm_config_mod, "load_config", lambda *_a, **_k: fake_load())
    clear_config_cache()
    cached_config()
    cached_config()
    cached_config()
    assert len(calls) == 1
    clear_config_cache()
    cached_config()
    assert len(calls) == 2
