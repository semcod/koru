"""Write command handlers — delegate to coru.cli via runner."""

from __future__ import annotations

from typing import Any

from dsl2coru.handlers.argv import to_cli_args
from dsl2coru.handlers.runner import Runner, default_runner
from dsl2coru.result import DslResult


def run_command(
    payload: dict[str, Any],
    *,
    line: str,
    runner: Runner | None = None,
) -> DslResult:
    verb = str(payload["verb"]).upper()
    runner_fn = runner or default_runner
    argv = to_cli_args(payload)
    if not argv:
        return DslResult(ok=True, verb=verb, command=line, action="noop")
    rc, stdout, stderr = runner_fn(argv)
    data = {"argv": argv}
    output = (stdout or "").strip()
    error = stderr.strip() if stderr else None
    if rc != 0:
        return DslResult(
            ok=False,
            verb=verb,
            command=line,
            action=argv[0],
            output=output,
            data=data,
            error=error,
        )
    return DslResult(
        ok=True,
        verb=verb,
        command=line,
        action=argv[0],
        output=output,
        data=data,
    )
