"""Tests for `koru autonomous` one-command loop."""

from __future__ import annotations

import os
from types import SimpleNamespace

from koru import autonomous as autonomous_mod
from koru.scan import ScanResult


def test_effective_flags_matrix() -> None:
    assert autonomous_mod._effective_flags("queue") == (False, False)
    assert autonomous_mod._effective_flags("scan") == (True, False)
    assert autonomous_mod._effective_flags("all") == (True, True)


def test_resolve_autopilot_ide_env_overrides_cli(monkeypatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "cursor")
    assert autonomous_mod._resolve_autopilot_ide("vscode") == "cursor"
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    assert autonomous_mod._resolve_autopilot_ide("vscode") == "vscode"


def test_resolve_autopilot_ide_ignores_bad_env(monkeypatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "not-a-real-ide")
    assert autonomous_mod._resolve_autopilot_ide("jetbrains") == "jetbrains"


def test_resolve_autopilot_ide_auto_env_does_not_override_cli(monkeypatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "auto")
    assert autonomous_mod._resolve_autopilot_ide("cursor") == "cursor"


def test_apply_agent_lane_environ_auto_cursor(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    (tmp_path / ".cursor").mkdir()
    lane = autonomous_mod._apply_agent_lane_environ(tmp_path, "auto")
    assert lane == "cursor"
    assert os.environ["KORU_AUTOPILOT_INSTANCE"] == "cursor"


def test_apply_agent_lane_environ_none_is_noop(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "keep-me")
    lane = autonomous_mod._apply_agent_lane_environ(tmp_path, "none")
    assert lane is None
    assert os.environ["KORU_AUTOPILOT_INSTANCE"] == "keep-me"


def test_autonomous_main_prepends_up_for_flags(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        autonomous_mod,
        "init_project",
        lambda project, force=False: SimpleNamespace(project=project),
    )
    monkeypatch.setattr(
        autonomous_mod,
        "run_planfile_queue_loop",
        lambda **kwargs: SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=0 last_status=idle",
            last_status="idle",
        ),
    )
    monkeypatch.setattr(autonomous_mod.time, "sleep", lambda _s: None)

    rc = autonomous_mod.autonomous_main(
        [
            "--project",
            str(tmp_path),
            "--max-cycles",
            "1",
            "--sleep-seconds",
            "0",
            "--ticket-sources",
            "queue",
            "--no-autopilot",
        ]
    )
    assert rc == 0


def test_up_single_cycle_queue_only_no_autopilot(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        autonomous_mod,
        "init_project",
        lambda project, force=False: SimpleNamespace(project=project),
    )

    queue_calls: list[dict] = []

    def fake_queue_loop(**kwargs):
        queue_calls.append(kwargs)
        return SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=0 last_status=idle",
            last_status="idle",
        )

    monkeypatch.setattr(autonomous_mod, "run_planfile_queue_loop", fake_queue_loop)
    monkeypatch.setattr(autonomous_mod.time, "sleep", lambda _s: None)

    rc = autonomous_mod.autonomous_main(
        [
            "up",
            "--project",
            str(tmp_path),
            "--max-cycles",
            "1",
            "--sleep-seconds",
            "0",
            "--ticket-sources",
            "queue",
            "--no-autopilot",
        ]
    )

    assert rc == 0
    assert len(queue_calls) == 1
    assert queue_calls[0]["queue_name"] == "default"


def test_up_single_cycle_all_sources_runs_scan(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        autonomous_mod,
        "init_project",
        lambda project, force=False: SimpleNamespace(project=project),
    )
    monkeypatch.setattr(
        autonomous_mod,
        "run_scan",
        lambda **kwargs: ScanResult(suggestions=[], applied=[], skipped=[]),
    )
    monkeypatch.setattr(
        autonomous_mod,
        "run_planfile_queue_loop",
        lambda **kwargs: SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=0 last_status=idle",
            last_status="idle",
        ),
    )
    monkeypatch.setattr(autonomous_mod.time, "sleep", lambda _s: None)

    rc = autonomous_mod.autonomous_main(
        [
            "up",
            "--project",
            str(tmp_path),
            "--max-cycles",
            "1",
            "--sleep-seconds",
            "0",
            "--ticket-sources",
            "all",
            "--no-autopilot",
        ]
    )

    assert rc == 0


def test_up_auto_installs_plugin_before_autopilot_loop(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        autonomous_mod,
        "init_project",
        lambda project, force=False: SimpleNamespace(project=project),
    )
    monkeypatch.setattr(
        autonomous_mod,
        "run_planfile_queue_loop",
        lambda **kwargs: SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=0 last_status=idle",
            last_status="idle",
        ),
    )
    monkeypatch.setattr(autonomous_mod.time, "sleep", lambda _s: None)

    install_calls: list[str] = []

    def fake_install_plugin_for_ide(*, ide):
        install_calls.append(ide)
        return SimpleNamespace(status="installed", ide=ide, message="ok", command=None)

    class FakeClient:
        def drive(self, *_args, **_kwargs):
            return {"ok": True, "backend": "plugin"}

    monkeypatch.setattr(autonomous_mod, "install_plugin_for_ide", fake_install_plugin_for_ide)
    monkeypatch.setattr(
        autonomous_mod,
        "format_plugin_install_result",
        lambda result: f"plugin {result.status} {result.ide}",
    )
    monkeypatch.setattr(
        autonomous_mod,
        "_start_or_reuse_daemon",
        lambda **kwargs: (FakeClient(), None, None),
    )

    rc = autonomous_mod.autonomous_main(
        [
            "up",
            "--project",
            str(tmp_path),
            "--max-cycles",
            "1",
            "--sleep-seconds",
            "0",
            "--ticket-sources",
            "queue",
            "--agent-lane",
            "none",
            "--autopilot-ide",
            "cursor",
        ]
    )

    assert rc == 0
    assert install_calls == ["cursor"]


def test_run_cycle_skips_autopilot_when_queue_waits_for_input(
    tmp_path,
    monkeypatch,
) -> None:
    class FailIfDrivenClient:
        def drive(self, *_args, **_kwargs):
            raise AssertionError("autopilot should not drive waiting_input queues")

    monkeypatch.setattr(
        autonomous_mod,
        "run_planfile_queue_loop",
        lambda **kwargs: SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input",
            last_status="waiting_input",
        ),
    )

    _scan_result, queue_result, autopilot_status = autonomous_mod._run_cycle(
        cycle=1,
        project=tmp_path,
        actor="koru-test",
        queue_name=None,
        enable_scan=False,
        max_iterations=50,
        enable_autopilot=True,
        autopilot_ide="auto",
        drive_prompt="continue with the next ticket",
        submit=True,
        client=FailIfDrivenClient(),
    )

    assert queue_result.last_status == "waiting_input"
    assert autopilot_status == "skipped"
