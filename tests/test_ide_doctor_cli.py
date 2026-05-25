"""Tests for ``koru ide doctor`` bridge diagnostics."""

from __future__ import annotations

import json
from pathlib import Path

from koru.cli_ide import ide_main
from koru.ide_doctor_cli import _resolve_socket
from koru.ide_adapters import shared
from koru.ide_adapters import bridge as bridge_mod


def _write_extensions_json(path: Path, extension_ids: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [{"identifier": {"id": extension_id}} for extension_id in extension_ids]
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_extension_metadata_is_scoped_per_ide(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _write_extensions_json(tmp_path / ".cursor" / "extensions" / "extensions.json", [])
    _write_extensions_json(
        tmp_path / ".vscode" / "extensions" / "extensions.json",
        [shared.EXTENSION_ID],
    )

    assert shared.extension_listed_in_extensions_json("cursor") is False
    assert shared.extension_listed_in_extensions_json("vscode") is True


def test_ide_doctor_json_reports_plugin_not_connected(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    class FakeAutopilotClient:
        def __init__(self, *, socket_path: Path, timeout: float) -> None:
            self.socket_path = socket_path
            self.timeout = timeout

        def is_running(self) -> bool:
            return True

        def status(self) -> dict[str, object]:
            return {"plugins": []}

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setattr(bridge_mod, "AutopilotClient", FakeAutopilotClient)
    _write_extensions_json(
        tmp_path / ".vscode" / "extensions" / "extensions.json",
        [shared.EXTENSION_ID],
    )

    rc = ide_main(
        [
            "doctor",
            "--ide",
            "vscode",
            "--project",
            str(tmp_path),
            "--socket",
            str(tmp_path / "koru-autopilot-vscode.sock"),
            "--format",
            "json",
        ],
    )

    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ide"] == "vscode"
    assert payload["daemon_running"] is True
    assert payload["plugins_connected"] is False
    assert payload["hypotheses"][0]["id"] == "vscode.plugin.not_connected"
    assert "Developer: Reload Window" in payload["hypotheses"][0]["remediation"]["summary"]


def test_ide_doctor_json_prioritizes_stale_rejected_plugin(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    class FakeAutopilotClient:
        def __init__(self, *, socket_path: Path, timeout: float) -> None:
            self.socket_path = socket_path
            self.timeout = timeout

        def is_running(self) -> bool:
            return True

        def status(self) -> dict[str, object]:
            return {
                "plugins": [],
                "rejected_plugins": [
                    {
                        "ide": "vscode",
                        "version": "0.1.74",
                        "expected_version": "0.1.75",
                    },
                ],
            }

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setattr(bridge_mod, "AutopilotClient", FakeAutopilotClient)
    _write_extensions_json(
        tmp_path / ".vscode" / "extensions" / "extensions.json",
        [shared.EXTENSION_ID],
    )

    rc = ide_main(
        [
            "doctor",
            "--ide",
            "vscode",
            "--project",
            str(tmp_path),
            "--socket",
            str(tmp_path / "koru-autopilot-vscode.sock"),
            "--format",
            "json",
        ],
    )

    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["hypotheses"][0]["id"] == "vscode.plugin.live_host_stale"
    assert "Developer: Reload Window" in payload["hypotheses"][0]["remediation"]["summary"]


def test_ide_doctor_defaults_socket_to_selected_lane(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_SOCKET", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    args = type("Args", (), {"socket": None, "instance": None})()

    socket = _resolve_socket(args, "cursor")

    assert socket == tmp_path / "koru-autopilot-cursor.sock"
    assert "KORU_AUTOPILOT_INSTANCE" not in __import__("os").environ


def test_ide_doctor_instance_overrides_selected_lane(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_SOCKET", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    args = type("Args", (), {"socket": None, "instance": "vscodium"})()

    socket = _resolve_socket(args, "cursor")

    assert socket == tmp_path / "koru-autopilot-vscodium.sock"
