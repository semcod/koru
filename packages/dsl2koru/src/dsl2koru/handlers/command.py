"""Compatibility write-command handlers delegated to ``coru.cli``."""

from __future__ import annotations

from typing import Any

from dsl2koru.handlers.argv import to_cli_args
from dsl2koru.handlers.runner import Runner, default_runner
from dsl2koru.result import DslResult


def run_command(
    payload: dict[str, Any],
    *,
    line: str,
    runner: Runner | None = None,
) -> DslResult:
    verb = str(payload["verb"]).upper()
    argv = to_cli_args(payload)
    if not argv:
        return DslResult(ok=True, verb=verb, command=line, action="noop")
    rc, stdout, stderr = (runner or default_runner)(argv)
    result = DslResult(
        ok=rc == 0,
        verb=verb,
        command=line,
        action=argv[0],
        output=(stdout or "").strip(),
        data={"argv": argv},
    )
    if rc != 0:
        result.error = stderr.strip() if stderr else None
    return result
