"""Routing of shell-client targets (tillm) in the autonomous loop.

Covers three autonomy guarantees:
- ``--ide claude`` must fail loudly (not silently fall through to the IDE
  plugin lane) when the tillm package is unavailable,
- ``--ide auto`` on an editor-less host auto-selects an installed shell
  client so the loop is autonomous in headless environments,
- the tillm_bridge helpers behind both behaviors.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import koru.tillm_bridge as tillm_bridge
from koru.autonomous_cycle_config import (
    _autodetect_shell_client_for_auto,
    configure_loop_state,
)


def _args(autopilot_ide: str = "auto") -> SimpleNamespace:
    return SimpleNamespace(
        ticket_sources="default",
        queue_name="default",
        agent_lane="auto",
        autopilot_ide=autopilot_ide,
        emit_events="human",
    )


def _configure(args: SimpleNamespace, tmp_path: Path, *, lane: str | None = None):
    return configure_loop_state(
        args,
        tmp_path,
        effective_flags=lambda ticket_sources: (True, False),
        apply_agent_lane_environ=lambda *_a: lane,
        resolve_autopilot_ide=lambda *_a, **_k: ("vscode", "router:auto"),
        resolve_ide_route_fn=lambda *_a, **_k: None,
        state_factory=lambda: object(),
        load_checkpoint=lambda *_a, **_k: None,
    )


class TestShellClientMisroutingGuard:
    def test_shell_token_without_tillm_aborts_loudly(self, tmp_path, monkeypatch):
        monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
        monkeypatch.setattr(tillm_bridge, "shell_drive_client_id", lambda _t: None)
        monkeypatch.setattr(tillm_bridge, "looks_like_shell_client", lambda _t: True)

        with pytest.raises(SystemExit) as excinfo:
            _configure(_args("claude"), tmp_path)
        assert "tillm" in str(excinfo.value)

    def test_looks_like_shell_client_fallback_tokens(self, monkeypatch):
        # Simulate tillm being unimportable: the registry lookup yields None,
        # so recognition must come from the fallback token list.
        monkeypatch.setattr(tillm_bridge, "shell_drive_client_id", lambda _t: None)
        assert tillm_bridge.looks_like_shell_client("claude") is True
        assert tillm_bridge.looks_like_shell_client("Claude-Code") is True
        assert tillm_bridge.looks_like_shell_client("vscode") is False
        assert tillm_bridge.looks_like_shell_client("") is False


class TestAutoShellClientSelection:
    def test_auto_on_headless_host_selects_available_client(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
        monkeypatch.delenv("KORU_TILLM_CLIENT", raising=False)
        monkeypatch.delenv("KORU_AUTO_SHELL_CLIENT", raising=False)
        monkeypatch.setattr(tillm_bridge, "shell_drive_client_id", lambda _t: None)
        monkeypatch.setattr(tillm_bridge, "looks_like_shell_client", lambda _t: False)
        monkeypatch.setattr(tillm_bridge, "tillm_available", lambda: True)
        monkeypatch.setattr(
            tillm_bridge, "detect_available_shell_client", lambda: "claude"
        )
        import koruide.ide as koruide_ide

        monkeypatch.setattr(koruide_ide, "detect_running_ides", lambda: [])

        _, _, selected_ide, *_rest = _configure(_args("auto"), tmp_path, lane=None)

        assert selected_ide == "claude"
        import os

        assert os.environ.get("KORU_TILLM_CLIENT") == "claude"

    def test_autodetect_skipped_when_editor_running(self):
        result = _autodetect_shell_client_for_auto(
            "auto",
            None,
            tillm_available=lambda: True,
            detect_running_ides_fn=lambda: [SimpleNamespace(id="vscode")],
            detect_shell_client_fn=lambda: "claude",
        )
        assert result is None

    def test_autodetect_skipped_for_explicit_target(self):
        result = _autodetect_shell_client_for_auto(
            "vscode",
            None,
            tillm_available=lambda: True,
            detect_running_ides_fn=lambda: [],
            detect_shell_client_fn=lambda: "claude",
        )
        assert result is None

    def test_autodetect_skipped_when_lane_points_at_editor(self):
        result = _autodetect_shell_client_for_auto(
            "auto",
            "cursor-main",
            tillm_available=lambda: True,
            detect_running_ides_fn=lambda: [],
            detect_shell_client_fn=lambda: "claude",
        )
        assert result is None

    def test_autodetect_opt_out_env(self, monkeypatch):
        monkeypatch.setenv("KORU_AUTO_SHELL_CLIENT", "0")
        result = _autodetect_shell_client_for_auto(
            "auto",
            None,
            tillm_available=lambda: True,
            detect_running_ides_fn=lambda: [],
            detect_shell_client_fn=lambda: "claude",
        )
        assert result is None

    def test_autodetect_requires_tillm(self):
        result = _autodetect_shell_client_for_auto(
            "auto",
            None,
            tillm_available=lambda: False,
            detect_running_ides_fn=lambda: [],
            detect_shell_client_fn=lambda: "claude",
        )
        assert result is None


class TestTillmBridgeDetection:
    def test_detect_available_shell_client_prefers_launchable(self, monkeypatch):
        rows = [
            {"id": "aider", "available": True, "launchable": False},
            {"id": "claude", "available": True, "launchable": True},
        ]
        monkeypatch.setattr(
            tillm_bridge, "detect_shell_agent_rows", lambda **_k: rows
        )
        assert tillm_bridge.detect_available_shell_client() == "claude"

    def test_detect_available_shell_client_none_when_nothing_launchable(
        self, monkeypatch
    ):
        rows = [{"id": "aider", "available": False, "launchable": False}]
        monkeypatch.setattr(
            tillm_bridge, "detect_shell_agent_rows", lambda **_k: rows
        )
        assert tillm_bridge.detect_available_shell_client() is None
