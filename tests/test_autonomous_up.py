from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from koru.autonomous_up import (
    AutonomousUpContext,
    autonomous_context_resource_kwargs,
    run_autonomous_up_loop,
)


def test_autonomous_context_resource_kwargs_maps_resource_tuple() -> None:
    resources = (
        "client",
        "daemon",
        "thread",
        Path("/tmp/socket"),
        True,
        False,
        "operator",
        "vscodium",
        "loop-state",
        Path("/tmp/checkpoint"),
        42,
        Path("/tmp/diag"),
        "wup",
        "pipeline",
    )

    mapped = autonomous_context_resource_kwargs(resources)

    assert mapped["client"] == "client"
    assert mapped["autopilot_ide"] == "vscodium"
    assert mapped["restored_cycle"] == 42
    assert mapped["auto_pipeline_state"] == "pipeline"


def test_run_autonomous_up_loop_runs_prechecks_cycle_and_cleanup() -> None:
    calls: list[str] = []
    context = AutonomousUpContext(
        args=SimpleNamespace(emit_events="human"),
        previous_stdio_format_env="old",
        strict_env={"KORU_STRICT_PLUGIN_VERSION": (False, None)},
        correlation_id="cid",
        project=Path("/tmp/project"),
        startup_probe=object(),
        client=object(),
        daemon=object(),
        thread=object(),
        socket_path=Path("/tmp/socket"),
        autopilot_socket_observed_at_boot=True,
        enable_scan=True,
        queue_name="operator",
        autopilot_ide="vscodium",
        loop_state=object(),
        checkpoint_path=Path("/tmp/checkpoint"),
        restored_cycle=4,
        diagnostic_state_dir=Path("/tmp/diag"),
        wup_process=object(),
        auto_pipeline_state=object(),
    )

    rc = run_autonomous_up_loop(
        context,
        install_sigterm_handler=lambda _args, _state: "previous-sigterm",
        run_pre_checks=lambda *_args: calls.append("prechecks") or (True, True),
        run_autonomous_cycle=lambda **kwargs: calls.append(f"cycle={kwargs['cycle']}") or True,
        handle_interrupt=lambda *_args, **_kwargs: 130,
        restore_env_vars=lambda _snapshot: calls.append("restore"),
        cleanup_session=lambda *_args: calls.append("cleanup"),
    )

    assert rc == 0
    assert calls == ["prechecks", "cycle=5", "restore", "cleanup"]
