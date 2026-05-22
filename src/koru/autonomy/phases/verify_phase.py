"""Verification phase logic for autonomous cycle."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from koru.autonomy.post_run_verify import load_post_run_verify_config, verify_after_ide_work
from koru.autonomy.state import AutoloopState
from koru.queue import run_process as _run_process
from koru.queue import run_shell_command as _run_shell_command


def handle_post_run_verify_ide(
    project: Path,
    state: AutoloopState,
    cycle: int,
    _hp: Callable[..., Any],
    _emit: Callable[..., Any],
) -> Any:
    verify_config = load_post_run_verify_config(project)
    ide_verify_outcomes = verify_after_ide_work(
        project,
        state,
        config=verify_config,
        planfile_runner=_run_process,
        shell_runner=_run_shell_command,
    )
    if ide_verify_outcomes:
        failed_ide = [o for o in ide_verify_outcomes if not o.get("ok")]
        _hp(
            f"  post_run_verify (IDE): tickets={len(ide_verify_outcomes)} failed={len(failed_ide)}",
        )
        _emit(
            "PostRunVerifyIdeCompleted",
            {
                "cycle": cycle,
                "ticket_count": len(ide_verify_outcomes),
                "failed_count": len(failed_ide),
                "outcomes": ide_verify_outcomes,
            },
            command="; ".join(verify_config.commands) if verify_config else None,
        )
    return verify_config
