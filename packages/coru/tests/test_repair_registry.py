from __future__ import annotations

import json
import zipfile
from pathlib import Path

from coru import repair_registry as rr


def test_collect_problems_build_mismatch_on_disk(tmp_path: Path, monkeypatch) -> None:
    ext_root = tmp_path / ".cursor" / "extensions"
    ext_dir = ext_root / "semcod.koru-autopilot-cursor-0.2.2"
    ext_dir.mkdir(parents=True)
    (ext_dir / "package.json").write_text(
        json.dumps({"version": "0.2.2", "koruAutopilotBuild": {"sha": "4f260d36817403e9"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(rr.Path, "home", lambda: tmp_path)

    status = {
        "plugins": [
            {"ide": "cursor", "version": "0.2.2", "buildSha": "4f260d36817403e9"},
        ]
    }
    problems = rr.collect_problems_from_status(
        status,
        ide="cursor",
        expected_build="e3caf7acdab415c4",
    )
    codes = {p.code for p in problems}
    assert "plugin_extension_stale_on_disk" in codes


def test_collect_problems_stale_in_memory(tmp_path: Path, monkeypatch) -> None:
    ext_root = tmp_path / ".cursor" / "extensions"
    ext_dir = ext_root / "semcod.koru-autopilot-cursor-0.2.2"
    ext_dir.mkdir(parents=True)
    (ext_dir / "package.json").write_text(
        json.dumps({"version": "0.2.2", "koruAutopilotBuild": {"sha": "e3caf7acdab415c4"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(rr.Path, "home", lambda: tmp_path)

    status = {
        "plugins": [
            {"ide": "cursor", "version": "0.2.2", "buildSha": "4f260d36817403e9"},
        ]
    }
    problems = rr.collect_problems_from_status(
        status,
        ide="cursor",
        expected_build="e3caf7acdab415c4",
    )
    assert any(p.code == "plugin_extension_stale_in_memory" for p in problems)


def test_collect_problems_from_manage_report_keeps_issue_plugin_and_action_codes() -> None:
    report = {
        "issues": [
            {
                "code": "daemon_not_running",
                "severity": "warning",
                "message": "daemon stopped",
                "fix": "start daemon",
            },
            {"code": ""},
            "ignored",
        ],
        "plugin": {
            "ide": "cursor",
            "connected": False,
            "supported": True,
        },
        "actions": [
            {
                "action": "install_plugin",
                "result": {
                    "status": "failed",
                    "message": "zygote sandbox refused launch",
                },
            },
            {"name": "install_plugin", "result": {"status": "ok"}},
            "ignored",
        ],
    }

    problems = rr.collect_problems_from_manage_report(report)

    by_code = {problem.code: problem for problem in problems}
    assert set(by_code) == {
        "daemon_not_running",
        "install_plugin_cli_sandbox",
        "plugin_not_connected",
    }
    assert by_code["daemon_not_running"].fix_hint == "start daemon"
    assert by_code["install_plugin_cli_sandbox"].context == {
        "source": "manage_report.actions",
        "installer_message": "zygote sandbox refused launch",
    }


def test_manual_vsix_unpack_installs_expected_build(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    plugin_dir = repo / "plugins" / "koru-autopilot-cursor"
    plugin_dir.mkdir(parents=True)
    vsix = plugin_dir / "koru-autopilot-cursor-0.2.2.vsix"
    pkg = {
        "name": "koru-autopilot-cursor",
        "version": "0.2.2",
        "koruAutopilotBuild": {"schema": 1, "sha": "e3caf7acdab415c4"},
    }
    with zipfile.ZipFile(vsix, "w") as archive:
        archive.writestr("extension/package.json", json.dumps(pkg))

    home = tmp_path / "home"
    monkeypatch.setattr(rr.Path, "home", lambda: home)

    attempt = rr.manual_vsix_unpack(ide="cursor", repo_root=repo)
    assert attempt.ok is True
    installed = (
        home
        / ".cursor"
        / "extensions"
        / "semcod.koru-autopilot-cursor-0.2.2"
        / "package.json"
    )
    assert installed.is_file()
    installed_pkg = json.loads(installed.read_text(encoding="utf-8"))
    assert installed_pkg["koruAutopilotBuild"]["sha"] == "e3caf7acdab415c4"


def test_run_repair_pipeline_manual_unpack_then_resolved(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    plugin_dir = repo / "plugins" / "koru-autopilot-cursor"
    plugin_dir.mkdir(parents=True)
    vsix = plugin_dir / "koru-autopilot-cursor-0.2.2.vsix"
    pkg = {
        "name": "koru-autopilot-cursor",
        "version": "0.2.2",
        "koruAutopilotBuild": {"schema": 1, "sha": "e3caf7acdab415c4"},
    }
    with zipfile.ZipFile(vsix, "w") as archive:
        archive.writestr("extension/package.json", json.dumps(pkg))
    home = tmp_path / "home"
    monkeypatch.setattr(rr.Path, "home", lambda: home)

    calls: list[list[str]] = []
    status_queue = [
        {"plugins": [{"ide": "cursor", "buildSha": "4f260d36817403e9"}]},
        {"plugins": [{"ide": "cursor", "buildSha": "e3caf7acdab415c4"}]},
        {"plugins": [{"ide": "cursor", "buildSha": "e3caf7acdab415c4"}]},
    ]

    def fetch_status(_ide: str, _instance: str) -> dict:
        return (
            status_queue.pop(0)
            if status_queue
            else {"plugins": [{"ide": "cursor", "buildSha": "e3caf7acdab415c4"}]}
        )

    plan = rr.run_repair_pipeline(
        ide="cursor",
        instance="cursor-main",
        repo_root=repo,
        problems=[
            rr.RepairProblem(
                code="plugin_extension_stale_on_disk",
                severity="error",
                message="stale disk",
                context={"expected_build": "e3caf7acdab415c4"},
            )
        ],
        run_koru=lambda args: calls.append(list(args)) or 0,
        replay=lambda _ide, _instance, args: calls.append(list(args)) or 0,
        fetch_status=fetch_status,
    )
    assert any(a.action_id == "manual_vsix_unpack" and a.ok for a in plan.attempts)
    assert plan.resolved is True


def test_collect_problems_skips_plugin_when_daemon_stopped() -> None:
    problems = rr.collect_problems_from_status(
        None,
        ide="cursor",
        expected_build="e3caf7acdab415c4",
        daemon_running=False,
    )
    assert problems == []


def test_run_repair_pipeline_ensure_daemon_before_reload() -> None:
    daemon_calls = 0
    reload_calls: list[str] = []

    def ensure_daemon() -> int:
        nonlocal daemon_calls
        daemon_calls += 1
        return 0

    def ide_reload(ide: str, _repo: Path | None) -> rr.RepairAttempt:
        reload_calls.append(ide)
        return rr.RepairAttempt(action_id="reload_ide", mode="auto", ok=True, message="ok")

    plan = rr.run_repair_pipeline(
        ide="cursor",
        instance="cursor-main",
        repo_root=None,
        problems=[
            rr.RepairProblem(code="daemon_not_running", severity="warning", message="stopped"),
            rr.RepairProblem(
                code="plugin_not_connected",
                severity="error",
                message="not connected",
            ),
        ],
        run_koru=lambda _args: 0,
        replay=lambda _ide, _instance, _args: 0,
        fetch_status=lambda _ide, _instance: {
            "plugins": [{"ide": "cursor", "buildSha": "e3caf7acdab415c4"}]
        },
        ensure_daemon=ensure_daemon,
        ide_reload=ide_reload,
        ide_connect=lambda _ide: rr.RepairAttempt(
            action_id="connect_plugin",
            mode="auto",
            ok=True,
            message="ok",
        ),
    )
    assert daemon_calls == 1
    assert reload_calls == ["cursor"]
    assert plan.resolved is True


def test_runtime_alignment_problem_gets_manual_guidance() -> None:
    plan = rr.run_repair_pipeline(
        ide="vscodium",
        instance="vscodium",
        repo_root=None,
        problems=[
            rr.RepairProblem(
                code="venv_alignment",
                severity="warning",
                message="virtual_env mismatch",
                fix_hint="source .venv/bin/activate && hash -r",
            )
        ],
        run_koru=lambda _args: 0,
        replay=lambda _ide, _instance, _args: 0,
        fetch_status=lambda _ide, _instance: {},
    )

    assert any(a.action_id == "runtime_guidance" and not a.automated for a in plan.attempts)


def test_unknown_problem_gets_manual_registry_extension_hint() -> None:
    plan = rr.run_repair_pipeline(
        ide="vscodium",
        instance="vscodium",
        repo_root=None,
        problems=[
            rr.RepairProblem(
                code="new_problem_code",
                severity="warning",
                message="new problem",
            )
        ],
        run_koru=lambda _args: 0,
        replay=lambda _ide, _instance, _args: 0,
        fetch_status=lambda _ide, _instance: {},
    )

    assert any(a.action_id == "manual_guidance:new_problem_code" for a in plan.attempts)
    assert "REPAIR_REGISTRY" in plan.attempts[-1].message
