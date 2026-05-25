from __future__ import annotations

import subprocess
from pathlib import Path

from koru import cli_self
from koru import self_control


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

    report = self_control.run_self_control(tmp_path, ide="vscodium")

    package = next(check for check in report.checks if check.name == "package_identity")
    assert package.status == "warn"
    assert "version_mismatch=true" in package.detail
    assert report.needs_repair is True


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
    commands: list[list[str]] = []

    def runner(command, cwd):  # noqa: ANN001
        commands.append(list(command))
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    report = self_control.repair_self_control(tmp_path, yes=True, runner=runner)

    assert commands
    assert commands[0][-2:] == ["-e", str(tmp_path.resolve())]
    assert any(action["action"] == "pip_install_editable" for action in report.actions)


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
