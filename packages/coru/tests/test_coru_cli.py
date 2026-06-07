from __future__ import annotations

import json
import subprocess
from importlib import metadata
from pathlib import Path
from types import SimpleNamespace

import pytest

from coru import cli as coru_cli
from coru import repair_registry


@pytest.fixture(autouse=True)
def _isolated_supervisor_registry(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CORU_SUPERVISOR_STATE_DIR", str(tmp_path / "coru-supervisor"))


def test_heuristic_plan_auto() -> None:
    plan = coru_cli._heuristic_plan("run auto for windsurf-main in windsurf")
    assert plan.action == "auto"
    assert plan.ide == "windsurf"


def test_heuristic_plan_diag_routes_to_doctor() -> None:
    plan = coru_cli._heuristic_plan("zrob diagnostyke bridge")
    assert plan.action == "doctor"


def test_heuristic_plan_calibration() -> None:
    plan = coru_cli._heuristic_plan("uruchom calibration dla cursor-main")
    assert plan.action == "calibration"
    assert plan.ide == "cursor"


def test_format_calibration_probe_report_pass() -> None:
    ok, lines = coru_cli._format_calibration_probe_report(
        {
            "ok": True,
            "verification": "submit_verified",
            "winning_focus_open": "workbench.action.chat.open",
            "winning_paste": "editor.action.clipboardPasteAction",
            "winning_submit": "workbench.action.chat.submit",
        }
    )
    assert ok is True
    assert any("winning_focus_open=" in line for line in lines)


def test_format_calibration_probe_report_submit_unverified() -> None:
    ok, lines = coru_cli._format_calibration_probe_report(
        {
            "ok": False,
            "verification": "submit_unverified",
            "winning_focus_open": "workbench.action.chat.open",
            "winning_paste": "editor.action.clipboardPasteAction",
        }
    )
    assert ok is False
    assert any("Calibrate chat probe ladder" in line for line in lines)


def test_parse_drive_json_from_stdout_extracts_trailing_object() -> None:
    raw = 'noise\n{"ok": false, "verification": "submit_unverified"}\n'
    parsed = coru_cli._parse_drive_json_from_stdout(raw)
    assert parsed is not None
    assert parsed["verification"] == "submit_unverified"


def test_calibration_desktop_focus_titles_include_workspace() -> None:
    titles = coru_cli._calibration_desktop_focus_titles("cursor", workspace_name="koru")
    assert "Cursor" in titles
    assert "koru" in titles


def test_write_calibration_desktop_oql(tmp_path: Path) -> None:
    path = coru_cli._write_calibration_desktop_oql(
        ide="cursor",
        root=tmp_path,
        focus_titles=("Cursor", "koru"),
    )
    text = path.read_text(encoding="utf-8")
    assert "DESKTOP_LIST" in text
    assert 'DESKTOP_FOCUS "Cursor"' in text
    assert 'DESKTOP_FOCUS "koru"' in text
    assert "calibration-cursor-desktop.png" in text
    assert "DESKTOP_CAPTURE" not in text


def test_materialize_calibration_desktop_oql_from_template(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    scenarios = repo / "testql-scenarios"
    scenarios.mkdir(parents=True)
    (scenarios / "cursor-desktop-calibration.oql").write_text(
        "\n".join(
            [
                'SET window_title "Cursor"',
                'SET capture_path ".planfile/.koru/calibration-cursor-desktop.png"',
                "DESKTOP_LIST",
                'DESKTOP_FOCUS "${window_title}"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(repo)
    path, source = coru_cli._materialize_calibration_desktop_oql(
        ide="cursor",
        root=repo,
        focus_titles=("Cursor", "koru"),
    )
    text = path.read_text(encoding="utf-8")
    assert source.startswith("template:")
    assert 'DESKTOP_FOCUS "koru"' in text
    assert "DESKTOP_CAPTURE" not in text


def test_write_calibration_bridge_testql(tmp_path: Path) -> None:
    path = coru_cli._write_calibration_bridge_testql(
        ide="cursor",
        instance="cursor-main",
        root=tmp_path,
    )
    text = path.read_text(encoding="utf-8")
    assert "koru autopilot status" in text
    assert "cursor-main" in text


def test_format_calibration_desktop_report_error() -> None:
    lines = coru_cli._format_calibration_desktop_report(
        {"ok": False, "error": "window not found"},
        ide="cursor",
        focus_titles=("Cursor",),
    )
    assert any("desktop preflight" in line for line in lines)
    assert any("window not found" in line for line in lines)


def test_lane_calibration_runs_desktop_preflight_and_single_drive(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(coru_cli, "_diagnose_lane", lambda *_a, **_k: 0)
    monkeypatch.setattr(coru_cli, "_lane_status_raw", lambda *_a, **_k: 0)
    monkeypatch.setattr(coru_cli, "_target_plugin_rows", lambda *_a, **_k: [{"ide": "cursor"}])
    monkeypatch.setattr(
        coru_cli,
        "_run_calibration_desktop_preflight",
        lambda *_a, **_k: (True, ["[coru] calibration: desktop preflight (testql DESKTOP_*)"]),
    )
    monkeypatch.setattr(
        coru_cli,
        "_run_calibration_bridge_preflight",
        lambda *_a, **_k: (True, ["[coru] calibration: bridge preflight (testql SHELL)"]),
    )

    def fake_drive_capture(*_args, **_kwargs):
        calls.append("drive_capture")
        return 1, {"ok": False, "verification": "submit_unverified", "winning_focus_open": "x", "winning_paste": "y"}

    monkeypatch.setattr(coru_cli, "_lane_drive_capture", fake_drive_capture)
    monkeypatch.setattr(coru_cli, "_run_lane_repair", lambda *_a, **_k: None)
    monkeypatch.setattr(coru_cli, "_print_troubleshooting_log_locations", lambda *_a, **_k: None)

    rc = coru_cli._lane_calibration("cursor", "cursor-main", skip_fix=True)

    assert rc == 1
    assert calls == ["drive_capture"]


def test_calibration_command_runs_lane_calibration(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_lane_calibration(
        ide: str,
        instance: str,
        *,
        probe_prompt: str = "probe test",
        skip_fix: bool = False,
        skip_desktop: bool = False,
        skip_bridge: bool = False,
    ) -> int:
        called.update(
            {
                "ide": ide,
                "instance": instance,
                "probe_prompt": probe_prompt,
                "skip_fix": skip_fix,
                "skip_desktop": skip_desktop,
                "skip_bridge": skip_bridge,
            }
        )
        return 0

    monkeypatch.setattr(coru_cli, "_default_lane", lambda _ide, _inst: ("cursor", "cursor-main"))
    monkeypatch.setattr(
        coru_cli,
        "_resolve_calibration_lane",
        lambda ide, instance, *, explicit_ide: (ide, instance),
    )
    monkeypatch.setattr(coru_cli, "_lane_calibration", fake_lane_calibration)

    rc = coru_cli.main(
        ["calibration", "--probe-prompt", "hello-probe", "--skip-fix", "--skip-bridge"]
    )

    assert rc == 0
    assert called == {
        "ide": "cursor",
        "instance": "cursor-main",
        "probe_prompt": "hello-probe",
        "skip_fix": True,
        "skip_desktop": False,
        "skip_bridge": True,
    }


def test_calibration_is_known_command_not_text_shorthand(monkeypatch) -> None:
    called: dict[str, object] = {"heuristic": False}

    monkeypatch.setattr(coru_cli, "_lane_calibration", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(coru_cli, "_default_lane", lambda _ide, _inst: ("cursor", "cursor-main"))
    monkeypatch.setattr(
        coru_cli,
        "_resolve_calibration_lane",
        lambda ide, instance, *, explicit_ide: (ide, instance),
    )

    def fake_heuristic(text: str) -> coru_cli.Plan:
        called["heuristic"] = text
        return coru_cli.Plan(action="diagnose")

    monkeypatch.setattr(coru_cli, "_heuristic_plan", fake_heuristic)

    rc = coru_cli.main(["calibration"])
    assert rc == 0
    assert called["heuristic"] is False


def test_execute_text_uses_heuristic(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_diagnose(ide: str, instance: str, **kwargs) -> int:
        called["ide"] = ide
        called["instance"] = instance
        return 0

    monkeypatch.setattr(coru_cli, "_diagnose_lane", fake_diagnose)
    rc = coru_cli.main(["text", "status for cursor-main in cursor"])

    assert rc == 0
    assert called["ide"] == "cursor"


def test_doctor_requires_system_shell_by_default(monkeypatch, capsys) -> None:
    monkeypatch.setattr(coru_cli, "_terminal_shell_context", lambda: ("vscode", "env:VSCODE_PID.exe", True))
    rc = coru_cli.main(["doctor"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "run this from system shell" in err


def test_doctor_allow_integrated_shell_executes_lane_doctor(monkeypatch) -> None:
    called: dict[str, object] = {}

    monkeypatch.setattr(coru_cli, "_terminal_shell_context", lambda: ("vscode", "env:VSCODE_PID.exe", True))
    monkeypatch.setattr(coru_cli, "_default_lane", lambda _ide, _inst: ("cursor", "cursor-main"))

    def fake_lane_doctor(ide: str, instance: str, *, fix: bool = False, probe: bool = False, probe_prompt: str = "test") -> int:
        called["ide"] = ide
        called["instance"] = instance
        called["fix"] = fix
        called["probe"] = probe
        called["probe_prompt"] = probe_prompt
        return 0

    monkeypatch.setattr(coru_cli, "_lane_doctor", fake_lane_doctor)

    rc = coru_cli.main([
        "doctor",
        "--allow-integrated-shell",
        "--fix",
        "--probe",
        "--probe-prompt",
        "probe-ok",
    ])
    assert rc == 0
    assert called == {
        "ide": "cursor",
        "instance": "cursor-main",
        "fix": True,
        "probe": True,
        "probe_prompt": "probe-ok",
    }


def test_fetch_manage_report_uses_supported_manage_json_args(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(coru_cli, "_koru_exec_argv", lambda: ["koru"])

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(cmd, 0, stdout='{"ok": true, "issues": []}', stderr="")

    monkeypatch.setattr(coru_cli.subprocess, "run", fake_run)

    report = coru_cli._fetch_manage_report("vscodium", "vscodium")

    assert report == {"ok": True, "issues": []}
    assert captured["cmd"] == ["koru", "autopilot", "manage", "--ide", "vscodium", "--format", "json"]


def test_collect_lane_repair_problems_merges_all_sources(monkeypatch, tmp_path) -> None:
    readiness = SimpleNamespace(
        check_runtime_consistency=lambda *_args, **_kwargs: SimpleNamespace(
            issues=[
                SimpleNamespace(
                    code="runtime_mismatch",
                    severity="fail",
                    message="runtime mismatch",
                    fix_command="fix runtime",
                )
            ]
        ),
        check_lane_terminal_socket_alignment=lambda **_kwargs: SimpleNamespace(
            issues=[
                SimpleNamespace(
                    code="lane_socket_mismatch",
                    severity="warn",
                    message="lane socket mismatch",
                    fix_command=None,
                )
            ]
        ),
    )
    payload = {
        "socket": str(tmp_path / "socket"),
        "drive": {"ok": False, "reason": "submit_failed"},
    }

    monkeypatch.setattr(
        coru_cli,
        "_fetch_manage_report",
        lambda _ide, _instance: {
            "daemon": {"running": True},
            "plugin": {"connected": False, "expected_build_sha": "expected"},
        },
    )
    monkeypatch.setattr(
        coru_cli,
        "_lane_status_payload",
        lambda _ide, _instance, *, payload=None: {
            "plugins": [{"ide": "vscodium", "buildSha": "actual"}],
            "console_logs": [{"data": {"ok": False, "reason": "sentinel unchanged"}}],
        },
    )
    monkeypatch.setattr(coru_cli, "_import_koru_readiness_module", lambda: readiness)
    monkeypatch.setattr(coru_cli, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(coru_cli, "_terminal_shell_context", lambda: ("vscodium", "test", True))
    monkeypatch.setattr(coru_cli, "_terminal_host_kind", lambda: "integrated")

    problems = coru_cli._collect_lane_repair_problems("vscodium", "vscodium", payload=payload)
    codes = {problem.code for problem in problems}

    assert "runtime_mismatch" in codes
    assert "lane_socket_mismatch" in codes
    assert any(problem.context.get("source") == "readiness.runtime" for problem in problems)
    assert any(problem.context.get("source") == "readiness.lane_alignment" for problem in problems)


def test_lane_doctor_fix_uses_registry_before_fallback(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(coru_cli, "_diagnose_lane", lambda _ide, _instance, skip_ensure=False: 1)
    monkeypatch.setattr(coru_cli, "_koru_autopilot_env_payload", lambda _ide, _instance: {"socket": "/tmp/sock"})
    monkeypatch.setattr(
        coru_cli,
        "_run_lane_repair",
        lambda _ide, _instance, *, payload=None, **_kwargs: calls.append(
            f"registry:{payload['socket']}"
        )
        or type(
            "Plan",
            (),
            {"resolved": True},
        )(),
    )
    monkeypatch.setattr(coru_cli, "_lane_status_raw", lambda _ide, _instance: calls.append("status") or 0)
    monkeypatch.setattr(
        coru_cli,
        "_run_koru_lane",
        lambda _ide, _instance, args: calls.append("fallback") or 0,
    )

    rc = coru_cli._lane_doctor("vscodium", "vscodium", fix=True)

    assert rc == 0
    assert calls == ["registry:/tmp/sock", "status"]


def test_ensure_without_install_missing(monkeypatch) -> None:
    monkeypatch.setattr(coru_cli, "_tool_available", lambda _binary, _module: False)
    rc = coru_cli.main(["ensure"])
    assert rc == 1


def test_ensure_with_install_calls_pip(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_run(cmd, check):
        called["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(
        coru_cli,
        "_tool_available",
        lambda binary, _module: binary == "koru",
    )
    monkeypatch.setattr(coru_cli, "_project_venv_python", lambda: None)
    monkeypatch.setattr(coru_cli.subprocess, "run", fake_run)

    rc = coru_cli.main(["ensure", "--install"])
    assert rc == 0
    assert called["cmd"][0:4] == [coru_cli.sys.executable, "-m", "pip", "install"]


def test_ensure_with_install_prefers_project_venv_python(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_run(cmd, check):
        called["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(
        coru_cli,
        "_tool_available",
        lambda binary, _module: binary == "koru",
    )
    monkeypatch.setattr(coru_cli, "_project_venv_python", lambda: "/tmp/repo/.venv/bin/python")
    monkeypatch.setattr(coru_cli.subprocess, "run", fake_run)

    rc = coru_cli.main(["ensure", "--install"])
    assert rc == 0
    assert called["cmd"][0:4] == ["/tmp/repo/.venv/bin/python", "-m", "pip", "install"]


def test_setup_runs_environment_prepare(monkeypatch) -> None:
    monkeypatch.setattr(coru_cli, "_ensure_commands", lambda install: 0)
    monkeypatch.setattr(coru_cli, "_project_venv_python", lambda: "/tmp/repo/.venv/bin/python")
    rc = coru_cli.main(["setup"])
    assert rc == 0


def test_distribution_version_not_installed(monkeypatch) -> None:
    def fake_version(_name: str) -> str:
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(coru_cli.metadata, "version", fake_version)
    assert coru_cli._distribution_version("missing-pkg") == "not-installed"


def test_distribution_version_for_bundled_coru_falls_back_to_koru(monkeypatch) -> None:
    def fake_version(name: str) -> str:
        if name == "koru":
            return "0.1.312"
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(coru_cli.metadata, "version", fake_version)
    assert coru_cli._distribution_version("coru") == "0.1.312"


def test_print_runtime_versions(monkeypatch, capsys) -> None:
    monkeypatch.setattr(coru_cli, "_distribution_version", lambda name: "0.1.0" if name == "coru" else "0.1.308")
    coru_cli._print_runtime_versions()
    out = capsys.readouterr().out.strip()
    assert out == "versions: coru=0.1.0 koru=0.1.308"


def test_version_flag_prints_and_exits(monkeypatch, capsys) -> None:
    monkeypatch.setattr(coru_cli, "_distribution_version", lambda name: "0.1.0" if name == "coru" else "0.1.308")
    rc = coru_cli.main(["-V"])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    assert out == "versions: coru=0.1.0 koru=0.1.308"


def test_verbose_no_args_runs_autonomy_chain(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_execute_plans(plans, *, shell: str, context=None, announce: bool = False) -> int:
        called["actions"] = [plan.action for plan in plans]
        called["shell"] = shell
        called["announce"] = announce
        return 0

    monkeypatch.setattr(coru_cli, "_execute_plans", fake_execute_plans)
    rc = coru_cli.main(["--verbose"])
    assert rc == 0
    assert called == {
        "actions": ["ensure", "lane", "manage", "diagnose", "auto"],
        "shell": "bash",
        "announce": True,
    }


def test_local_install_target_koruenv() -> None:
    target = coru_cli._local_install_target("koruenv")
    assert target is not None
    assert target.endswith("/packages/koruenv")


def test_tool_argv_falls_back_to_local_koruenv_source(monkeypatch) -> None:
    monkeypatch.setattr(coru_cli, "_binary_path", lambda _name: None)
    monkeypatch.setattr(coru_cli, "_python_module_exists", lambda _name: False)

    argv = coru_cli._tool_argv("koruenv", "koruenv.cli", ["status", "cursor", "cursor-main"])

    assert argv[0:2] == [coru_cli.sys.executable, "-c"]
    assert "packages/koruenv/src" in argv[2]
    assert argv[-3:] == ["status", "cursor", "cursor-main"]


def test_ensure_accepts_local_source_fallback(monkeypatch) -> None:
    monkeypatch.setattr(coru_cli, "_binary_path", lambda _name: None)
    monkeypatch.setattr(coru_cli, "_python_module_exists", lambda _name: False)

    rc = coru_cli.main(["ensure"])

    assert rc == 0


def test_binary_path_prefers_repo_venv_over_global_path(monkeypatch, tmp_path) -> None:
    repo = tmp_path / "repo"
    bin_dir = repo / ".venv" / "bin"
    bin_dir.mkdir(parents=True)
    local_bin = bin_dir / "koru"
    local_bin.write_text("#!/bin/sh\n", encoding="utf-8")
    local_bin.chmod(0o755)

    monkeypatch.setattr(coru_cli, "_repo_root", lambda: repo)
    monkeypatch.setattr(coru_cli.shutil, "which", lambda _name: "/usr/bin/koru")

    assert coru_cli._binary_path("koru") == str(local_bin)


def test_maybe_reexec_into_project_python_skips_when_same_interpreter(monkeypatch) -> None:
    monkeypatch.delenv("CORU_DISABLE_AUTO_REEXEC", raising=False)
    monkeypatch.delenv("CORU_REEXEC_DONE", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(coru_cli, "_project_venv_python", lambda: "/tmp/repo/.venv/bin/python")
    monkeypatch.setattr(coru_cli.sys, "executable", "/tmp/repo/.venv/bin/python")

    assert coru_cli._maybe_reexec_into_project_python(["status"]) is False


def test_maybe_reexec_into_project_python_executes(monkeypatch, tmp_path) -> None:
    target = tmp_path / ".venv" / "bin" / "python"
    target.parent.mkdir(parents=True)
    target.write_text("", encoding="utf-8")

    source_dir = tmp_path / "packages" / "coru" / "src"
    source_dir.mkdir(parents=True)

    captured: dict[str, object] = {}

    def fake_execve(path, argv, env):
        captured["path"] = path
        captured["argv"] = list(argv)
        captured["env"] = dict(env)
        raise RuntimeError("exec-called")

    monkeypatch.delenv("CORU_DISABLE_AUTO_REEXEC", raising=False)
    monkeypatch.delenv("CORU_REEXEC_DONE", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(coru_cli, "_project_venv_python", lambda: str(target))
    monkeypatch.setattr(coru_cli.sys, "executable", "/tmp/global/bin/python")
    monkeypatch.setattr(coru_cli, "_local_module_source_dir", lambda _module: source_dir)
    monkeypatch.setattr(coru_cli.os, "execve", fake_execve)

    with pytest.raises(RuntimeError, match="exec-called"):
        coru_cli._maybe_reexec_into_project_python(["status"])

    assert captured["path"] == str(target)
    assert captured["argv"][0] == str(target)
    assert "status" in captured["argv"]
    assert captured["env"]["CORU_REEXEC_DONE"] == "1"


def test_maybe_reexec_into_project_python_uses_venv_symlink_path(monkeypatch, tmp_path) -> None:
    base_python = tmp_path / "miniconda" / "bin" / "python"
    base_python.parent.mkdir(parents=True)
    base_python.write_text("", encoding="utf-8")
    target = tmp_path / ".venv" / "bin" / "python"
    target.parent.mkdir(parents=True)
    target.symlink_to(base_python)
    source_dir = tmp_path / "packages" / "coru" / "src"
    source_dir.mkdir(parents=True)
    captured: dict[str, object] = {}

    def fake_execve(path, argv, env):
        captured["path"] = path
        captured["argv"] = list(argv)
        captured["env"] = dict(env)
        raise RuntimeError("exec-called")

    monkeypatch.delenv("CORU_DISABLE_AUTO_REEXEC", raising=False)
    monkeypatch.delenv("CORU_REEXEC_DONE", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(coru_cli, "_project_venv_python", lambda: str(target))
    monkeypatch.setattr(coru_cli.sys, "executable", str(base_python))
    monkeypatch.setattr(coru_cli.sys, "prefix", str(tmp_path / "miniconda"))
    monkeypatch.setattr(coru_cli, "_local_module_source_dir", lambda _module: source_dir)
    monkeypatch.setattr(coru_cli.os, "execve", fake_execve)

    with pytest.raises(RuntimeError, match="exec-called"):
        coru_cli._maybe_reexec_into_project_python(["status"])

    assert captured["path"] == str(target)
    assert captured["argv"][0] == str(target)


def test_build_plan_chain_for_auto_intent() -> None:
    plans = coru_cli._build_plan_chain("run auto for cursor-main in cursor")
    assert [p.action for p in plans] == ["ensure", "lane", "manage", "diagnose", "auto"]


def test_build_plan_chain_for_polish_refactor_intent() -> None:
    plans = coru_cli._build_plan_chain("start refaktoryzacje")
    assert [p.action for p in plans] == ["ensure", "lane", "manage", "diagnose", "auto"]


def test_text_executes_chain(monkeypatch) -> None:
    called: list[str] = []

    def fake_execute(plans, **_kwargs):
        called.extend([p.action for p in plans])
        return 0

    monkeypatch.setattr(coru_cli, "_execute_plans", fake_execute)
    rc = coru_cli.main(["text", "start auto for windsurf-main in windsurf"])
    assert rc == 0
    assert called == ["ensure", "lane", "manage", "diagnose", "auto"]


def test_main_shorthand_routes_to_text(monkeypatch) -> None:
    called: list[str] = []

    def fake_execute(plans, **_kwargs):
        called.extend([p.action for p in plans])
        return 0

    monkeypatch.setattr(coru_cli, "_execute_plans", fake_execute)
    rc = coru_cli.main(["run", "auto", "for", "cursor-main", "in", "cursor"])
    assert rc == 0
    assert called == ["ensure", "lane", "manage", "diagnose", "auto"]


def test_auto_without_lane_uses_defaults(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_lane_auto(ide: str, instance: str, extra_args) -> int:
        called["ide"] = ide
        called["instance"] = instance
        called["extra_args"] = list(extra_args)
        return 0

    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("CURSOR_AGENT", raising=False)
    monkeypatch.delenv("CHROME_DESKTOP", raising=False)
    monkeypatch.setattr(coru_cli, "_repo_root", lambda: None)
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: None)
    monkeypatch.setattr(
        coru_cli,
        "_auto_readiness_gate",
        lambda ide, instance: coru_cli.AutoReadiness(0, ide, instance),
    )
    monkeypatch.setattr(coru_cli, "_lane_auto", fake_lane_auto)
    rc = coru_cli.main(["auto"])
    assert rc == 0
    assert called["ide"] == "auto"
    assert called["instance"] == "main"
    assert called["extra_args"] == []


def test_lane_auto_injects_agent_lane(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run_koru_lane(ide: str, instance: str, koru_args) -> int:
        captured["ide"] = ide
        captured["instance"] = instance
        captured["koru_args"] = list(koru_args)
        return 0

    monkeypatch.setattr(coru_cli, "_run_koru_lane", fake_run_koru_lane)
    rc = coru_cli._lane_auto("cursor", "cursor-main", ["--max-cycles", "1"])
    assert rc == 0
    command = captured["koru_args"]
    assert command[0] == "auto"
    assert "--agent-lane" in command
    idx = command.index("--agent-lane")
    assert command[idx + 1] == "cursor-main"
    assert "--max-cycles" in command


def test_lane_auto_injects_project_from_supervisor_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "koru"
    project.mkdir()
    monkeypatch.setenv("CORU_SUPERVISOR_STATE_DIR", str(tmp_path / "state"))
    (tmp_path / "state").mkdir()
    from coru.supervisor.registry import register_lane

    register_lane(
        ide="cursor",
        instance="cursor-main",
        project=str(project),
        set_active=True,
    )

    captured: dict[str, object] = {}

    def fake_run_with_resolved_lane_env(command, *, ide: str, instance: str) -> int:
        captured["command"] = list(command)
        captured["ide"] = ide
        captured["instance"] = instance
        return 0

    monkeypatch.setattr(coru_cli, "_koru_exec_argv", lambda: ["koru"])
    monkeypatch.setattr(coru_cli, "_run_with_resolved_lane_env", fake_run_with_resolved_lane_env)
    rc = coru_cli._lane_auto("cursor", "cursor-main", [])
    assert rc == 0
    command = captured["command"]
    assert "--project" in command
    assert command[command.index("--project") + 1] == str(project.resolve())


def test_run_auto_with_readiness_aborts_before_cycle(monkeypatch) -> None:
    called: dict[str, bool] = {"auto": False}

    def fake_lane_auto(ide: str, instance: str, extra_args) -> int:
        called["auto"] = True
        return 0

    monkeypatch.setattr(coru_cli, "_auto_readiness_gate", lambda _ide, _instance: coru_cli.AutoReadiness(7, "cursor", "cursor-main"))
    monkeypatch.setattr(coru_cli, "_lane_auto", fake_lane_auto)

    rc = coru_cli._run_auto_with_readiness("cursor", "cursor-main", [])

    assert rc == 7
    assert called["auto"] is False


def test_run_auto_with_readiness_continues_for_keyboard_fallback(monkeypatch, capsys) -> None:
    captured: dict[str, object] = {}

    def fake_lane_auto(ide: str, instance: str, extra_args) -> int:
        captured["ide"] = ide
        captured["instance"] = instance
        captured["extra_args"] = list(extra_args)
        return 0

    monkeypatch.setenv("KORU_AUTOPILOT_KEYBOARD_IF_NO_PLUGIN", "1")
    monkeypatch.setattr(
        coru_cli,
        "_auto_readiness_gate",
        lambda _ide, _instance: coru_cli.AutoReadiness(
            7,
            "vscodium",
            "vscodium",
            reason="plugin",
        ),
    )
    monkeypatch.setattr(
        coru_cli,
        "_lane_status_payload",
        lambda _ide, _instance: {
            "daemon": {"running": True},
            "plugins": [],
            "selected_backend": "wtype",
        },
    )
    monkeypatch.setattr(coru_cli, "_lane_auto", fake_lane_auto)

    rc = coru_cli._run_auto_with_readiness("vscodium", "vscodium", ["--max-cycles", "1"])

    assert rc == 0
    assert captured == {
        "ide": "vscodium",
        "instance": "vscodium",
        "extra_args": ["--max-cycles", "1"],
    }
    assert "keyboard fallback is enabled" in capsys.readouterr().err


def test_run_auto_with_readiness_still_blocks_plugin_failure_without_fallback(
    monkeypatch,
) -> None:
    called: dict[str, bool] = {"auto": False}

    def fake_lane_auto(ide: str, instance: str, extra_args) -> int:
        called["auto"] = True
        return 0

    monkeypatch.delenv("KORU_AUTOPILOT_ALLOW_KEYBOARD_FALLBACK", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_PREFER_KEYBOARD", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_VISIBLE_TYPING", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_KEYBOARD_IF_NO_PLUGIN", raising=False)
    monkeypatch.setattr(
        coru_cli,
        "_auto_readiness_gate",
        lambda _ide, _instance: coru_cli.AutoReadiness(
            7,
            "vscodium",
            "vscodium",
            reason="plugin",
        ),
    )
    monkeypatch.setattr(
        coru_cli,
        "_lane_status_payload",
        lambda _ide, _instance: {
            "daemon": {"running": True},
            "plugins": [],
            "selected_backend": "wtype",
        },
    )
    monkeypatch.setattr(coru_cli, "_lane_auto", fake_lane_auto)

    rc = coru_cli._run_auto_with_readiness("vscodium", "vscodium", [])

    assert rc == 7
    assert called["auto"] is False


def test_run_auto_with_readiness_uses_resolved_lane(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_lane_auto(ide: str, instance: str, extra_args) -> int:
        captured["ide"] = ide
        captured["instance"] = instance
        captured["extra_args"] = list(extra_args)
        return 0

    monkeypatch.setattr(
        coru_cli,
        "_auto_readiness_gate",
        lambda _ide, _instance: coru_cli.AutoReadiness(0, "cursor", "cursor-main"),
    )
    monkeypatch.setattr(coru_cli, "_lane_auto", fake_lane_auto)

    rc = coru_cli._run_auto_with_readiness("auto", "main", ["--max-cycles", "1"])

    assert rc == 0
    assert captured == {"ide": "cursor", "instance": "cursor-main", "extra_args": ["--max-cycles", "1"]}


def test_auto_readiness_gate_repairs_socket_daemon_and_plugin(monkeypatch) -> None:
    calls: list[str] = []
    statuses = iter([1, 1, 0])

    monkeypatch.setattr(
        coru_cli,
        "_koru_autopilot_env_payload",
        lambda _ide, _instance: {"ide": "cursor", "instance": "cursor-main", "source": "test"},
    )
    monkeypatch.setattr(
        coru_cli,
        "_diagnose_runtime_consistency",
        lambda _ide, _instance, _payload: calls.append("consistency") or 0,
    )
    monkeypatch.setattr(coru_cli, "_lane_status_raw", lambda _ide, _instance: calls.append("status") or next(statuses))
    monkeypatch.setattr(coru_cli, "_gc_stale_lane_socket", lambda _ide, _instance: calls.append("gc") or 0)
    monkeypatch.setattr(coru_cli, "_ensure_daemon_running", lambda _ide, _instance: calls.append("daemon") or 0)
    monkeypatch.setattr(
        coru_cli,
        "_run_lane_repair",
        lambda _ide, _instance, *, payload=None: repair_registry.RepairPlan(problems=(), attempts=(), resolved=True),
    )
    monkeypatch.setattr(coru_cli, "_terminal_shell_context", lambda: (None, "none", False))
    monkeypatch.setattr(coru_cli, "_attempt_plugin_self_heal", lambda _ide, _instance, **_kwargs: calls.append("heal") or 0)

    readiness = coru_cli._auto_readiness_gate("auto", "main")

    assert readiness == coru_cli.AutoReadiness(0, "cursor", "cursor-main")
    assert calls == ["consistency", "status", "gc", "daemon", "status", "heal", "status"]


def test_auto_readiness_gate_blocks_workspace_mismatch(monkeypatch, tmp_path: Path) -> None:
    project = tmp_path / "repo"
    project.mkdir()
    socket_path = tmp_path / "koru-autopilot-cursor-main.sock"
    issue = type(
        "Issue",
        (),
        {
            "code": "plugin_workspace_mismatch",
            "severity": "fail",
            "message": "wrong workspace",
            "fix_command": "connect correct workspace",
        },
    )()
    failed = type("Result", (), {"ok": False, "issues": (issue,), "primary_fix": "connect correct workspace"})()
    ok = type("Result", (), {"ok": True, "issues": (), "primary_fix": None})()

    class FakeReadiness:
        @staticmethod
        def check_daemon_client_alignment(status, *, project, socket_path):
            return ok

        @staticmethod
        def check_workspace_socket_ownership(project, socket_path, status, *, autopilot_ide):
            return failed

        @staticmethod
        def check_lane_terminal_socket_alignment(*, autopilot_ide, lane_instance, socket_path, **_kwargs):
            return ok

        @staticmethod
        def format_readiness_lines(result, *, prefix=""):
            return [f"{prefix}: [{i.severity.upper()}] {i.code}: {i.message}" for i in result.issues]

        @staticmethod
        def apply_socket_ownership_repairs(project, socket_path, readiness):
            return []

    monkeypatch.setattr(coru_cli, "_repo_root", lambda: project)
    monkeypatch.setattr(coru_cli, "_import_koru_readiness_module", lambda: FakeReadiness)
    monkeypatch.setattr(
        coru_cli,
        "_koru_autopilot_env_payload",
        lambda _ide, _instance: {"ide": "cursor", "instance": "cursor-main", "socket": str(socket_path)},
    )
    monkeypatch.setattr(coru_cli, "_diagnose_runtime_consistency", lambda _ide, _instance, _payload: 0)
    monkeypatch.setattr(coru_cli, "_lane_status_raw", lambda _ide, _instance: 0)
    monkeypatch.setattr(coru_cli, "_ensure_daemon_running", lambda _ide, _instance: 0)
    monkeypatch.setattr(coru_cli, "_lane_status_payload", lambda _ide, _instance, *, payload=None: {"plugins": []})
    monkeypatch.setattr(
        coru_cli,
        "_run_lane_repair",
        lambda _ide, _instance, *, payload=None: repair_registry.RepairPlan(problems=(), attempts=(), resolved=True),
    )

    readiness = coru_cli._auto_readiness_gate("cursor", "cursor-main")

    assert readiness == coru_cli.AutoReadiness(1, "cursor", "cursor-main")


def test_auto_readiness_gate_restarts_stale_daemon(monkeypatch, tmp_path: Path) -> None:
    project = tmp_path / "repo"
    project.mkdir()
    socket_path = tmp_path / "koru-autopilot-cursor-main.sock"
    calls: list[str] = []
    issue = type(
        "Issue",
        (),
        {
            "code": "daemon_version_mismatch",
            "severity": "fail",
            "message": "daemon old != client new",
            "fix_command": "koru autopilot shutdown && koru auto",
        },
    )()
    failed = type("Result", (), {"ok": False, "issues": (issue,), "primary_fix": "restart"})()
    ok = type("Result", (), {"ok": True, "issues": (), "primary_fix": None})()

    class FakeReadiness:
        @staticmethod
        def check_daemon_client_alignment(status, *, project, socket_path):
            calls.append(f"daemon:{status['version']}")
            return failed if status["version"] == "old" else ok

        @staticmethod
        def check_workspace_socket_ownership(project, socket_path, status, *, autopilot_ide):
            calls.append(f"workspace:{status['version']}")
            return ok

        @staticmethod
        def check_lane_terminal_socket_alignment(*, autopilot_ide, lane_instance, socket_path, **kwargs):
            assert kwargs == {
                "terminal_ide": "vscodium",
                "terminal_integrated": True,
                "terminal_kind": "integrated",
            }
            calls.append("lane")
            return ok

        @staticmethod
        def format_readiness_lines(result, *, prefix=""):
            return [f"{prefix}: [{i.severity.upper()}] {i.code}: {i.message}" for i in result.issues]

    statuses = iter([{"version": "old"}, {"version": "new"}])

    monkeypatch.setattr(coru_cli, "_repo_root", lambda: project)
    monkeypatch.setattr(coru_cli, "_import_koru_readiness_module", lambda: FakeReadiness)
    monkeypatch.setattr(coru_cli, "_terminal_shell_context", lambda: ("vscodium", "env:VSCODE_*", True))
    monkeypatch.setattr(
        coru_cli,
        "_lane_status_payload",
        lambda _ide, _instance, *, payload=None: next(statuses),
    )
    monkeypatch.setattr(
        coru_cli,
        "_run_koru_lane",
        lambda _ide, _instance, args: calls.append(" ".join(args)) or 0,
    )
    monkeypatch.setattr(coru_cli, "_ensure_daemon_running", lambda _ide, _instance: calls.append("start") or 0)

    rc = coru_cli._auto_ownership_gate(
        "cursor",
        "cursor-main",
        payload={"socket": str(socket_path)},
    )

    assert rc == 0
    assert calls == [
        "daemon:old",
        "autopilot shutdown",
        "start",
        "daemon:new",
        "workspace:new",
        "lane",
    ]


def test_auto_ownership_allows_cross_terminal_when_target_plugin_connected(monkeypatch, tmp_path: Path) -> None:
    project = tmp_path / "repo"
    project.mkdir()
    socket_path = tmp_path / "koru-autopilot-cursor-main.sock"
    ok = type("Result", (), {"ok": True, "issues": (), "primary_fix": None})()
    captured: dict[str, object] = {}

    class FakeReadiness:
        @staticmethod
        def check_daemon_client_alignment(status, *, project, socket_path):
            return ok

        @staticmethod
        def check_workspace_socket_ownership(project, socket_path, status, *, autopilot_ide):
            return ok

        @staticmethod
        def check_lane_terminal_socket_alignment(*, autopilot_ide, lane_instance, socket_path, **kwargs):
            captured.update(kwargs)
            if kwargs.get("terminal_integrated"):
                issue = type(
                    "Issue",
                    (),
                    {
                        "code": "terminal_lane_mismatch",
                        "severity": "fail",
                        "message": "wrong terminal",
                        "fix_command": "use target terminal",
                    },
                )()
                return type("Result", (), {"ok": False, "issues": (issue,), "primary_fix": "use target terminal"})()
            return ok

        @staticmethod
        def format_readiness_lines(result, *, prefix=""):
            return [f"{prefix}: [{i.severity.upper()}] {i.code}: {i.message}" for i in result.issues]

    monkeypatch.setattr(coru_cli, "_repo_root", lambda: project)
    monkeypatch.setattr(coru_cli, "_import_koru_readiness_module", lambda: FakeReadiness)
    monkeypatch.setattr(coru_cli, "_terminal_shell_context", lambda: ("vscodium", "env:VSCODE_*", True))
    monkeypatch.setattr(
        coru_cli,
        "_lane_status_payload",
        lambda _ide, _instance, *, payload=None: {
            "plugins": [
                {
                    "ide": "cursor",
                    "workspaceFolders": [str(project)],
                }
            ]
        },
    )

    rc = coru_cli._auto_ownership_gate(
        "cursor",
        "cursor-main",
        payload={"socket": str(socket_path)},
    )

    assert rc == 0
    assert captured["terminal_ide"] == "vscodium"
    assert captured["terminal_integrated"] is False


def test_diagnose_runtime_consistency_passes_coru_terminal_context(monkeypatch, tmp_path: Path) -> None:
    ok = type("Result", (), {"ok": True, "issues": (), "primary_fix": None})()
    captured: dict[str, object] = {}

    class FakeReadiness:
        @staticmethod
        def check_runtime_consistency(project, *, launcher_executable, strict=False):
            return ok

        @staticmethod
        def check_lane_terminal_socket_alignment(**kwargs):
            captured.update(kwargs)
            return ok

        @staticmethod
        def format_readiness_lines(result, *, prefix=""):
            return []

    monkeypatch.setattr(coru_cli, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(coru_cli, "_import_koru_readiness_module", lambda: FakeReadiness)
    monkeypatch.setattr(coru_cli, "_terminal_shell_context", lambda: ("vscodium", "env:VSCODE_*", True))

    rc = coru_cli._diagnose_runtime_consistency("vscodium", "vscodium", None)

    assert rc == 0
    assert captured["autopilot_ide"] == "vscodium"
    assert captured["lane_instance"] == "vscodium"
    assert captured["terminal_ide"] == "vscodium"
    assert captured["terminal_integrated"] is True


def test_auto_without_lane_uses_terminal_hint(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_lane_auto(ide: str, instance: str, extra_args) -> int:
        called["ide"] = ide
        called["instance"] = instance
        return 0

    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    for name in (
        "CHROME_DESKTOP",
        "GIO_LAUNCHED_DESKTOP_FILE",
        "TERM_PROGRAM",
        "TERM_PROGRAM_VERSION",
        "VSCODE_CODE_CACHE_PATH",
        "VSCODE_NLS_CONFIG",
        "VSCODE_PID",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("CURSOR_AGENT", "1")
    monkeypatch.setattr(coru_cli, "_repo_root", lambda: None)
    monkeypatch.setattr(
        coru_cli,
        "_auto_readiness_gate",
        lambda ide, instance: coru_cli.AutoReadiness(0, ide, instance),
    )
    monkeypatch.setattr(coru_cli, "_lane_auto", fake_lane_auto)
    rc = coru_cli.main(["auto"])
    assert rc == 0
    assert called == {"ide": "cursor", "instance": "cursor"}


def test_auto_explicit_cursor_lane_overrides_stale_env(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_run_auto_with_readiness(ide: str, instance: str, extra_args) -> int:
        called["ide"] = ide
        called["instance"] = instance
        called["extra_args"] = list(extra_args)
        return 0

    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "vscodium")
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscodium")
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: "cursor")
    monkeypatch.setattr(coru_cli, "_run_auto_with_readiness", fake_run_auto_with_readiness)

    rc = coru_cli.main(["auto", "cursor", "cursor-main", "--", "--max-cycles", "1"])

    assert rc == 0
    assert called == {
        "ide": "cursor",
        "instance": "cursor-main",
        "extra_args": ["--max-cycles", "1"],
    }


def test_project_ide_settings_scope_default_instance(monkeypatch, tmp_path) -> None:
    (tmp_path / ".koru" / "cursor").mkdir(parents=True)
    (tmp_path / ".koru" / "cursor" / "settings.json").write_text(
        json.dumps({"instance": "cursor-main"}),
        encoding="utf-8",
    )
    (tmp_path / ".koru" / "vscodium").mkdir(parents=True)
    (tmp_path / ".koru" / "vscodium" / "settings.json").write_text(
        json.dumps({"instance": "vscodium"}),
        encoding="utf-8",
    )

    from coru.supervisor.registry import register_lane

    register_lane(
        ide="vscodium",
        instance="vscodium",
        project=str(tmp_path),
        set_active=True,
    )
    monkeypatch.setattr(coru_cli, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: "cursor")

    assert coru_cli._default_lane(None, None) == ("cursor", "cursor-main")


def test_auto_explicit_lane_writes_project_ide_settings(monkeypatch, tmp_path) -> None:
    called: dict[str, object] = {}

    def fake_run_auto_with_readiness(ide: str, instance: str, extra_args) -> int:
        called["ide"] = ide
        called["instance"] = instance
        called["extra_args"] = list(extra_args)
        return 0

    monkeypatch.setattr(coru_cli, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: None)
    monkeypatch.setattr(coru_cli, "_run_auto_with_readiness", fake_run_auto_with_readiness)

    rc = coru_cli.main(["auto", "cursor", "cursor-main"])

    settings_path = tmp_path / ".koru" / "cursor" / "settings.json"
    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    assert rc == 0
    assert called == {"ide": "cursor", "instance": "cursor-main", "extra_args": []}
    assert payload["ide"] == "cursor"
    assert payload["instance"] == "cursor-main"
    assert payload["project"] == str(tmp_path)


def test_polish_refactor_defaults_without_windsurf(monkeypatch) -> None:
    resolved: list[tuple[str, str, str]] = []

    def fake_execute(plans, **_kwargs):
        for plan in plans:
            resolved_plan = coru_cli._resolve_defaults(plan)
            resolved.append((resolved_plan.action, resolved_plan.ide, resolved_plan.instance))
        return 0

    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.setattr(coru_cli, "_repo_root", lambda: None)
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: None)
    monkeypatch.setattr(coru_cli, "_execute_plans", fake_execute)
    rc = coru_cli.main(["text", "start refaktoryzacje"])
    assert rc == 0
    assert resolved[-1] == ("auto", "auto", "main")


def test_lane_status_defaults_can_use_env(monkeypatch) -> None:
    called: dict[str, str] = {}

    def fake_lane_status(ide: str, instance: str) -> int:
        called["ide"] = ide
        called["instance"] = instance
        return 0

    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "cursor")
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "cursor-main")
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: None)
    monkeypatch.setattr(coru_cli, "_lane_status", fake_lane_status)

    rc = coru_cli.main(["lane-status"])
    assert rc == 0
    assert called == {"ide": "cursor", "instance": "cursor-main"}


def test_lane_status_passes_resolved_koru_binary(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(coru_cli, "_koru_exec_argv", lambda: ["/tmp/repo/.venv/bin/koru"])
    monkeypatch.setattr(coru_cli, "_koru_autopilot_env_payload", lambda _ide, _instance: None)

    def fake_run_with_resolved_lane_env(command, *, ide: str, instance: str) -> int:
        captured["command"] = list(command)
        captured["ide"] = ide
        captured["instance"] = instance
        return 0

    monkeypatch.setattr(coru_cli, "_run_with_resolved_lane_env", fake_run_with_resolved_lane_env)

    rc = coru_cli._lane_status("cursor", "cursor-main")

    assert rc == 0
    assert captured["command"] == [
        "/tmp/repo/.venv/bin/koru",
        "autopilot",
        "status",
        "--ide",
        "cursor",
        "--explain",
    ]


def test_lane_status_uses_koruenv_run_for_module_koru(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(coru_cli, "_koru_exec_argv", lambda: ["/tmp/python", "-m", "koru.cli"])
    monkeypatch.setattr(coru_cli, "_koru_autopilot_env_payload", lambda _ide, _instance: None)

    def fake_run_with_resolved_lane_env(command, *, ide: str, instance: str) -> int:
        captured["command"] = list(command)
        return 0

    monkeypatch.setattr(coru_cli, "_run_with_resolved_lane_env", fake_run_with_resolved_lane_env)

    rc = coru_cli._lane_status("cursor", "cursor-main")

    assert rc == 0
    assert captured["command"] == [
        "/tmp/python",
        "-m",
        "koru.cli",
        "autopilot",
        "status",
        "--ide",
        "cursor",
        "--explain",
    ]


def test_terminal_hint_overrides_stale_env_ide(monkeypatch) -> None:
    called: dict[str, str] = {}

    def fake_diagnose(ide: str, instance: str, **kwargs) -> int:
        called["ide"] = ide
        called["instance"] = instance
        return 0

    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "windsurf")
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "windsurf-main")
    monkeypatch.setattr(coru_cli, "_repo_root", lambda: None)
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: "cursor")
    monkeypatch.setattr(coru_cli, "_diagnose_lane", fake_diagnose)

    rc = coru_cli.main(["status"])
    assert rc == 0
    assert called == {"ide": "cursor", "instance": "cursor"}


def test_stale_instance_not_reused_for_different_ide(monkeypatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "windsurf-main")
    monkeypatch.setattr(coru_cli, "_repo_root", lambda: None)
    assert coru_cli._infer_default_instance(ide="cursor") == "cursor"


def test_infer_default_ide_keeps_integrated_terminal_over_alive_daemon(monkeypatch) -> None:
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: "cursor")
    monkeypatch.setattr(
        coru_cli,
        "_terminal_shell_context",
        lambda: ("cursor", "env:CURSOR_*", True),
    )
    monkeypatch.setattr(coru_cli, "_connected_daemon_instance", lambda ide: None)
    monkeypatch.setattr(coru_cli, "_alive_daemon_ide", lambda: "antigravity")

    assert coru_cli._infer_default_ide() == "cursor"


def test_resolve_calibration_lane_prefers_integrated_terminal(monkeypatch) -> None:
    monkeypatch.setattr(coru_cli, "_print_terminal_context", lambda **_k: None)
    monkeypatch.setattr(
        coru_cli,
        "_terminal_shell_context",
        lambda: ("cursor", "env:CURSOR_*", True),
    )
    monkeypatch.setattr(coru_cli, "_infer_default_instance", lambda *, ide: f"{ide}-main")

    ide, instance = coru_cli._resolve_calibration_lane(
        "antigravity",
        "antigravity",
        explicit_ide=None,
    )

    assert ide == "cursor"
    assert instance == "cursor-main"


def test_resolve_calibration_lane_honors_explicit_ide(monkeypatch) -> None:
    monkeypatch.setattr(coru_cli, "_print_terminal_context", lambda **_k: None)
    monkeypatch.setattr(
        coru_cli,
        "_terminal_shell_context",
        lambda: ("cursor", "env:CURSOR_*", True),
    )

    ide, instance = coru_cli._resolve_calibration_lane(
        "antigravity",
        "antigravity",
        explicit_ide="antigravity",
    )

    assert ide == "antigravity"
    assert instance == "antigravity"


def test_terminal_hint_overrides_stale_supervisor_lane(monkeypatch, tmp_path: Path) -> None:
    project = tmp_path / "koru"
    project.mkdir()
    from coru.supervisor.registry import register_lane

    register_lane(
        ide="vscodium",
        instance="vscodium",
        project=str(project),
        set_active=True,
    )
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: "cursor")
    monkeypatch.setattr(coru_cli, "_repo_root", lambda: None)

    assert coru_cli._infer_default_ide() == "cursor"
    assert coru_cli._infer_default_instance(ide="cursor") == "cursor"


def test_generic_main_not_reused_when_ide_auto(monkeypatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "main")
    monkeypatch.setattr(coru_cli, "_repo_root", lambda: None)
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: "jetbrains")
    assert coru_cli._infer_default_instance(ide="auto") == "jetbrains"


def test_workspace_socket_path_drives_default_instance(monkeypatch, tmp_path) -> None:
    settings_dir = tmp_path / ".cursor"
    settings_dir.mkdir(parents=True, exist_ok=True)
    (settings_dir / "settings.json").write_text(
        '{"koruAutopilot.socketPath":"/run/user/1000/koru-autopilot-cursor-main.sock"}',
        encoding="utf-8",
    )

    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.setattr(coru_cli, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: None)

    assert coru_cli._infer_default_instance(ide="cursor") == "cursor-main"


def test_workspace_socket_path_drives_default_ide(monkeypatch, tmp_path) -> None:
    settings_dir = tmp_path / ".cursor"
    settings_dir.mkdir(parents=True, exist_ok=True)
    (settings_dir / "settings.json").write_text(
        '{"koruAutopilot.socketPath":"/run/user/1000/koru-autopilot-cursor-main.sock"}',
        encoding="utf-8",
    )

    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.setattr(coru_cli, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: None)

    assert coru_cli._infer_default_ide() == "cursor"


_FORK_ENV_KEYS = (
    "TERM_PROGRAM",
    "TERM_PROGRAM_VERSION",
    "CHROME_DESKTOP",
    "GIO_LAUNCHED_DESKTOP_FILE",
    "VSCODE_PID",
    "VSCODE_NLS_CONFIG",
    "VSCODE_IPC_HOOK",
    "VSCODE_CODE_CACHE_PATH",
    "VSCODE_CWD",
    "CURSOR_AGENT",
    "CURSOR_CLI",
    "WINDSURF_CASCADE_TERMINAL",
    "WINDSURF_VERSION",
    "WINDSURF_CSRF_TOKEN",
    "TERMINAL_EMULATOR",
    "IDEA_INITIAL_DIRECTORY",
    "PYCHARM_HOSTED",
    "JETBRAINS_IDE",
)


def _clear_fork_env(monkeypatch) -> None:
    for key in _FORK_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_terminal_ide_hint_jetbrains_from_emulator(monkeypatch) -> None:
    _clear_fork_env(monkeypatch)
    monkeypatch.setenv("TERMINAL_EMULATOR", "JetBrains-JediTerm")
    assert coru_cli._terminal_ide_hint() == "jetbrains"


def test_terminal_shell_context_windsurf_from_devin_desktop(monkeypatch) -> None:
    """Windsurf shipped as devin-desktop is recognised by provider name, not vscode."""
    _clear_fork_env(monkeypatch)
    monkeypatch.setenv("TERM_PROGRAM", "vscode")
    monkeypatch.setenv("TERM_PROGRAM_VERSION", "1.110.1-devin-desktop")
    monkeypatch.setenv("CHROME_DESKTOP", "devin-desktop.desktop")
    monkeypatch.setenv(
        "GIO_LAUNCHED_DESKTOP_FILE", "/usr/share/applications/devin-desktop.desktop"
    )
    monkeypatch.setenv("WINDSURF_CASCADE_TERMINAL", "1")
    assert coru_cli._terminal_shell_context_fallback()[0] == "windsurf"


def test_terminal_shell_context_windsurf_from_cascade_marker_only(monkeypatch) -> None:
    """A Windsurf cascade marker beats the generic vscode fallback."""
    _clear_fork_env(monkeypatch)
    monkeypatch.setenv("TERM_PROGRAM", "vscode")
    monkeypatch.setenv("CHROME_DESKTOP", "code.desktop")
    monkeypatch.setenv("WINDSURF_CASCADE_TERMINAL", "1")
    assert coru_cli._terminal_shell_context_fallback()[0] == "windsurf"


def test_terminal_shell_context_plain_vscode_is_last_resort(monkeypatch) -> None:
    """Plain VS Code (no fork markers) still resolves to vscode."""
    _clear_fork_env(monkeypatch)
    monkeypatch.setenv("TERM_PROGRAM", "vscode")
    monkeypatch.setenv("VSCODE_NLS_CONFIG", "/usr/share/code/resources/app")
    assert coru_cli._terminal_shell_context_fallback()[0] == "vscode"


def test_terminal_ide_hint_detects_codium_when_pid_probe_fails(monkeypatch) -> None:
    _clear_fork_env(monkeypatch)
    monkeypatch.setenv("TERM_PROGRAM", "vscode")
    monkeypatch.setenv("VSCODE_PID", "12345")
    monkeypatch.setenv("CHROME_DESKTOP", "codium.desktop")
    monkeypatch.setenv("VSCODE_CODE_CACHE_PATH", "/home/tom/.config/VSCodium/CachedData/sha")
    monkeypatch.setattr(coru_cli, "_ide_from_vscode_pid", lambda: None)


    assert coru_cli._terminal_ide_hint() == "vscodium"


def test_terminal_ide_hint_detects_codium_from_nls_config(monkeypatch) -> None:
    _clear_fork_env(monkeypatch)
    monkeypatch.setenv("TERM_PROGRAM", "vscode")
    monkeypatch.setenv("VSCODE_PID", "12345")
    monkeypatch.delenv("CHROME_DESKTOP", raising=False)
    monkeypatch.delenv("VSCODE_CODE_CACHE_PATH", raising=False)
    monkeypatch.setenv(
        "VSCODE_NLS_CONFIG",
        '{"defaultMessagesFile":"/snap/codium/495/usr/share/codium/resources/app/out/nls.messages.json"}',
    )
    monkeypatch.setattr(coru_cli, "_ide_from_vscode_pid", lambda: None)


    assert coru_cli._terminal_ide_hint() == "vscodium"


def test_terminal_ide_hint_detects_codium_from_nls_config_without_pid(monkeypatch) -> None:
    _clear_fork_env(monkeypatch)
    monkeypatch.setenv("TERM_PROGRAM", "vscode")
    monkeypatch.delenv("VSCODE_PID", raising=False)
    monkeypatch.delenv("CHROME_DESKTOP", raising=False)
    monkeypatch.delenv("VSCODE_CODE_CACHE_PATH", raising=False)
    monkeypatch.setenv(
        "VSCODE_NLS_CONFIG",
        '{"defaultMessagesFile":"/snap/codium/495/usr/share/codium/resources/app/out/nls.messages.json"}',
    )


    assert coru_cli._terminal_ide_hint() == "vscodium"


def test_terminal_ide_hint_vscode_pid_beats_stale_cursor_env(monkeypatch) -> None:
    _clear_fork_env(monkeypatch)
    monkeypatch.setenv("TERM_PROGRAM", "vscode")
    monkeypatch.setenv("VSCODE_PID", "12345")
    monkeypatch.setenv("CURSOR_AGENT", "1")
    monkeypatch.setenv("CHROME_DESKTOP", "cursor.desktop")
    monkeypatch.setattr(coru_cli, "_ide_from_vscode_pid", lambda: "vscode")


    assert coru_cli._terminal_ide_hint() == "vscode"


def test_terminal_shell_context_system_when_no_ide_markers(monkeypatch) -> None:
    for key in (
        "CURSOR_AGENT",
        "CURSOR_CLI",
        "CHROME_DESKTOP",
        "TERM_PROGRAM",
        "TERM_PROGRAM_VERSION",
        "VSCODE_PID",
        "VSCODE_NLS_CONFIG",
        "VSCODE_IPC_HOOK",
        "VSCODE_CODE_CACHE_PATH",
        "VSCODE_CWD",
        "WINDSURF_CASCADE_TERMINAL",
        "WINDSURF_VERSION",
        "WINDSURF_CSRF_TOKEN",
        "GIO_LAUNCHED_DESKTOP_FILE",
        "TERMINAL_EMULATOR",
        "IDEA_INITIAL_DIRECTORY",
        "PYCHARM_HOSTED",
        "JETBRAINS_IDE",
    ):
        monkeypatch.delenv(key, raising=False)

    ide, source, integrated = coru_cli._terminal_shell_context_fallback()
    assert ide is None
    assert source == "none"
    assert integrated is False


def test_warns_when_stale_main_lane_overridden(monkeypatch, capsys) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "main")
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: "jetbrains")
    coru_cli._resolve_defaults(coru_cli.Plan(action="status"))
    err = capsys.readouterr().err
    assert "stale lane overridden: main -> jetbrains" in err


def test_warns_only_once_per_chat_context(monkeypatch, capsys) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "main")
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: "jetbrains")
    ctx = coru_cli.SessionContext()
    coru_cli._resolve_defaults(coru_cli.Plan(action="status"), context=ctx)
    coru_cli._resolve_defaults(coru_cli.Plan(action="auto"), context=ctx)
    err_lines = [line for line in capsys.readouterr().err.splitlines() if "stale lane overridden" in line]
    assert len(err_lines) == 1


def test_normalize_lane_pair_prefers_instance_ide(capsys) -> None:
    ide, instance = coru_cli._normalize_lane_pair("vscode", "cursor-main")
    assert (ide, instance) == ("cursor", "cursor-main")
    assert "lane normalized from instance" in capsys.readouterr().err


def test_default_lane_normalizes_mismatched_explicit_pair(capsys) -> None:
    ide, instance = coru_cli._default_lane("vscode", "cursor-main")
    assert (ide, instance) == ("cursor", "cursor-main")
    assert "lane normalized from instance" in capsys.readouterr().err


def test_run_with_lane_environment_sets_and_restores(monkeypatch) -> None:
    observed: dict[str, str | None] = {}

    def fake_run(_cmd, *, passthrough=True):
        observed["ide"] = coru_cli.os.environ.get("KORU_AUTOPILOT_IDE")
        observed["instance"] = coru_cli.os.environ.get("KORU_AUTOPILOT_INSTANCE")
        observed["socket"] = coru_cli.os.environ.get("KORU_AUTOPILOT_SOCKET")
        return 0

    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "vscode")
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode-main")
    monkeypatch.setenv("KORU_AUTOPILOT_SOCKET", "/tmp/old.sock")
    monkeypatch.setattr(coru_cli, "_run", fake_run)

    rc = coru_cli._run_with_lane_environment(["echo", "ok"], ide="cursor", instance="cursor-main")

    assert rc == 0
    assert observed == {"ide": "cursor", "instance": "cursor-main", "socket": None}
    assert coru_cli.os.environ.get("KORU_AUTOPILOT_IDE") == "vscode"
    assert coru_cli.os.environ.get("KORU_AUTOPILOT_INSTANCE") == "vscode-main"
    assert coru_cli.os.environ.get("KORU_AUTOPILOT_SOCKET") == "/tmp/old.sock"


def test_koru_autopilot_env_payload_uses_explicit_lane_env(monkeypatch) -> None:
    captured: dict[str, str | None] = {}

    def fake_run(cmd, **kwargs):
        env = kwargs["env"]
        captured["instance"] = env.get("KORU_AUTOPILOT_INSTANCE")
        captured["ide"] = env.get("KORU_AUTOPILOT_IDE")
        captured["socket"] = env.get("KORU_AUTOPILOT_SOCKET")
        return type(
            "Proc",
            (),
            {
                "returncode": 0,
                "stdout": json.dumps(
                    {
                        "ok": True,
                        "ide": "vscodium",
                        "instance": "vscodium",
                        "socket": "/run/user/1000/koru-autopilot-vscodium.sock",
                        "source": "env:KORU_AUTOPILOT_INSTANCE",
                        "env": {"KORU_AUTOPILOT_INSTANCE": "vscodium"},
                    }
                ),
            },
        )()

    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "cursor-main")
    monkeypatch.setenv("KORU_AUTOPILOT_SOCKET", "/run/user/1000/koru-autopilot-cursor-main.sock")
    monkeypatch.setattr(coru_cli, "_koru_exec_argv", lambda: ["/tmp/koru"])
    monkeypatch.setattr(coru_cli, "_project_for_lane", lambda _ide, _instance: "/tmp/repo")
    monkeypatch.setattr(coru_cli.subprocess, "run", fake_run)

    payload = coru_cli._koru_autopilot_env_payload("vscodium", "vscodium")

    assert payload is not None
    assert payload["instance"] == "vscodium"
    assert captured == {
        "ide": "vscodium",
        "instance": "vscodium",
        "socket": None,
    }


def test_execute_plans_binds_lane_session_over_stale_env(monkeypatch) -> None:
    observed: list[tuple[str | None, str | None]] = []

    def fake_execute_plan(plan, *, shell: str, context=None) -> int:
        observed.append(
            (
                coru_cli.os.environ.get("KORU_AUTOPILOT_IDE"),
                coru_cli.os.environ.get("KORU_AUTOPILOT_INSTANCE"),
            )
        )
        return 0

    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "cursor-main")
    monkeypatch.setenv("KORU_AUTOPILOT_SOCKET", "/run/user/1000/koru-autopilot-cursor-main.sock")
    monkeypatch.setattr(coru_cli, "_execute_plan", fake_execute_plan)

    plans = [
        coru_cli.Plan(action="ensure", ide="vscodium", instance="vscodium"),
        coru_cli.Plan(action="auto", ide="vscodium", instance="vscodium"),
    ]
    rc = coru_cli._execute_plans(plans)

    assert rc == 0
    assert observed == [("vscodium", "vscodium"), ("vscodium", "vscodium")]
    assert coru_cli.os.environ.get("KORU_AUTOPILOT_INSTANCE") == "cursor-main"


def test_no_args_starts_autonomous_work(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_execute_plans(plans, *, shell: str, context=None, announce: bool = False) -> int:
        called["actions"] = [plan.action for plan in plans]
        called["install"] = [plan.install for plan in plans]
        called["shell"] = shell
        called["announce"] = announce
        return 0

    monkeypatch.setattr(coru_cli, "_execute_plans", fake_execute_plans)
    rc = coru_cli.main([])
    assert rc == 0
    assert called == {
        "actions": ["ensure", "lane", "manage", "diagnose", "auto"],
        "install": [True, False, False, False, False],
        "shell": "bash",
        "announce": False,
    }


def test_no_args_starts_chat_when_coru_mode_chat(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_chat_loop(
        *,
        use_llm: bool,
        shell: str,
        single_action: bool,
        verbose: bool = False,
        require_plugin: bool = False,
    ) -> int:
        called["require_plugin"] = require_plugin
        return 0

    monkeypatch.setenv("CORU_MODE", "chat")
    monkeypatch.setattr(coru_cli, "_chat_loop", fake_chat_loop)
    rc = coru_cli.main([])
    assert rc == 0
    assert called == {"require_plugin": True}


def test_bare_coru_forwards_args_after_double_dash(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_run_default_autonomous(auto_args, *, shell="bash", verbose=False) -> int:
        called["auto_args"] = tuple(auto_args)
        return 0

    monkeypatch.delenv("CORU_MODE", raising=False)
    monkeypatch.setattr(coru_cli, "_run_default_autonomous", fake_run_default_autonomous)
    rc = coru_cli.main(["--", "--max-cycles", "1"])
    assert rc == 0
    assert called["auto_args"] == ("--max-cycles", "1")


def test_bare_coru_interactive_prompts_for_ide_and_project(monkeypatch) -> None:
    called: dict[str, object] = {}
    answers = iter(["2", "2"])

    def fake_run_default_autonomous(auto_args, *, shell="bash", verbose=False) -> int:
        called["auto_args"] = tuple(auto_args)
        return 0

    monkeypatch.delenv("CORU_MODE", raising=False)
    monkeypatch.setattr(coru_cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(coru_cli.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(coru_cli, "_running_ide_choices", lambda: ["vscode", "cursor"])
    monkeypatch.setattr(coru_cli, "_infer_default_ide", lambda: "vscode")
    monkeypatch.setattr(coru_cli, "_instance_for_ide_choice", lambda ide: f"{ide}-main")
    monkeypatch.setattr(coru_cli, "_repo_root", lambda: None)
    monkeypatch.setattr(coru_cli, "_supervisor_project_choices", lambda: ["/repo-a", "/repo-b"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr(coru_cli, "_run_default_autonomous", fake_run_default_autonomous)

    rc = coru_cli.main([])
    assert rc == 0
    assert called["auto_args"] == (
        "--agent-lane",
        "cursor-main",
        "--project",
        "/repo-b",
    )


def test_bare_coru_uses_integrated_terminal_ide_without_prompt(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_run_default_autonomous(auto_args, *, shell="bash", verbose=False) -> int:
        called["auto_args"] = tuple(auto_args)
        return 0

    def fail_input(_prompt: str) -> str:
        raise AssertionError("integrated terminal IDE should be selected automatically")

    monkeypatch.delenv("CORU_MODE", raising=False)
    monkeypatch.setattr(coru_cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(coru_cli.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(
        coru_cli,
        "_running_ide_choices",
        lambda: ["windsurf", "vscodium", "jetbrains"],
    )
    monkeypatch.setattr(
        coru_cli,
        "_terminal_shell_context",
        lambda: ("vscodium", "env:VSCODE_*", True),
    )
    monkeypatch.setattr(coru_cli, "_instance_for_ide_choice", lambda ide: ide)
    monkeypatch.setattr(coru_cli, "_repo_root", lambda: None)
    monkeypatch.setattr(coru_cli, "_supervisor_project_choices", lambda: [])
    monkeypatch.setattr("builtins.input", fail_input)
    monkeypatch.setattr(coru_cli, "_run_default_autonomous", fake_run_default_autonomous)

    rc = coru_cli.main([])

    assert rc == 0
    assert called["auto_args"] == ("--agent-lane", "vscodium")


def test_default_autonomous_uses_interactive_agent_lane_for_startup_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[tuple[str, str, str, tuple[str, ...]]] = []

    def fake_execute_plans(plans, *, shell: str, context=None, announce: bool = False) -> int:
        for plan in plans:
            seen.append((plan.action, plan.ide or "", plan.instance or "", tuple(plan.auto_args)))
        return 0

    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscodium")
    monkeypatch.setattr(coru_cli, "_terminal_shell_context", lambda: (None, "none", False))
    monkeypatch.setattr(coru_cli, "_print_runtime_versions", lambda: None)
    monkeypatch.setattr(coru_cli, "_print_troubleshooting_log_locations", lambda _ide, _instance: None)
    monkeypatch.setattr(coru_cli, "_execute_plans", fake_execute_plans)

    rc = coru_cli._run_default_autonomous(["--agent-lane", "cursor-main"])

    assert rc == 0
    assert [(action, ide, instance) for action, ide, instance, _args in seen] == [
        ("ensure", "cursor", "cursor-main"),
        ("lane", "cursor", "cursor-main"),
        ("manage", "cursor", "cursor-main"),
        ("diagnose", "cursor", "cursor-main"),
        ("auto", "cursor", "cursor-main"),
    ]
    assert seen[-1][3] == ("--agent-lane", "cursor-main")


def test_bare_coru_no_prompt_when_single_ide_and_project(monkeypatch) -> None:
    called: dict[str, object] = {}

    def fake_run_default_autonomous(auto_args, *, shell="bash", verbose=False) -> int:
        called["auto_args"] = tuple(auto_args)
        return 0

    monkeypatch.delenv("CORU_MODE", raising=False)
    monkeypatch.setattr(coru_cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(coru_cli.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(coru_cli, "_running_ide_choices", lambda: ["cursor"])
    monkeypatch.setattr(coru_cli, "_repo_root", lambda: None)
    monkeypatch.setattr(coru_cli, "_supervisor_project_choices", lambda: ["/repo-a"])
    monkeypatch.setattr(coru_cli, "_run_default_autonomous", fake_run_default_autonomous)

    rc = coru_cli.main([])
    assert rc == 0
    assert called["auto_args"] == ()


def test_status_alias_routes_to_lane_status(monkeypatch) -> None:
    called: dict[str, str] = {}

    def fake_diagnose(ide: str, instance: str, **kwargs) -> int:
        called["ide"] = ide
        called["instance"] = instance
        return 0

    monkeypatch.setattr(coru_cli, "_diagnose_lane", fake_diagnose)
    rc = coru_cli.main(["status", "cursor", "cursor-main"])
    assert rc == 0
    assert called == {"ide": "cursor", "instance": "cursor-main"}


def test_diagnose_attempts_plugin_self_heal_on_system_shell(monkeypatch) -> None:
    calls: dict[str, int] = {"status": 0, "heal": 0}

    monkeypatch.setattr(coru_cli, "_print_troubleshooting_log_locations", lambda _ide, _instance: None)
    monkeypatch.setattr(coru_cli, "_ensure_commands", lambda install=False: 0)
    monkeypatch.setattr(
        coru_cli,
        "_koru_autopilot_env_payload",
        lambda _ide, _instance: {"ide": "cursor", "instance": "cursor-main", "socket": "/tmp/x.sock", "source": "test"},
    )
    monkeypatch.setattr(coru_cli, "_lane_manage_fix", lambda _ide, _instance: 0)
    monkeypatch.setattr(coru_cli, "_ensure_daemon_running", lambda _ide, _instance: 0)
    monkeypatch.setattr(coru_cli, "_terminal_shell_context", lambda: (None, "none", False))

    def fake_status(_ide: str, _instance: str) -> int:
        calls["status"] += 1
        return 1 if calls["status"] == 1 else 0

    def fake_heal(_ide: str, _instance: str, *, timeout_seconds: float = 12.0) -> int:
        calls["heal"] += 1
        return 0

    monkeypatch.setattr(coru_cli, "_lane_status_raw", fake_status)
    monkeypatch.setattr(coru_cli, "_attempt_plugin_self_heal", fake_heal)

    rc = coru_cli._diagnose_lane("cursor", "cursor-main")
    assert rc == 0
    assert calls["heal"] == 1


def test_diagnose_runs_plugin_self_heal_in_integrated_shell(monkeypatch) -> None:
    calls: dict[str, int] = {"heal": 0}

    monkeypatch.setattr(coru_cli, "_print_troubleshooting_log_locations", lambda _ide, _instance: None)
    monkeypatch.setattr(coru_cli, "_ensure_commands", lambda install=False: 0)
    monkeypatch.setattr(
        coru_cli,
        "_koru_autopilot_env_payload",
        lambda _ide, _instance: {"ide": "cursor", "instance": "cursor-main", "socket": "/tmp/x.sock", "source": "test"},
    )
    monkeypatch.setattr(coru_cli, "_diagnose_runtime_consistency", lambda _ide, _instance, _payload: 0)
    monkeypatch.setattr(coru_cli, "_lane_manage_fix", lambda _ide, _instance: 0)
    monkeypatch.setattr(coru_cli, "_ensure_daemon_running", lambda _ide, _instance: 0)
    monkeypatch.setattr(
        coru_cli,
        "_run_lane_repair",
        lambda _ide, _instance, *, payload=None: repair_registry.RepairPlan(problems=(), attempts=(), resolved=True),
    )
    monkeypatch.setattr(coru_cli, "_terminal_shell_context", lambda: ("vscode", "env:TERM_PROGRAM", True))
    status_calls = {"n": 0}

    def fake_status_raw(_ide: str, _instance: str) -> int:
        status_calls["n"] += 1
        return 0 if status_calls["n"] > 1 else 1

    monkeypatch.setattr(coru_cli, "_lane_status_raw", fake_status_raw)
    monkeypatch.setattr(
        coru_cli,
        "_lane_status_payload",
        lambda _ide, _instance, *, payload=None: {"plugins": [{"ide": "cursor", "version": "0.2.2"}]},
    )
    monkeypatch.setattr(coru_cli, "_print_ide_control_context", lambda *args, **kwargs: None)

    def fake_heal(_ide: str, _instance: str, *, timeout_seconds: float = 12.0, attempts: int = 3) -> int:
        calls["heal"] += 1
        return 0

    monkeypatch.setattr(coru_cli, "_attempt_plugin_self_heal", fake_heal)

    rc = coru_cli._diagnose_lane("cursor", "cursor-main")
    assert rc == 0
    assert calls["heal"] == 1


def test_diagnose_runtime_consistency_warns_on_python_mismatch(monkeypatch, capsys) -> None:
    monkeypatch.setattr(coru_cli, "_repo_root", lambda: None)
    monkeypatch.setattr(coru_cli, "_project_venv_python", lambda: "/tmp/repo/.venv/bin/python")
    monkeypatch.setattr(coru_cli.sys, "executable", "/tmp/global/.venv/bin/python")
    monkeypatch.setattr(coru_cli, "_koru_exec_argv", lambda: ["/tmp/repo/.venv/bin/koru"])

    coru_cli._diagnose_runtime_consistency("cursor", "cursor-main", None)
    err = capsys.readouterr().err
    assert "python env mismatch" in err


def test_attempt_plugin_self_heal_retries_until_status_ok(monkeypatch) -> None:
    calls: dict[str, int] = {"status": 0, "reload": 0, "connect": 0}

    def fake_status(_ide: str, _instance: str) -> int:
        calls["status"] += 1
        return 0 if calls["status"] >= 3 else 1

    def fake_reload(_ide: str, _repo) -> repair_registry.RepairAttempt:
        calls["reload"] += 1
        return repair_registry.RepairAttempt(action_id="reload_ide", mode="auto", ok=True, message="ok")

    def fake_connect(_ide: str) -> repair_registry.RepairAttempt:
        calls["connect"] += 1
        return repair_registry.RepairAttempt(action_id="connect_plugin", mode="auto", ok=True, message="ok")

    monkeypatch.setattr(coru_cli, "_lane_status_raw", fake_status)
    monkeypatch.setattr(coru_cli, "_repair_reload_ide", fake_reload)
    monkeypatch.setattr(coru_cli, "_repair_connect_plugin", fake_connect)
    monkeypatch.setattr(coru_cli, "_fetch_manage_report", lambda _ide, _instance: None)
    monkeypatch.setattr(
        coru_cli,
        "_lane_status_payload",
        lambda _ide, _instance, *, payload=None: {"plugins": [{"ide": "cursor", "buildSha": "abc"}]},
    )
    monkeypatch.setattr(coru_cli.time, "sleep", lambda _s: None)

    rc = coru_cli._attempt_plugin_self_heal("cursor", "cursor-main", timeout_seconds=0.01, attempts=3)
    assert rc == 0
    assert calls["reload"] >= 1


def test_status_failure_continues_to_auto_for_refactor(monkeypatch) -> None:
    called: list[str] = []

    def fake_ensure(install: bool) -> int:
        called.append("ensure")
        return 0

    def fake_lane_env(ide: str, instance: str, shell: str) -> int:
        called.append("lane")
        return 0

    def fake_lane_manage_fix(ide: str, instance: str) -> int:
        called.append("manage")
        return 0

    def fake_diagnose(ide: str, instance: str, **kwargs) -> int:
        called.append("diagnose")
        return 1

    def fake_lane_auto(ide: str, instance: str, extra_args) -> int:
        called.append("auto")
        return 0

    monkeypatch.setattr(coru_cli, "_ensure_commands", fake_ensure)
    monkeypatch.setattr(coru_cli, "_lane_env", fake_lane_env)
    monkeypatch.setattr(coru_cli, "_lane_manage_fix", fake_lane_manage_fix)
    monkeypatch.setattr(coru_cli, "_diagnose_lane", fake_diagnose)
    monkeypatch.setattr(
        coru_cli,
        "_auto_readiness_gate",
        lambda ide, instance: coru_cli.AutoReadiness(0, ide, instance),
    )
    monkeypatch.setattr(coru_cli, "_lane_auto", fake_lane_auto)

    rc = coru_cli.main(["text", "refaktoryzuj"])
    assert rc == 0
    assert called == ["ensure", "lane", "manage", "diagnose", "auto"]


def test_chat_refaktoryzuj_continues_past_status_when_daemon_down(monkeypatch) -> None:
    called: dict[str, str] = {}
    inputs = iter(["refaktoryzuj", "quit"])

    def fake_drive(ide: str, instance: str, prompt: str, *, require_plugin: bool = False) -> int:
        called["ide"] = ide
        called["instance"] = instance
        called["prompt"] = prompt
        called["require_plugin"] = require_plugin
        return 0

    monkeypatch.setattr(coru_cli, "_lane_chat_prompt", fake_drive)
    monkeypatch.setattr(coru_cli, "_chat_llm_enabled", lambda _use_llm: False)
    monkeypatch.setattr(coru_cli, "_repo_root", lambda: None)
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: "cursor")
    monkeypatch.setattr(coru_cli, "_print_troubleshooting_log_locations", lambda _ide, _instance: None)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))

    rc = coru_cli.main(["chat"])
    assert rc == 0
    assert called == {
        "ide": "cursor",
        "instance": "cursor",
        "prompt": "refaktoryzuj",
        "require_plugin": True,
    }


def test_chat_uses_llm_rewrite_when_configured(monkeypatch) -> None:
    called: dict[str, str] = {}
    inputs = iter(["zrob refakotryzacje", "quit"])

    def fake_drive(ide: str, instance: str, prompt: str, *, require_plugin: bool = False) -> int:
        called["ide"] = ide
        called["instance"] = instance
        called["prompt"] = prompt
        called["require_plugin"] = require_plugin
        return 0

    monkeypatch.setattr(coru_cli, "_repo_root", lambda: None)
    monkeypatch.setattr(coru_cli, "_lane_chat_prompt", fake_drive)
    monkeypatch.setattr(coru_cli, "_chat_llm_enabled", lambda _use_llm: True)
    monkeypatch.setattr(coru_cli, "_llm_rewrite_chat_prompt", lambda text, **_k: f"IDE PROMPT: {text}")
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: "jetbrains")
    monkeypatch.setattr(coru_cli, "_print_troubleshooting_log_locations", lambda _ide, _instance: None)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))

    rc = coru_cli.main(["chat"])
    assert rc == 0
    assert called == {
        "ide": "jetbrains",
        "instance": "jetbrains",
        "prompt": "IDE PROMPT: zrob refakotryzacje",
        "require_plugin": True,
    }


def test_chat_slash_command_executes_coru_actions(monkeypatch) -> None:
    called: list[str] = []
    inputs = iter(["/refaktoryzuj", "quit"])

    def fake_ensure(install: bool) -> int:
        called.append("ensure")
        return 0

    def fake_lane_env(ide: str, instance: str, shell: str) -> int:
        called.append("lane")
        return 0

    def fake_lane_manage_fix(ide: str, instance: str) -> int:
        called.append("manage")
        return 0

    def fake_diagnose(ide: str, instance: str, **kwargs) -> int:
        called.append("diagnose")
        return 1

    def fake_lane_auto(ide: str, instance: str, extra_args) -> int:
        called.append("auto")
        return 0

    monkeypatch.setattr(coru_cli, "_ensure_commands", fake_ensure)
    monkeypatch.setattr(coru_cli, "_lane_env", fake_lane_env)
    monkeypatch.setattr(coru_cli, "_lane_manage_fix", fake_lane_manage_fix)
    monkeypatch.setattr(coru_cli, "_diagnose_lane", fake_diagnose)
    monkeypatch.setattr(
        coru_cli,
        "_auto_readiness_gate",
        lambda ide, instance: coru_cli.AutoReadiness(0, ide, instance),
    )
    monkeypatch.setattr(coru_cli, "_lane_auto", fake_lane_auto)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))

    rc = coru_cli.main(["chat"])
    assert rc == 0
    assert called == ["ensure", "lane", "manage", "diagnose", "auto"]


def test_status_failure_stops_without_auto_chain(monkeypatch) -> None:
    def fake_diagnose(ide: str, instance: str, **kwargs) -> int:
        return 1

    monkeypatch.setattr(coru_cli, "_diagnose_lane", fake_diagnose)
    rc = coru_cli.main(["text", "status for cursor-main in cursor"])
    assert rc == 1


def test_build_plan_chain_refaktoryzuj() -> None:
    plans = coru_cli._build_plan_chain("refaktoryzuj")
    assert [p.action for p in plans] == ["ensure", "lane", "manage", "diagnose", "auto"]


def test_heuristic_plan_refakotryzuj_typo() -> None:
    plan = coru_cli._heuristic_plan("refakotryzuj")
    assert plan.action == "auto"


def test_build_plan_chain_refakotryzuj_typo() -> None:
    plans = coru_cli._build_plan_chain("refakotryzuj")
    assert [p.action for p in plans] == ["ensure", "lane", "manage", "diagnose", "auto"]


def test_status_failure_continues_to_auto_for_refakotryzuj_typo(monkeypatch) -> None:
    captured: list[list[str]] = []

    def fake_execute_plans(plans, *, shell: str, context=None, announce: bool = False) -> int:
        captured.append([plan.action for plan in plans])
        return 0

    monkeypatch.setattr(coru_cli, "_execute_plans", fake_execute_plans)

    rc = coru_cli.main(["text", "refakotryzuj"])
    assert rc == 0
    assert captured == [["ensure", "lane", "manage", "diagnose", "auto"]]


def test_chat_refakotryzuj_typo_continues_past_status(monkeypatch) -> None:
    called: dict[str, str] = {}
    inputs = iter(["refakotryzuj", "quit"])

    def fake_drive(ide: str, instance: str, prompt: str, *, require_plugin: bool = False) -> int:
        called["ide"] = ide
        called["instance"] = instance
        called["prompt"] = prompt
        called["require_plugin"] = require_plugin
        return 0

    monkeypatch.setattr(coru_cli, "_lane_chat_prompt", fake_drive)
    monkeypatch.setattr(coru_cli, "_chat_llm_enabled", lambda _use_llm: False)
    monkeypatch.setattr(coru_cli, "_repo_root", lambda: None)
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: "cursor")
    monkeypatch.setattr(coru_cli, "_print_troubleshooting_log_locations", lambda _ide, _instance: None)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))

    rc = coru_cli.main(["chat"])
    assert rc == 0
    assert called == {
        "ide": "cursor",
        "instance": "cursor",
        "prompt": "refakotryzuj",
        "require_plugin": True,
    }


def test_env_alias_routes_to_lane(monkeypatch) -> None:
    called: dict[str, str] = {}

    def fake_lane_env(ide: str, instance: str, shell: str) -> int:
        called["ide"] = ide
        called["instance"] = instance
        called["shell"] = shell
        return 0

    monkeypatch.setattr(coru_cli, "_lane_env", fake_lane_env)
    rc = coru_cli.main(["env", "vscode", "vscode-main", "--shell", "zsh"])
    assert rc == 0
    assert called == {"ide": "vscode", "instance": "vscode-main", "shell": "zsh"}


def test_lane_chat_prompt_uses_ide_not_instance(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(coru_cli, "_koru_exec_argv", lambda: ["koru"])
    monkeypatch.setattr(coru_cli, "_koru_autopilot_env_payload", lambda _ide, _instance: None)

    def fake_run_with_resolved_lane_env(command, *, ide: str, instance: str) -> int:
        captured["command"] = list(command)
        captured["ide"] = ide
        captured["instance"] = instance
        return 0

    monkeypatch.setattr(coru_cli, "_run_with_resolved_lane_env", fake_run_with_resolved_lane_env)

    rc = coru_cli._lane_chat_prompt("cursor", "cursor-main", "hello")
    assert rc == 0
    assert captured["command"] == ["koru", "autopilot", "drive", "--ide", "cursor", "hello"]


def test_chat_autostarts_daemon_and_retries_on_rc2(monkeypatch) -> None:
    inputs = iter(["zrob refaktor", "quit"])
    drive_calls: list[tuple[str, str, str]] = []
    daemon_calls: list[tuple[str, str]] = []

    def fake_drive(ide: str, instance: str, prompt: str, *, require_plugin: bool = False) -> int:
        drive_calls.append((ide, instance, prompt))
        return 2 if len(drive_calls) == 1 else 0

    monkeypatch.setattr(coru_cli, "_lane_chat_prompt", fake_drive)
    monkeypatch.setattr(coru_cli, "_lane_status", lambda _ide, _instance: 0)
    monkeypatch.setattr(coru_cli, "_chat_llm_enabled", lambda _use_llm: False)
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: "cursor")
    monkeypatch.setattr(coru_cli, "_print_troubleshooting_log_locations", lambda _ide, _instance: None)
    monkeypatch.setattr(
        coru_cli,
        "_start_autopilot_daemon_for_lane",
        lambda ide, instance: daemon_calls.append((ide, instance)) or 0,
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))

    rc = coru_cli.main(["chat"])
    assert rc == 0
    assert daemon_calls == [("cursor", "cursor-main")]
    assert drive_calls == [
        ("cursor", "cursor-main", "zrob refaktor"),
        ("cursor", "cursor-main", "zrob refaktor"),
    ]


def test_start_autopilot_daemon_uses_lane_instance(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            captured["cmd"] = cmd
            captured["env"] = kwargs["env"]

    monkeypatch.setattr(coru_cli, "_koru_exec_argv", lambda: ["/tmp/repo/.venv/bin/koru"])
    monkeypatch.setattr(coru_cli, "_koru_autopilot_env_payload", lambda _ide, _instance: None)
    monkeypatch.setattr(coru_cli, "_project_for_lane", lambda _ide, _instance: None)
    monkeypatch.setattr(coru_cli.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(coru_cli.time, "sleep", lambda _seconds: None)

    rc = coru_cli._start_autopilot_daemon_for_lane("cursor", "cursor-main")

    assert rc == 0
    assert captured["cmd"] == ["/tmp/repo/.venv/bin/koru", "autopilot", "daemon", "--idempotent"]
    assert captured["env"]["KORU_AUTOPILOT_IDE"] == "cursor"
    assert captured["env"]["KORU_AUTOPILOT_INSTANCE"] == "cursor-main"
    assert "KORU_AUTOPILOT_SOCKET" not in captured["env"]


def test_chat_reports_failure_when_daemon_autostart_fails(monkeypatch, capsys) -> None:
    inputs = iter(["zrob refaktor", "quit"])
    drive_calls: list[tuple[str, str, str]] = []

    def fake_drive(ide: str, instance: str, prompt: str, *, require_plugin: bool = False) -> int:
        drive_calls.append((ide, instance, prompt))
        return 2

    monkeypatch.setattr(coru_cli, "_lane_chat_prompt", fake_drive)
    monkeypatch.setattr(coru_cli, "_lane_status", lambda _ide, _instance: 0)
    monkeypatch.setattr(coru_cli, "_chat_llm_enabled", lambda _use_llm: False)
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: "cursor")
    monkeypatch.setattr(coru_cli, "_print_troubleshooting_log_locations", lambda _ide, _instance: None)
    monkeypatch.setattr(coru_cli, "_start_autopilot_daemon_for_lane", lambda _ide, _instance: 1)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))

    rc = coru_cli.main(["chat"])
    assert rc == 0
    assert drive_calls == [("cursor", "cursor-main", "zrob refaktor")]
    assert "[coru] failed rc=2" in capsys.readouterr().out


def test_extract_global_flags_accepts_log_format() -> None:
    rest, verbose, show_version, log_format, require_plugin = coru_cli._extract_global_flags(
        ["--log-format", "jsonl", "--verbose", "status"]
    )

    assert rest == ["status"]
    assert verbose is True
    assert show_version is False
    assert log_format == "jsonl"
    assert require_plugin is False


def test_extract_global_flags_accepts_require_plugin() -> None:
    rest, verbose, show_version, log_format, require_plugin = coru_cli._extract_global_flags(
        ["--require-plugin", "chat"]
    )

    assert rest == ["chat"]
    assert verbose is False
    assert show_version is False
    assert log_format == "human"
    assert require_plugin is True


def test_chat_emits_jsonl_contract(monkeypatch, capsys) -> None:
    inputs = iter(["zrob refaktor", "quit"])

    monkeypatch.setattr(
        coru_cli,
        "_lane_chat_prompt",
        lambda _ide, _instance, _prompt, require_plugin=False: 0,
    )
    monkeypatch.setattr(coru_cli, "_lane_status", lambda _ide, _instance: 0)
    monkeypatch.setattr(coru_cli, "_chat_llm_enabled", lambda _use_llm: False)
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: "cursor")
    monkeypatch.setattr(coru_cli, "_print_troubleshooting_log_locations", lambda _ide, _instance: None)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))

    rc = coru_cli.main(["--log-format", "jsonl", "chat"])
    assert rc == 0
    err_lines = [line for line in capsys.readouterr().err.splitlines() if line.strip().startswith("{")]
    assert err_lines
    payload = __import__("json").loads(err_lines[0])
    assert set(["ts", "corr", "component", "level", "action", "result"]).issubset(payload)


def test_chat_forwards_require_plugin(monkeypatch) -> None:
    called: dict[str, object] = {}
    inputs = iter(["refaktor", "quit"])

    def fake_drive(ide: str, instance: str, prompt: str, *, require_plugin: bool = False) -> int:
        called["ide"] = ide
        called["instance"] = instance
        called["prompt"] = prompt
        called["require_plugin"] = require_plugin
        return 0

    monkeypatch.setattr(coru_cli, "_lane_chat_prompt", fake_drive)
    monkeypatch.setattr(coru_cli, "_lane_status", lambda _ide, _instance: 0)
    monkeypatch.setattr(coru_cli, "_chat_llm_enabled", lambda _use_llm: False)
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: "cursor")
    monkeypatch.setattr(coru_cli, "_print_troubleshooting_log_locations", lambda _ide, _instance: None)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))

    rc = coru_cli.main(["--require-plugin", "chat"])
    assert rc == 0
    assert called == {
        "ide": "cursor",
        "instance": "cursor-main",
        "prompt": "refaktor",
        "require_plugin": True,
    }


def test_chat_allows_explicit_keyboard_fallback(monkeypatch) -> None:
    called: dict[str, object] = {}
    inputs = iter(["refaktor", "quit"])

    def fake_drive(ide: str, instance: str, prompt: str, *, require_plugin: bool = False) -> int:
        called["ide"] = ide
        called["instance"] = instance
        called["prompt"] = prompt
        called["require_plugin"] = require_plugin
        return 0

    monkeypatch.setattr(coru_cli, "_lane_chat_prompt", fake_drive)
    monkeypatch.setattr(coru_cli, "_chat_llm_enabled", lambda _use_llm: False)
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: "cursor")
    monkeypatch.setattr(coru_cli, "_print_troubleshooting_log_locations", lambda _ide, _instance: None)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))

    rc = coru_cli.main(["chat", "--allow-keyboard-fallback"])

    assert rc == 0
    assert called == {
        "ide": "cursor",
        "instance": "cursor-main",
        "prompt": "refaktor",
        "require_plugin": False,
    }


