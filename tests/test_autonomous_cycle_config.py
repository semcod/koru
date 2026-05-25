from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from koru.autonomous_cycle_config import compute_cycle_sleep, configure_loop_state


def test_configure_loop_state_uses_existing_agent_lane_env(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    args = SimpleNamespace(
        ticket_sources="default",
        queue_name="default",
        agent_lane="auto",
        autopilot_ide="auto",
        emit_events="human",
    )
    loop_state = object()

    def fail_apply_agent_lane_environ(project: Path, agent_lane: str) -> str:
        raise AssertionError("existing KORU_AUTOPILOT_INSTANCE should be reused")

    def fail_resolve_autopilot_ide(*args: object, **kwargs: object) -> tuple[str, str]:
        raise AssertionError("explicit lane should be used directly")

    enable_scan, queue_name, autopilot_ide, restored_state, checkpoint_path, restored_cycle = (
        configure_loop_state(
            args,
            tmp_path,
            effective_flags=lambda ticket_sources: (True, False),
            apply_agent_lane_environ=fail_apply_agent_lane_environ,
            resolve_autopilot_ide=fail_resolve_autopilot_ide,
            resolve_ide_route_fn=lambda *_args, **_kwargs: None,
            state_factory=lambda: loop_state,
            load_checkpoint=lambda *_args, **_kwargs: 7,
        )
    )

    assert enable_scan is True
    assert queue_name == "default"
    assert autopilot_ide == "vscode"
    assert restored_state is loop_state
    assert checkpoint_path == (tmp_path / ".planfile/.koru/autonomous-state.json").resolve()
    assert restored_cycle == 7


def test_compute_cycle_sleep_caps_plugin_reconnect_blockers() -> None:
    args = SimpleNamespace(
        sleep_seconds=60.0,
        max_sleep_seconds=900.0,
        backoff_on_stagnation=True,
    )
    loop_state = SimpleNamespace(
        stagnation_streak=8,
        last_message_sent_ts=0.0,
    )
    queue_result = SimpleNamespace(last_status="idle")

    sleep = compute_cycle_sleep(
        args,
        loop_state,
        queue_result,
        autopilot_status="skipped(plugin_version_mismatch)",
        compute_backoff_sleep=lambda *_args: 900.0,
        now=lambda: 500.0,
    )

    assert sleep == 15.0


def test_compute_cycle_sleep_keeps_backoff_for_plain_idle_skip() -> None:
    args = SimpleNamespace(
        sleep_seconds=60.0,
        max_sleep_seconds=900.0,
        backoff_on_stagnation=True,
    )
    loop_state = SimpleNamespace(
        stagnation_streak=8,
        last_message_sent_ts=0.0,
    )
    queue_result = SimpleNamespace(last_status="idle")

    sleep = compute_cycle_sleep(
        args,
        loop_state,
        queue_result,
        autopilot_status="skipped(idle_no_ticket)",
        compute_backoff_sleep=lambda *_args: 900.0,
        now=lambda: 500.0,
    )

    assert sleep == 900.0
