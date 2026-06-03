"""``koru autopilot drive`` command implementation (R5b).

Extracted from :mod:`koru.autopilot.cli_command` to isolate drive logic
(daemon communication, fallback handling, direct injection) into a cohesive module.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from koru.autopilot.drive_repair_policy import (
    DriveRepairReaction,
    decide_drive_repair_reaction,
)
from koru.autopilot.log_contract import emit_log
from koru.control_commands import shell_command

if TYPE_CHECKING:
    from koru.autopilot.client import AutopilotClient


def _drive_text_from_args(args: argparse.Namespace) -> tuple[str | None, int]:
    prompt_file = getattr(args, "prompt_file", None)
    if prompt_file is not None:
        try:
            return Path(prompt_file).read_text(encoding="utf-8"), 0
        except OSError as exc:
            print(
                f"koru autopilot drive: cannot read --prompt-file {prompt_file}: {exc}",
                file=sys.stderr,
            )
            return None, 2
    text = str(args.prompt).strip() if args.prompt is not None else " ".join(args.text).strip()
    if text.strip():
        return text, 0
    print(
        "koru autopilot drive: missing text — pass words after `drive`, "
        "or use --prompt / -p '...'",
        file=sys.stderr,
    )
    return None, 2


def _drive_command_argv(args: argparse.Namespace, text: str) -> list[str]:
    """Build command argv for shell_command logging."""
    drive_argv = ["koru", "autopilot", "drive", "--ide", str(args.ide)]
    if not args.submit:
        drive_argv.append("--no-submit")
    if args.require_plugin:
        drive_argv.append("--require-plugin")
    if getattr(args, "direct", False):
        drive_argv.append("--direct")
    prompt_file = getattr(args, "prompt_file", None)
    if prompt_file is not None:
        drive_argv.extend(["--prompt-file", str(prompt_file)])
        return drive_argv
    if args.prompt is not None:
        drive_argv.extend(["--prompt", text])
    else:
        drive_argv.append(text)
    return drive_argv


def _record_drive_command(args: argparse.Namespace, text: str) -> Path:
    project = getattr(args, "project", None) or Path.cwd()
    shell_command(
        project,
        corr="cli-drive",
        argv=_drive_command_argv(args, text),
        cwd=str(project.resolve()),
        actor="operator",
        replayable=not args.dry_run,
    )
    return project


def _connect_drive_client(
    args: argparse.Namespace,
    *,
    client_fn: callable,
    daemon_start_hint_fn: callable,
) -> tuple[AutopilotClient | None, int]:
    client: AutopilotClient = client_fn(args)
    if client.is_running():
        return client, 0
    print(
        "koru autopilot drive: daemon not running. "
        f"{daemon_start_hint_fn(args)}",
        file=sys.stderr,
    )
    return None, 2


def _drive_daemon(
    client: AutopilotClient,
    args: argparse.Namespace,
    text: str,
) -> tuple[dict, int]:
    try:
        reply = client.drive(
            text,
            submit=args.submit,
            ide=args.ide,
            require_plugin=args.require_plugin,
        )
    except (OSError, RuntimeError) as exc:
        print(f"koru autopilot drive: {exc}", file=sys.stderr)
        return {}, 1
    return reply, -1


def _run_direct_fallback(
    args: argparse.Namespace,
    text: str,
    reply: dict,
    *,
    run_direct_drive_fn: callable,
) -> int:
    print(
        "koru autopilot drive: daemon could not open/focus chat input; "
        "falling back to local --direct injection",
        file=sys.stderr,
    )
    rc, direct_payload = run_direct_drive_fn(args, text, emit_payload=False)
    if direct_payload is None:
        print(json.dumps(reply, indent=2, sort_keys=True))
        return 1
    direct_payload = dict(direct_payload)
    direct_payload["daemon_fallback"] = {
        "ok": reply.get("ok"),
        "message": reply.get("message"),
        "opened": reply.get("opened"),
        "submitted": reply.get("submitted"),
    }
    print(json.dumps(direct_payload, indent=2, sort_keys=True))
    return rc


def _bridge_subject(ide: str, project: Path) -> str:
    return f"ide-bridge:{ide}:{project.resolve()}"


def _bridge_hypotheses_payload(status) -> list[dict[str, object]]:
    return [
        {
            "id": h.id,
            "confidence": h.confidence,
            "evidence": h.evidence,
            "remediation": h.remediation.summary,
            "remediation_kind": h.remediation.kind,
            "remediation_command": h.remediation.command,
        }
        for h in status.hypotheses
    ]


def _bridge_status_payload(status) -> dict[str, object]:
    return {
        "ide": status.ide,
        "socket": status.socket_path,
        "project": status.project,
        "daemon_running": status.daemon_running,
        "plugins_connected": status.plugins_connected,
        "plugins_compatible": status.plugins_compatible,
        "ready": status.ready,
        "fixes_applied": list(status.fixes_applied),
    }


def _diagnose_bridge_after_drive_failure(
    args: argparse.Namespace,
    client: AutopilotClient,
    reply: dict,
) -> DriveRepairReaction | None:
    if bool(reply.get("ok", True)):
        return None
    raw_socket_path = getattr(client, "socket_path", None) or getattr(args, "socket", None)
    if raw_socket_path is None:
        return None
    try:
        socket_path = Path(raw_socket_path)
    except TypeError:
        return None

    from koru.bounded_contexts.repairs import RepairCommandService, RepairQueryService
    from koru.bounded_contexts.repairs.commands import (
        RecordRepairAttemptCommand,
        RecordRepairDiagnosticCommand,
    )
    from koru.bounded_contexts.repairs.queries import LoadRepairHistoryQuery
    from koru.cqrs import runtime_for_project
    from koru.ide_adapters.bridge import evaluate_bridge

    project = (getattr(args, "project", None) or Path.cwd()).expanduser().resolve()
    ide = str(getattr(args, "ide", "auto") or "auto")
    try:
        status = evaluate_bridge(ide=ide, socket_path=socket_path, project=project)
    except (OSError, RuntimeError, TypeError, ValueError):
        return None

    runtime = runtime_for_project(project)
    commands = RepairCommandService(runtime)
    queries = RepairQueryService(runtime)
    hypotheses = _bridge_hypotheses_payload(status)
    primary = hypotheses[0]["id"] if hypotheses else "ready"
    subject = _bridge_subject(status.ide, project)
    recent_history = queries.history(LoadRepairHistoryQuery(subject=subject, limit=10))
    reaction = decide_drive_repair_reaction(
        status,
        require_plugin=bool(getattr(args, "require_plugin", False)),
        recent_events=recent_history,
    )
    commands.record_diagnostic(
        RecordRepairDiagnosticCommand(
            subject=subject,
            repair_kind="ide_bridge",
            project=str(project),
            summary=f"drive failed; ide={status.ide} ready={status.ready} primary={primary}",
            status={
                **_bridge_status_payload(status),
                "drive_reply": {
                    "ok": reply.get("ok"),
                    "message": reply.get("message"),
                    "backend": reply.get("backend"),
                    "opened": reply.get("opened"),
                    "submitted": reply.get("submitted"),
                },
            },
            hypotheses=hypotheses,
        )
    )

    if reaction.fallback_to_direct:
        commands.record_attempt(
            RecordRepairAttemptCommand(
                subject=subject,
                repair_kind="ide_bridge",
                project=str(project),
                attempted=True,
                ok=False,
                actions=["drive reaction: switch to local direct injection"],
                summary=f"ide={status.ide} {reaction.reason}; using direct fallback",
            )
        )
    elif reaction.action != "none":
        commands.record_attempt(
            RecordRepairAttemptCommand(
                subject=subject,
                repair_kind="ide_bridge",
                project=str(project),
                attempted=True,
                ok=False,
                actions=[f"drive reaction: {reaction.action}"],
                summary=f"ide={status.ide} {reaction.reason}",
            )
        )
    return reaction


def _finish_drive_reply(
    args: argparse.Namespace,
    text: str,
    reply: dict,
    *,
    client: AutopilotClient,
    run_direct_drive_fn: callable,
    should_fallback_fn: callable,
    repair_reaction_fn: callable | None = None,
) -> int:
    if should_fallback_fn(args, reply):
        return _run_direct_fallback(
            args,
            text,
            reply,
            run_direct_drive_fn=run_direct_drive_fn,
        )
    if not reply.get("ok", True):
        reaction_source = repair_reaction_fn or _diagnose_bridge_after_drive_failure
        reaction = reaction_source(args, client, reply)
        if reaction is not None and reaction.fallback_to_direct:
            print(
                "koru autopilot drive: bridge diagnostic selected local --direct "
                f"fallback ({reaction.reason})",
                file=sys.stderr,
            )
            return _run_direct_fallback(
                args,
                text,
                reply,
                run_direct_drive_fn=run_direct_drive_fn,
            )
        from koru.autonomy.ide_operator_guidance import (
            classify_drive_failure_guidance,
            emit_operator_guidance,
        )

        guidance = classify_drive_failure_guidance(reply, ide=str(args.ide))
        if guidance:
            emit_operator_guidance(guidance, title="Operator — IDE chat control")
    print(json.dumps(reply, indent=2, sort_keys=True))
    return 0 if reply.get("ok", True) else 1


def action_drive(
    args: argparse.Namespace,
    *,
    client_fn: callable,
    daemon_start_hint_fn: callable,
    run_direct_drive_fn: callable,
    should_fallback_fn: callable,
    repair_reaction_fn: callable | None = None,
) -> int:
    """Execute ``koru autopilot drive`` command.

    Args:
        args: Parsed command-line arguments
        client_fn: Factory for AutopilotClient (injected for testability)
        daemon_start_hint_fn: Function to generate daemon start hint message
        run_direct_drive_fn: Function to execute direct drive fallback
        should_fallback_fn: Function to check if fallback to direct drive is needed

    Returns:
        Exit code (0 success, 1 error, 2 usage error)
    """
    text, rc = _drive_text_from_args(args)
    if text is None:
        emit_log(
            args,
            component="autopilot.drive",
            level="error",
            action="validate_input",
            result="failed",
            rc=rc,
        )
        return rc
    _record_drive_command(args, text)
    emit_log(
        args,
        component="autopilot.drive",
        level="info",
        action="request",
        result="started",
        ide=str(args.ide),
        submit=bool(args.submit),
        require_plugin=bool(args.require_plugin),
        direct=bool(args.direct),
        chars=len(text),
    )

    if args.direct:
        rc, _payload = run_direct_drive_fn(args, text, emit_payload=True)
        emit_log(
            args,
            component="autopilot.drive",
            level="info" if rc == 0 else "error",
            action="direct",
            result="ok" if rc == 0 else "failed",
            rc=rc,
            ide=str(args.ide),
        )
        return rc

    client, rc = _connect_drive_client(
        args,
        client_fn=client_fn,
        daemon_start_hint_fn=daemon_start_hint_fn,
    )
    if client is None:
        emit_log(
            args,
            component="autopilot.drive",
            level="error",
            action="connect_daemon",
            result="failed",
            rc=rc,
            ide=str(args.ide),
        )
        return rc

    if args.dry_run:
        print(f"[dry-run] would send {len(text)} chars to daemon ide={args.ide}")
        emit_log(
            args,
            component="autopilot.drive",
            level="info",
            action="dry_run",
            result="ok",
            rc=0,
            ide=str(args.ide),
            chars=len(text),
        )
        return 0

    reply, rc = _drive_daemon(client, args, text)
    if rc != -1:
        emit_log(
            args,
            component="autopilot.drive",
            level="error",
            action="drive",
            result="failed",
            rc=rc,
            ide=str(args.ide),
        )
        return rc
    final_rc = _finish_drive_reply(
        args,
        text,
        reply,
        client=client,
        run_direct_drive_fn=run_direct_drive_fn,
        should_fallback_fn=should_fallback_fn,
        repair_reaction_fn=repair_reaction_fn,
    )
    emit_log(
        args,
        component="autopilot.drive",
        level="info" if final_rc == 0 else "error",
        action="drive",
        result="ok" if final_rc == 0 else "failed",
        rc=final_rc,
        ide=str(args.ide),
        backend=str(reply.get("backend") or ""),
        opened=reply.get("opened"),
        submitted=reply.get("submitted"),
    )
    return final_rc