def test_chat_preflights_lane_status_and_autostarts_missing_plugin(monkeypatch) -> None:
    inputs = iter(["zrob refaktor", "quit"])
    drive_calls: list[tuple[str, str, str]] = []
    daemon_calls: list[tuple[str, str]] = []

    def fake_drive(ide: str, instance: str, prompt: str, *, require_plugin: bool = False) -> int:
        drive_calls.append((ide, instance, prompt))
        return 0

    monkeypatch.setattr(coru_cli, "_lane_chat_prompt", fake_drive)
    monkeypatch.setattr(coru_cli, "_lane_status", lambda _ide, _instance: 1)
    monkeypatch.setattr(
        coru_cli,
        "_start_autopilot_daemon_for_lane",
        lambda ide, instance: daemon_calls.append((ide, instance)) or 0,
    )
    monkeypatch.setattr(coru_cli, "_chat_llm_enabled", lambda _use_llm: False)
    monkeypatch.setattr(coru_cli, "_terminal_ide_hint", lambda: "cursor")
    monkeypatch.setattr(coru_cli, "_print_troubleshooting_log_locations", lambda _ide, _instance: None)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))

    rc = coru_cli.main(["chat"])

    assert rc == 0
    assert daemon_calls == [("cursor", "cursor-main")]
    assert drive_calls == [("cursor", "cursor-main", "zrob refaktor")]


