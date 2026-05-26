from __future__ import annotations

import os
from pathlib import Path

import pytest

from koru.autonomous_cycle import _plugin_required_for_ide
from koru.ide_router import resolve_ide_route
from koruide.config import cached_config
from koruide.plugin_version import EXPECTED_VSCODE_PLUGIN_VERSION
from koruide.socket import default_socket_path

ROOT = Path(__file__).resolve().parents[1]
MATRIX_IDES = ("vscode", "vscodium", "cursor", "windsurf", "antigravity", "jetbrains", "zed")
PLUGIN_REQUIRED_IDES = frozenset({"vscode", "vscodium", "cursor", "windsurf", "antigravity"})


@pytest.mark.parametrize("ide", MATRIX_IDES)
def test_headless_bridge_route_honors_each_matrix_ide(ide: str) -> None:
    route = resolve_ide_route(
        cli_autopilot_ide="auto",
        environ={
            "KORU_HEADLESS": "1",
            "KORU_HEADLESS_ALLOW_AUTOPILOT": "1",
            "KORU_AUTOPILOT_IDE": ide,
        },
    )

    assert route.autopilot_ide == ide
    assert route.primary_surface == "ide_shell"
    assert route.recommend_autopilot_drive is True


@pytest.mark.parametrize("ide", MATRIX_IDES)
def test_autopilot_plugin_requirement_matrix(monkeypatch: pytest.MonkeyPatch, ide: str) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_ALLOW_KEYBOARD_FALLBACK", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_PREFER_KEYBOARD", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_VISIBLE_TYPING", raising=False)

    assert _plugin_required_for_ide(ide) is (ide in PLUGIN_REQUIRED_IDES)


@pytest.mark.parametrize("ide", MATRIX_IDES)
def test_every_matrix_ide_has_submit_key_default(ide: str) -> None:
    assert cached_config().submit_key_for(ide)


@pytest.mark.parametrize("ide", MATRIX_IDES)
def test_every_matrix_ide_has_isolated_default_socket(
    monkeypatch: pytest.MonkeyPatch,
    ide: str,
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_SOCKET", raising=False)
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", ide)
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")

    assert default_socket_path().name == f"koru-autopilot-{ide}.sock"


def test_container_matrix_env_matches_supported_ide() -> None:
    ide = os.environ.get("KORU_MATRIX_IDE")
    if not ide:
        pytest.skip("not running inside the Docker IDE matrix container")
    assert ide in MATRIX_IDES


def test_vscodium_matrix_keeps_explicit_lane_despite_generic_vscode_terminal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from koru import autonomous_startup as startup

    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscodium")
    monkeypatch.setenv("TERM_PROGRAM", "vscode")
    monkeypatch.setattr(startup, "_terminal_agent_lane_from_env", lambda: "vscode")
    monkeypatch.setattr(
        startup,
        "detect_running_ides",
        lambda: [
            startup.RunningIDE(id="vscode", label="VS Code", pid=10, exe="/usr/bin/code"),
            startup.RunningIDE(id="vscodium", label="VSCodium", pid=11, exe="/usr/bin/codium"),
        ],
    )

    lane, source = startup.resolve_agent_lane_id(
        tmp_path,
        "auto",
        resolve_project_lane=lambda _project, lane_id: lane_id,
    )

    assert lane == "vscodium"
    assert source == "env:KORU_AUTOPILOT_INSTANCE"


def test_vscodium_matrix_uses_isolated_socket_with_vscode_terminal_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscodium")
    monkeypatch.setenv("TERM_PROGRAM", "vscode")
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")
    monkeypatch.delenv("KORU_AUTOPILOT_SOCKET", raising=False)

    assert default_socket_path().name == "koru-autopilot-vscodium.sock"


def test_vscodium_plugin_uses_host_clipboard_for_webview_paste() -> None:
    source = (
        ROOT / "plugins" / "koru-autopilot-vscodium" / "src" / "_shared" / "autopilot-bridge.ts"
    ).read_text(encoding="utf-8")

    assert "tryHostClipboardPaste" in source
    assert "wl-copy" in source
    assert "wtype\", [\"-M\", \"ctrl\", \"-k\", \"v\", \"-m\", \"ctrl\"]" in source
    assert "xdotool\", [\"key\", \"ctrl+v\"]" in source
    assert "ydotool\", [\"key\", \"ctrl+v\"]" in source
    assert "host-clipboard:${clip}+${paste.command}" in source
    assert "HOST_CLIPBOARD_RESTORE" in source
    assert "paste_failure_reason" in source


def test_vscodium_plugin_does_not_report_submit_success_without_submission() -> None:
    source = (
        ROOT / "plugins" / "koru-autopilot-vscodium" / "src" / "_shared" / "autopilot-bridge.ts"
    ).read_text(encoding="utf-8")

    assert 'command: "vscodium-submit-unavailable"' in source
    assert 'verification: "submit_unverified"' in source
    assert "submitted: false" in source
    assert "manual Send may be required" in source
    assert "operation_trace" in source
    assert "OP_ROUTE" in source
    assert "submit_verify" in source


def test_vscodium_submit_tries_registered_commands_before_host_fallbacks() -> None:
    source = (
        ROOT / "plugins" / "koru-autopilot-vscodium" / "src" / "_shared" / "autopilot-bridge.ts"
    ).read_text(encoding="utf-8")

    registered = source.index("const registered = await this._tryRegisteredCommands")
    host_click = source.index("const hostClick = await this._tryHostClickSubmit")
    assert registered < host_click
    assert 'buildSubmitCommands("vscodium")' in source


def test_vscodium_plugin_supports_configured_submit_click() -> None:
    source = (
        ROOT / "plugins" / "koru-autopilot-vscodium" / "src" / "_shared" / "autopilot-bridge.ts"
    ).read_text(encoding="utf-8")
    package = (
        ROOT / "plugins" / "koru-autopilot-vscodium" / "package.json"
    ).read_text(encoding="utf-8")

    assert "submitClickX" in package
    assert "submitClickY" in package
    assert "koruAutopilot.captureSubmitClick" in package
    assert "SUBMIT_CLICK" in source
    assert "xdotool click@" in source
    assert "ydotool click@" in source
    assert "trustUnverifiedHostSubmit" in package
    assert "trustUnverifiedHostSubmit" in source


def test_matrix_fake_extension_version_matches_bundled_plugin() -> None:
    entrypoint = (ROOT / "scripts" / "docker-ide-matrix-entrypoint.sh").read_text(
        encoding="utf-8",
    )
    native = (ROOT / ".github" / "workflows" / "native-ide-matrix.yml").read_text(
        encoding="utf-8",
    )

    assert "koruide.plugin_version import EXPECTED_VSCODE_PLUGIN_VERSION" in entrypoint
    assert "KORU_FAKE_EXTENSION_VERSION:-" in entrypoint
    assert f'"{EXPECTED_VSCODE_PLUGIN_VERSION}"' in native
