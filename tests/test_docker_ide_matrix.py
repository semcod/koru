from __future__ import annotations

import os

import pytest

from koru.autonomous_cycle import _plugin_required_for_ide
from koru.ide_router import resolve_ide_route
from koruide.config import cached_config
from koruide.socket import default_socket_path

MATRIX_IDES = ("vscode", "vscodium", "cursor", "windsurf", "jetbrains", "zed")
PLUGIN_REQUIRED_IDES = frozenset({"vscode", "vscodium", "cursor", "windsurf"})


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