def test_print_troubleshooting_log_locations(capsys, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")
    monkeypatch.setattr(coru_cli, "_repo_root", lambda: tmp_path)

    coru_cli._print_troubleshooting_log_locations("cursor", "cursor-main")

    out = capsys.readouterr().out
    assert "debug logs:" in out
    assert str(tmp_path / ".planfile" / ".koru" / "nfo-events.jsonl") in out
    assert "koru-autopilot-cursor-main.daemon.json" in out
    assert "coru status" in out
    assert "coru daemon" in out


def test_repair_command_is_not_text_shorthand(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(coru_cli, "_repo_root", lambda: tmp_path)
    printed: list[str] = []

    class Args:
        command = "repair"
        repair_command = "history"
        ide = None
        instance = None
        limit = 5
        code = None
        format = "llm"

    monkeypatch.setattr(coru_cli, "_cmd_repair_history", lambda _args: printed.append("history") or 0)
    monkeypatch.setattr(coru_cli, "_build_parser", lambda: type("P", (), {"parse_args": lambda _self, _argv: Args()})())
    monkeypatch.setattr(coru_cli, "_maybe_reexec_into_project_python", lambda _argv: False)
    monkeypatch.setattr(coru_cli, "_extract_global_flags", lambda argv: (argv, False, False, "human", True))

    rc = coru_cli.main(["repair", "history", "--format", "llm"])

    assert rc == 0
    assert printed == ["history"]


def test_repair_command_is_not_text_shorthand(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(coru_cli, "_repo_root", lambda: tmp_path)
    printed: list[str] = []

    class Args:
        command = "repair"
        repair_command = "history"
        ide = None
        instance = None
        limit = 5
        code = None
        format = "llm"

    monkeypatch.setattr(coru_cli, "_cmd_repair_history", lambda _args: printed.append("history") or 0)
    monkeypatch.setattr(coru_cli, "_build_parser", lambda: type("P", (), {"parse_args": lambda _self, _argv: Args()})())
    monkeypatch.setattr(coru_cli, "_maybe_reexec_into_project_python", lambda _argv: False)
    monkeypatch.setattr(coru_cli, "_extract_global_flags", lambda argv: (argv, False, False, "human", True))

    rc = coru_cli.main(["repair", "history", "--format", "llm"])

    assert rc == 0
    assert printed == ["history"]
