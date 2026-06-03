"""Tests for ``koru ide doctor`` bridge diagnostics."""

from __future__ import annotations

import json
from pathlib import Path

from koru.cli_ide import ide_main
from koru.ide_adapters import bridge as bridge_mod
from koru.ide_adapters import shared
from koru.ide_doctor_cli import _resolve_socket


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


def test_ide_doctor_requires_compatible_plugin_for_project(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    project = tmp_path / "koru"
    other = tmp_path / "nexu"
    project.mkdir()
    other.mkdir()

    class FakeAutopilotClient:
        def __init__(self, *, socket_path: Path, timeout: float) -> None:
            self.socket_path = socket_path
            self.timeout = timeout

        def is_running(self) -> bool:
            return True

        def status(self) -> dict[str, object]:
            return {
                "plugins": [
                    {
                        "ide": "vscodium",
                        "version": "0.2.7",
                        "buildSha": "old-build",
                        "protocolVersion": 2,
                        "workspaceFolders": [str(project)],
                    },
                    {
                        "ide": "vscodium",
                        "version": "0.2.7",
                        "buildSha": "new-build",
                        "protocolVersion": 2,
                        "workspaceFolders": [str(other)],
                    },
                ],
            }

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("KORU_PLUGIN_VERSION_POLICY", "strict")
    monkeypatch.setattr(bridge_mod, "AutopilotClient", FakeAutopilotClient)
    monkeypatch.setattr(
        bridge_mod.DriveOrchestrator,
        "expected_plugin_build_sha",
        lambda _ide=None: "new-build",
    )
    _write_extensions_json(
        tmp_path / ".vscode-oss" / "extensions" / "extensions.json",
        [shared.extension_id_for_ide("vscodium")],
    )

    rc = ide_main(
        [
            "doctor",
            "--ide",
            "vscodium",
            "--project",
            str(project),
            "--socket",
            str(tmp_path / "koru-autopilot-vscodium.sock"),
            "--format",
            "json",
        ],
    )

    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["plugins_connected"] is True
    assert payload["plugins_compatible"] is False
    assert payload["ready"] is False
    assert payload["hypotheses"][0]["id"] == "vscodium.plugin.build_mismatch"
    assert "old-build" in payload["hypotheses"][0]["evidence"]
    assert "new-build" in payload["hypotheses"][0]["evidence"]


def test_ide_doctor_records_repair_history_for_llm(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    project = tmp_path / "koru"
    project.mkdir()

    class FakeAutopilotClient:
        def __init__(self, *, socket_path: Path, timeout: float) -> None:
            self.socket_path = socket_path
            self.timeout = timeout

        def is_running(self) -> bool:
            return True

        def status(self) -> dict[str, object]:
            return {
                "plugins": [
                    {
                        "ide": "vscodium",
                        "version": "0.2.7",
                        "buildSha": "old-build",
                        "protocolVersion": 2,
                        "workspaceFolders": [str(project)],
                    },
                ],
            }

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("KORU_PLUGIN_VERSION_POLICY", "strict")
    monkeypatch.setattr(bridge_mod, "AutopilotClient", FakeAutopilotClient)
    monkeypatch.setattr(
        bridge_mod.DriveOrchestrator,
        "expected_plugin_build_sha",
        lambda _ide=None: "new-build",
    )
    _write_extensions_json(
        tmp_path / ".vscode-oss" / "extensions" / "extensions.json",
        [shared.extension_id_for_ide("vscodium")],
    )

    rc = ide_main(
        [
            "doctor",
            "--ide",
            "vscodium",
            "--project",
            str(project),
            "--socket",
            str(tmp_path / "koru-autopilot-vscodium.sock"),
            "--fix",
            "--format",
            "json",
        ],
    )

    assert rc == 1
    capsys.readouterr()

    rc = ide_main(
        [
            "history",
            "--ide",
            "vscodium",
            "--project",
            str(project),
            "--format",
            "text",
        ],
    )

    assert rc == 0
    out = capsys.readouterr().out
    assert "repair history:" in out
    assert "repairs.diagnostic.recorded" in out
    assert "repairs.attempt.recorded" in out
    assert "vscodium.plugin.build_mismatch" in out
    assert "safe autofix requested" in out


def test_ide_doctor_defaults_socket_to_selected_lane(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_SOCKET", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
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
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    args = type("Args", (), {"socket": None, "instance": "vscodium"})()

    socket = _resolve_socket(args, "cursor")

    assert socket == tmp_path / "koru-autopilot-vscodium.sock"


def test_ide_doctor_uses_env_instance_when_arg_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_SOCKET", raising=False)
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "cursor-main")
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    args = type("Args", (), {"socket": None, "instance": None})()

    socket = _resolve_socket(args, "cursor")

    assert socket == tmp_path / "koru-autopilot-cursor-main.sock"


def test_ide_doctor_inferrs_instance_from_workspace_socket_when_env_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_SOCKET", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    project = tmp_path / "project"
    settings = project / ".cursor" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(
        json.dumps(
            {
                "koruAutopilot.socketPath": str(
                    tmp_path / "koru-autopilot-cursor-main.sock"
                ),
            }
        ),
        encoding="utf-8",
    )
    args = type(
        "Args",
        (),
        {"socket": None, "instance": None, "project": project},
    )()

    socket = _resolve_socket(args, "cursor")

    assert socket == tmp_path / "koru-autopilot-cursor-main.sock"
