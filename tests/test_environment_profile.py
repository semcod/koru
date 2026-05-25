from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from koru import environment_profile as env_profile


def test_environment_profile_separates_vscodium_wayland_plugin_control(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscodium")
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.setattr(env_profile, "detect_terminal_host_ide_id", lambda: "vscode")
    monkeypatch.setattr(env_profile, "detect_running_ides", lambda: [])
    monkeypatch.setattr(env_profile, "normalize_ide_id", lambda x: x if x else None)
    monkeypatch.setattr(env_profile, "detect_focused_ide_id", lambda: None)

    profile = env_profile.resolve_environment_profile(tmp_path, ide="auto")

    assert profile.os.display_server == "wayland"
    assert profile.os.preferred_keyboard_interface == "os_injector_wtype"
    assert profile.ide.id == "vscodium"
    assert profile.ide.plugin_supported is True
    assert profile.control.interface_id == "plugin_socket_vscode_family"
    assert profile.control.verification_mode == "strict_ack"
    assert "ide=vscodium" in profile.decision_key


def test_environment_profile_treats_jetbrains_as_distinct_control_surface(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")

    profile = env_profile.resolve_environment_profile(tmp_path, ide="jetbrains")

    assert profile.ide.id == "jetbrains"
    assert profile.ide.plugin_supported is False
    assert profile.ide.keyboard_fallback_default is True
    assert profile.ide.submit_key == "ctrl+Return"
    assert profile.control.interface_id == "plugin_socket_jetbrains"
    assert profile.control.verification_mode == "plugin_ack"


def test_environment_profile_treats_windsurf_as_distinct_native_surface(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")

    profile = env_profile.resolve_environment_profile(tmp_path, ide="windsurf")

    assert profile.ide.id == "windsurf"
    assert profile.control.interface_id == "windsurf_native_send"
    assert profile.control.interface_id != "antigravity_native_send"
    assert "ide=windsurf" in profile.decision_key
    assert "control=windsurf_native_send" in profile.decision_key


def test_environment_profile_uses_explicit_running_ide_when_no_env(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.setattr(env_profile, "detect_terminal_host_ide_id", lambda: None)
    monkeypatch.setattr(env_profile, "detect_focused_ide_id", lambda: None)
    monkeypatch.setattr(
        env_profile,
        "detect_running_ides",
        lambda: [SimpleNamespace(id="cursor")],
    )

    profile = env_profile.resolve_environment_profile(tmp_path, ide="auto")

    assert profile.ide.id == "cursor"
    assert profile.control.interface_id == "plugin_socket_vscode_family"


def test_llm_environment_is_an_independent_axis(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")

    profile = env_profile.resolve_environment_profile(tmp_path, ide="vscodium")

    assert profile.llm.provider == "openai"
    assert profile.llm.model == "gpt-test"
    assert profile.llm.source == "OPENAI_MODEL"
    assert "llm=openai" in profile.decision_key
