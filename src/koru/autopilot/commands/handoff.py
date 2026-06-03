"""``koru autopilot handoff`` command implementation (R5b).

Extracted from :mod:`koru.autopilot.cli_command` to isolate handoff logic
into a cohesive module.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from koru.autopilot.log_contract import emit_log

if TYPE_CHECKING:
    from koru.autopilot.client import AutopilotClient


def _build_brief(
    project: Path,
    *,
    build_context_fn: callable,
    render_markdown_handoff_fn: callable,
) -> str:
    """Build the koru markdown brief for ``project``.

    Args:
        project: Project path to build context for
        build_context_fn: Function to build project context
        render_markdown_handoff_fn: Function to render handoff markdown

    Returns:
        Markdown brief string
    """
    ctx = build_context_fn(project=project)
    return render_markdown_handoff_fn(ctx)


def action_handoff(
    args: argparse.Namespace,
    *,
    client_fn: callable,
    build_context_fn: callable,
    render_markdown_handoff_fn: callable,
) -> int:
    """Execute ``koru autopilot handoff`` command (P2.5).

    Builds the koru brief and pipes it through ``drive``.

    Args:
        args: Parsed command-line arguments
        client_fn: Factory for AutopilotClient
        build_context_fn: Function to build project context
        render_markdown_handoff_fn: Function to render handoff markdown

    Returns:
        Exit code (0 success, 1 error, 2 daemon not running)
    """
    project = args.project.resolve()
    emit_log(
        args,
        component="autopilot.handoff",
        level="info",
        action="request",
        result="started",
        ide=str(args.ide),
        submit=bool(args.submit),
        require_plugin=bool(args.require_plugin),
    )
    try:
        brief = _build_brief(
            project,
            build_context_fn=build_context_fn,
            render_markdown_handoff_fn=render_markdown_handoff_fn,
        )
    except Exception as exc:  # pragma: no cover — surfaces context errors
        print(f"koru autopilot handoff: {exc}", file=sys.stderr)
        emit_log(
            args,
            component="autopilot.handoff",
            level="error",
            action="build_brief",
            result="failed",
            rc=1,
            reason=str(exc),
        )
        return 1
    if not brief.strip():
        print("koru autopilot handoff: empty brief, refusing to drive", file=sys.stderr)
        emit_log(
            args,
            component="autopilot.handoff",
            level="error",
            action="validate_brief",
            result="failed",
            rc=1,
        )
        return 1
    if args.dry_run:
        print(brief)
        emit_log(
            args,
            component="autopilot.handoff",
            level="info",
            action="dry_run",
            result="ok",
            rc=0,
            chars=len(brief),
        )
        return 0
    client = client_fn(args)
    if not client.is_running():
        print(
            "koru autopilot handoff: daemon not running. Start it with `koru autopilot daemon`.",
            file=sys.stderr,
        )
        emit_log(
            args,
            component="autopilot.handoff",
            level="error",
            action="check_daemon",
            result="failed",
            rc=2,
        )
        return 2
    try:
        reply = client.drive(
            brief,
            submit=args.submit,
            ide=args.ide,
            require_plugin=args.require_plugin,
        )
    except (OSError, RuntimeError) as exc:
        print(f"koru autopilot handoff: {exc}", file=sys.stderr)
        emit_log(
            args,
            component="autopilot.handoff",
            level="error",
            action="drive",
            result="failed",
            rc=1,
            reason=str(exc),
        )
        return 1
    summary = {
        "ok": reply.get("ok", False),
        "chars": len(brief),
        "ide": args.ide,
        "submit": args.submit,
        "backend": reply.get("backend") or ("plugin" if reply.get("delivered") else "?"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    rc = 0 if reply.get("ok", True) else 1
    emit_log(
        args,
        component="autopilot.handoff",
        level="info" if rc == 0 else "error",
        action="drive",
        result="ok" if rc == 0 else "failed",
        rc=rc,
        chars=len(brief),
        backend=summary.get("backend"),
    )
    return rc
