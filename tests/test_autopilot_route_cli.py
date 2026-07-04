"""``koru autopilot route`` + pre-drive control-route emission."""

from __future__ import annotations

import argparse
import json
from types import SimpleNamespace

from gillm.routing import router as rt

from koru.autopilot.commands.route import action_route


def _plan(selected_viable: bool) -> rt.RoutePlan:
    env = rt.EnvironmentFingerprint(
        session="wayland",
        desktop="ubuntu:gnome",
        keyboard_backends=("ydotool",),
        focus_detection=False,
        vdisplay_available=False,
        blind_opt_in=selected_viable,
    )
    app = rt.AppTarget(app_id="jetbrains", window_hints=("pycharm",), has_calibration=True)
    return rt.route(env, app)


class _NoDaemonClient:
    def status(self):
        raise OSError("no daemon")


class _PluginClient:
    def status(self):
        return {"plugins": [{"ide": "jetbrains", "version": "0.2.8"}]}


def _args(**overrides) -> argparse.Namespace:
    base = {"ide": "jetbrains", "project": None, "output_format": "json", "socket": None}
    base.update(overrides)
    return argparse.Namespace(**base)


def test_route_json_exit_1_when_nothing_viable(monkeypatch, capsys):
    import koru.autopilot.commands.route as route_mod

    monkeypatch.setattr(
        "gillm.routing.route_for",
        lambda ide, plugin_connected=False: _plan(selected_viable=False),
    )
    monkeypatch.setattr(
        route_mod,
        "_plugin_connected",
        lambda *_a, **_k: False,
    )
    code = action_route(_args(), client_factory=lambda _a: _NoDaemonClient())
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["selected"] is None
    assert len(payload["solutions"]) == 6


def test_route_json_exit_0_with_viable_solution(monkeypatch, capsys):
    monkeypatch.setattr(
        "gillm.routing.route_for",
        lambda ide, plugin_connected=False: _plan(selected_viable=True),
    )
    code = action_route(_args(), client_factory=lambda _a: _NoDaemonClient())
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["selected"]["solution_id"] == rt.SOLUTION_YDOTOOL_BLIND


def test_plugin_connected_resolution_matches_ide():
    from koru.autopilot.commands.route import _plugin_connected

    assert _plugin_connected(lambda _a: _PluginClient(), _args(), "jetbrains") is True
    assert _plugin_connected(lambda _a: _PluginClient(), _args(), "vscode") is False
    assert _plugin_connected(lambda _a: _NoDaemonClient(), _args(), "jetbrains") is False


def test_pre_drive_emits_control_route_line_and_telemetry(monkeypatch):
    from koru.autonomy.cycle import cycle as cycle_mod

    monkeypatch.setattr(
        "gillm.routing.route_for",
        lambda ide, plugin_connected=False: _plan(selected_viable=False),
    )
    lines: list[str] = []
    telemetry: dict = {}
    cycle_mod._emit_pre_drive_control_route(
        autopilot_ide="jetbrains",
        plugin_connected=False,
        cycle_telemetry=telemetry,
        hp=lines.append,
    )
    assert any("no viable control route" in line for line in lines)
    assert telemetry["control_route"]["selected"] is None


def test_pre_drive_control_route_survives_missing_gillm_routing(monkeypatch):
    from koru.autonomy.cycle import cycle as cycle_mod

    def _boom(*_a, **_k):
        raise ImportError("gillm.routing unavailable")

    monkeypatch.setattr("gillm.routing.route_for", _boom)
    lines: list[str] = []
    telemetry: dict = {}
    cycle_mod._emit_pre_drive_control_route(
        autopilot_ide="jetbrains",
        plugin_connected=False,
        cycle_telemetry=telemetry,
        hp=lines.append,
    )
    assert lines == []
    assert "control_route" not in telemetry
