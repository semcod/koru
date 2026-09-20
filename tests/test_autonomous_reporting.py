"""Focused regression tests for ``koru.autonomous.reporting``.

The submodule owns the environment-reporting responsibility (doctor/status/
self-heal payloads, text formatting and actions) extracted from the historical
``koru.autonomous`` facade in ticket-185. These tests pin its behavior and the
facade re-export contract.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import koru.autonomous as autonomous_facade
from koru.autonomous.reporting import (
    _action_doctor,
    _action_self_heal,
    _action_status,
    _autonomous_report_payload,
    _format_autonomous_report_text,
    _ide_presence_payload,
    _repair_payload,
    _resolve_autonomous_report_socket,
    _socket_payload,
)
from koru.autonomy.environment import EnvironmentReport, IDEPresence, SocketHealth
from koru.autonomy.heal import RepairResult


def _presence(ide: str = "cursor", installed: bool = True, mcp: bool = False) -> IDEPresence:
    return IDEPresence(
        ide=ide,
        binary_path="/usr/bin/cursor" if installed else None,
        mcp_config_path=Path("/tmp/mcp.json") if mcp else None,
        mcp_has_koru=mcp,
    )


class TestSocketPayload:
    def test_none_socket_yields_none(self) -> None:
        assert _socket_payload(None) is None

    def test_socket_fields_and_derived_healthy(self, tmp_path: Path) -> None:
        socket = SocketHealth(path=tmp_path / "koru.sock", exists=True, listening=True, stale=False)
        payload = _socket_payload(socket)
        assert payload is not None
        assert payload["path"] == str(socket.path)
        assert payload["exists"] is True
        assert payload["listening"] is True
        assert payload["stale"] is False
        assert payload["healthy"] is True

    def test_stale_socket_is_not_healthy(self, tmp_path: Path) -> None:
        socket = SocketHealth(path=tmp_path / "koru.sock", exists=True, listening=False, stale=True)
        payload = _socket_payload(socket)
        assert payload is not None
        assert payload["healthy"] is False


class TestIdePresencePayload:
    def test_fields_and_optional_mcp_path(self) -> None:
        payload = _ide_presence_payload(_presence(mcp=True))
        assert payload["ide"] == "cursor"
        assert payload["installed"] is True
        assert payload["binary_path"] == "/usr/bin/cursor"
        assert payload["mcp_config_path"] == "/tmp/mcp.json"
        assert payload["mcp_has_koru"] is True

    def test_missing_mcp_config_serialises_to_none(self) -> None:
        payload = _ide_presence_payload(_presence())
        assert payload["mcp_config_path"] is None
        assert payload["mcp_has_koru"] is False


class TestReportPayload:
    def test_payload_shape_and_ready_derivation(self, tmp_path: Path) -> None:
        report = EnvironmentReport(
            headless=True,
            ides=[_presence("cursor", mcp=True), _presence("code", installed=False)],
            can_use_plugin_socket=True,
            fixable_issues=["install-plugin"],
            notes=["probe note"],
        )
        payload = _autonomous_report_payload(tmp_path, report, action="doctor")
        assert payload["action"] == "doctor"
        assert payload["project"] == str(tmp_path)
        assert payload["headless"] is True
        assert payload["installed_ides"] == ["cursor"]
        assert payload["mcp_enabled_ides"] == ["cursor"]
        assert len(payload["ides"]) == 2
        assert payload["autopilot_socket"] is None
        assert payload["ready"] is True
        assert payload["fixable_issues"] == ["install-plugin"]
        assert payload["notes"] == ["probe note"]

    def test_ready_requires_socket_or_mcp(self, tmp_path: Path) -> None:
        report = EnvironmentReport(headless=False)
        payload = _autonomous_report_payload(tmp_path, report, action="status")
        assert payload["ready"] is False


class TestReportText:
    def test_text_lines_with_socket(self, tmp_path: Path) -> None:
        socket = SocketHealth(path=tmp_path / "koru.sock", exists=True, listening=False, stale=True)
        report = EnvironmentReport(
            headless=False,
            ides=[_presence("cursor", mcp=True)],
            autopilot_socket=socket,
            can_use_mcp=True,
            fixable_issues=["install-plugin"],
            notes=["probe note"],
        )
        lines = _format_autonomous_report_text(report, action="status")
        assert lines[0] == "koru autonomous status"
        assert "installed IDEs: cursor" in lines
        assert "MCP enabled IDEs: cursor" in lines
        assert f"autopilot socket: {socket.path} exists=True listening=False stale=True" in lines
        assert "ready: True" in lines
        assert "fixable: install-plugin" in lines
        assert "note: probe note" in lines

    def test_text_lines_without_socket_or_ides(self) -> None:
        report = EnvironmentReport(headless=True)
        lines = _format_autonomous_report_text(report)
        assert "autopilot socket: not configured" in lines
        assert "installed IDEs: none" in lines
        assert "MCP enabled IDEs: none" in lines
        assert "ready: False" in lines


class TestResolveReportSocket:
    def test_explicit_socket_wins(self, tmp_path: Path) -> None:
        explicit = tmp_path / "explicit.sock"
        resolved = _resolve_autonomous_report_socket(explicit, tmp_path)
        assert resolved == explicit.expanduser().resolve()

    def test_default_socket_resolved_via_lane_context(self, tmp_path: Path, monkeypatch) -> None:
        seen: dict[str, object] = {}

        def fake_resolver(namespace, *, project):
            seen["namespace"] = namespace
            seen["project"] = project
            return Path("/resolved/default.sock")

        monkeypatch.setattr(
            "koru.autopilot.lane_context.resolve_client_socket_path",
            fake_resolver,
        )
        resolved = _resolve_autonomous_report_socket(None, tmp_path)
        assert resolved == Path("/resolved/default.sock")
        namespace = seen["namespace"]
        assert isinstance(namespace, argparse.Namespace)
        assert namespace.socket is None
        assert namespace.ide == "auto"
        assert seen["project"] == tmp_path


class TestDoctorStatusActions:
    def test_doctor_json_payload(self, tmp_path: Path, monkeypatch, capsys) -> None:
        report = EnvironmentReport(headless=False, can_use_plugin_socket=True)
        monkeypatch.setattr(
            "koru.autonomy.environment.probe_environment",
            lambda project, autopilot_socket=None: report,
        )
        args = argparse.Namespace(
            project=tmp_path,
            socket=None,
            format="json",
        )
        assert _action_doctor(args) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["action"] == "doctor"
        assert payload["ready"] is True

    def test_status_text_output(self, tmp_path: Path, monkeypatch, capsys) -> None:
        report = EnvironmentReport(headless=False, can_use_mcp=True, notes=["note-1"])
        monkeypatch.setattr(
            "koru.autonomy.environment.probe_environment",
            lambda project, autopilot_socket=None: report,
        )
        args = argparse.Namespace(
            project=tmp_path,
            socket=None,
            format="text",
        )
        assert _action_status(args) == 0
        out = capsys.readouterr().out
        assert "koru autonomous status" in out
        assert "note: note-1" in out


class TestSelfHealAction:
    def _args(self, tmp_path: Path, *, fmt: str, dry_run: bool) -> argparse.Namespace:
        return argparse.Namespace(
            project=tmp_path,
            socket=None,
            format=fmt,
            dry_run=dry_run,
        )

    def test_json_ok_when_no_failure(self, tmp_path: Path, monkeypatch, capsys) -> None:
        report = EnvironmentReport(headless=True)
        monkeypatch.setattr(
            "koru.autonomy.environment.probe_environment",
            lambda project, autopilot_socket=None: report,
        )
        results = [
            RepairResult(action="remove_stale_socket", status="fixed", detail="removed"),
            RepairResult(action="remove_stale_socket", status="skipped"),
        ]
        monkeypatch.setattr(
            "koru.autonomy.heal.heal_environment",
            lambda r, dry_run=False: results,
        )
        assert _action_self_heal(self._args(tmp_path, fmt="json", dry_run=True)) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["action"] == "self-heal"
        assert payload["dry_run"] is True
        assert payload["ok"] is True
        assert payload["results"][0] == {
            "action": "remove_stale_socket",
            "status": "fixed",
            "detail": "removed",
        }

    def test_json_exit_one_on_failed_repair(self, tmp_path: Path, monkeypatch, capsys) -> None:
        monkeypatch.setattr(
            "koru.autonomy.environment.probe_environment",
            lambda project, autopilot_socket=None: EnvironmentReport(headless=True),
        )
        monkeypatch.setattr(
            "koru.autonomy.heal.heal_environment",
            lambda r, dry_run=False: [
                RepairResult(action="remove_stale_socket", status="failed", detail="boom"),
            ],
        )
        assert _action_self_heal(self._args(tmp_path, fmt="json", dry_run=False)) == 1
        payload = json.loads(capsys.readouterr().out)
        assert payload["ok"] is False

    def test_text_output_lists_each_result(self, tmp_path: Path, monkeypatch, capsys) -> None:
        monkeypatch.setattr(
            "koru.autonomy.environment.probe_environment",
            lambda project, autopilot_socket=None: EnvironmentReport(headless=True),
        )
        monkeypatch.setattr(
            "koru.autonomy.heal.heal_environment",
            lambda r, dry_run=False: [
                RepairResult(action="remove_stale_socket", status="fixed", detail="removed x"),
                RepairResult(action="remove_stale_socket", status="failed"),
            ],
        )
        assert _action_self_heal(self._args(tmp_path, fmt="text", dry_run=False)) == 1
        out = capsys.readouterr().out
        assert "remove_stale_socket: fixed: removed x" in out
        assert "remove_stale_socket: failed" in out


class TestRepairPayload:
    def test_maps_every_result_field(self) -> None:
        results = [
            RepairResult(action="a1", status="fixed", detail="d1"),
            RepairResult(action="a2", status="skipped"),
        ]
        assert _repair_payload(results) == [
            {"action": "a1", "status": "fixed", "detail": "d1"},
            {"action": "a2", "status": "skipped", "detail": ""},
        ]


class TestFacadeReExports:
    def test_facade_reexports_reporting_api(self) -> None:
        assert autonomous_facade._socket_payload is _socket_payload
        assert autonomous_facade._ide_presence_payload is _ide_presence_payload
        assert autonomous_facade._autonomous_report_payload is _autonomous_report_payload
        assert autonomous_facade._format_autonomous_report_text is _format_autonomous_report_text
        assert autonomous_facade._resolve_autonomous_report_socket is _resolve_autonomous_report_socket
        assert autonomous_facade._action_doctor is _action_doctor
        assert autonomous_facade._action_status is _action_status
        assert autonomous_facade._action_self_heal is _action_self_heal
        assert autonomous_facade._repair_payload is _repair_payload
