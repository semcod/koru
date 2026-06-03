from __future__ import annotations

import subprocess
from pathlib import Path

from koru import cli_self, self_control


def test_run_self_control_reports_package_mismatch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'koru'\nversion = '9.9.9'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(self_control, "_installed_version", lambda: "0.0.1")
    monkeypatch.setattr(
        self_control,
        "_install_manager_checks",
        lambda *_args, **_kwargs: [
            self_control.SelfCheck("autopilot_install_manager", "ok", "ok")
        ],
    )
    monkeypatch.setattr(
        self_control,
        "_ecosystem_components",
        lambda *_args, **_kwargs: [
            self_control.EcosystemComponent(
                "koru_package",
                "python_package",
                "warn",
                current="0.0.1",
                expected="9.9.9",
                repair="pip install -e .",
            )
        ],
    )

    report = self_control.run_self_control(tmp_path, ide="vscodium")

    package = next(check for check in report.checks if check.name == "package_identity")
    assert package.status == "warn"
    assert "version_mismatch=true" in package.detail
    assert report.needs_repair is True
    environment = next(check for check in report.checks if check.name == "environment_profile")
    assert environment.status == "ok"
    assert "ide=vscodium" in environment.detail
    data = report.to_dict()
    assert data["ecosystem_components"][0]["name"] == "koru_package"
    assert data["update_plan"][0]["repair"] == "pip install -e ."


def test_repair_self_control_requires_yes(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'koru'\nversion = '9.9.9'\n",
        encoding="utf-8",
    )

    report = self_control.repair_self_control(tmp_path, yes=False)

    assert report.actions
    assert report.actions[0]["action"] == "refuse_without_yes"


def test_repair_self_control_runs_editable_install_when_package_mismatch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'koru'\nversion = '9.9.9'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(self_control, "_installed_version", lambda: "0.0.1")
    monkeypatch.setattr(
        self_control,
        "_install_manager_checks",
        lambda *_args, **_kwargs: [
            self_control.SelfCheck("autopilot_install_manager", "ok", "ok")
        ],
    )
    monkeypatch.setattr(self_control, "_ecosystem_components", lambda *_args, **_kwargs: [])
    commands: list[list[str]] = []

    def runner(command, cwd):  # noqa: ANN001
        commands.append(list(command))
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    report = self_control.repair_self_control(tmp_path, yes=True, runner=runner)

    assert commands
    assert commands[0][-2:] == ["-e", str(tmp_path.resolve())]
    assert any(action["action"] == "pip_install_editable" for action in report.actions)


def test_install_manager_component_reports_plugin_update_plan(monkeypatch) -> None:
    class Issue:
        def to_dict(self) -> dict[str, str]:
            return {"code": "plugin_version_mismatch", "severity": "error"}

    class Report:
        ok = False
        socket = "/tmp/koru.sock"
        package_version = "0.1.0"
        source_version = "0.1.0"
        issues = [Issue()]
        plugin = {
            "ide": "vscodium",
            "connected": True,
            "connected_version": "0.2.7",
            "connected_build_sha": "old",
            "installed_version": "0.2.8",
            "expected_version": "0.2.8",
            "expected_build_sha": "new",
        }

    monkeypatch.setattr(
        self_control,
        "collect_install_manager_report",
        lambda *_args, **_kwargs: Report(),
    )

    components = self_control._install_manager_component(
        ide="vscodium",
        socket_path=None,
    )

    plugin = next(component for component in components if component.kind == "ide_plugin")
    assert plugin.status == "warn"
    assert plugin.current == "0.2.7"
    assert plugin.expected == "0.2.8"
    assert plugin.needs_update is True
    assert plugin.repair == "koru autopilot manage --ide vscodium --fix"


def test_entrypoint_identity_accepts_global_venv_when_editable_source_matches(
    tmp_path: Path,
    monkeypatch,
) -> None:
    local = tmp_path / ".venv" / "bin" / "koru"
    global_koru = tmp_path / "global-venv" / "bin" / "koru"
    local.parent.mkdir(parents=True)
    global_koru.parent.mkdir(parents=True)
    local.write_text("#!/bin/sh\n", encoding="utf-8")
    global_koru.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(self_control.shutil, "which", lambda _name: str(global_koru))
    monkeypatch.setattr(
        self_control,
        "_installed_editable_source_root",
        lambda: tmp_path.resolve(),
    )

    check = self_control._check_entrypoint_identity(tmp_path)

    assert check.status == "ok"
    assert "editable_source_matches=true" in check.detail


def test_self_cli_accepts_json_after_subcommand(tmp_path: Path, monkeypatch, capsys) -> None:
    report = self_control.SelfControlReport(
        project=tmp_path,
        checks=[self_control.SelfCheck("package_identity", "ok", "ok")],
    )
    monkeypatch.setattr(cli_self, "run_self_control", lambda *_args, **_kwargs: report)

    rc = cli_self.self_main(["doctor", "--project", str(tmp_path), "--json"])

    captured = capsys.readouterr()
    assert rc == 0
    assert '"schema": "koru.self-control/v1"' in captured.out


def test_self_cli_accepts_json_before_subcommand(tmp_path: Path, monkeypatch, capsys) -> None:
    report = self_control.SelfControlReport(
        project=tmp_path,
        checks=[self_control.SelfCheck("package_identity", "ok", "ok")],
    )
    monkeypatch.setattr(cli_self, "run_self_control", lambda *_args, **_kwargs: report)

    rc = cli_self.self_main(["--project", str(tmp_path), "--json", "doctor"])

    captured = capsys.readouterr()
    assert rc == 0
    assert '"ok": true' in captured.out


def test_self_cli_repair_passes_yes_flag(tmp_path: Path, monkeypatch, capsys) -> None:
    report = self_control.SelfControlReport(
        project=tmp_path,
        checks=[self_control.SelfCheck("package_identity", "ok", "ok")],
    )
    calls: list[dict[str, object]] = []

    def fake_repair(*_args, **kwargs):  # noqa: ANN001, ANN202
        calls.append(dict(kwargs))
        return report

    monkeypatch.setattr(cli_self, "repair_self_control", fake_repair)

    rc = cli_self.self_main(["repair", "--project", str(tmp_path), "--yes", "--json"])

    captured = capsys.readouterr()
    assert rc == 0
    assert '"ok": true' in captured.out
    assert calls[0]["yes"] is True
