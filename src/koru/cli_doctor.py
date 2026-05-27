"""CLI command for running diagnostics."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import shlex
from pathlib import Path
from typing import Any

from koru.autonomy.environment import probe_socket_health
from koru.autopilot.ide import detect_terminal_host_ide_id, normalize_ide_id
from koru.autopilot.install_manager import repair_installation
from koru.doctor import detected_problems as doctor_detected_problems
from koru.doctor import problem_catalog as doctor_problem_catalog
from koru.doctor import render_problem_catalog_text
from koru.doctor import render_text as render_doctor_text
from koru.doctor import run_diagnostics
from koru.events import emit_management_event


def _doctor_selected_ide() -> str:
    raw = (
        os.environ.get("KORU_AUTOPILOT_IDE")
        or os.environ.get("KORU_AUTOPILOT_INSTANCE")
        or ""
    ).strip()
    normalized = normalize_ide_id(raw)
    if normalized:
        return normalized
    terminal = normalize_ide_id(detect_terminal_host_ide_id())
    return terminal or "auto"


def doctor_fix_payload(report: Any) -> dict[str, object]:
    """Guided remediation for ``koru --doctor --fix``.

    The root doctor is intentionally read-only. This payload tells a human or
    LLM operator which explicit commands may mutate the host/project.
    """
    project = str(report.project)
    ide = _doctor_selected_ide()
    failing = [c.name for c in report.checks if c.status == "fail"]
    warnings = [c.name for c in report.checks if c.status == "warn"]
    return {
        "mode": "guided",
        "writes_by_default": False,
        "failing_checks": failing,
        "warning_checks": warnings,
        "commands": [
            f"koru --doctor --project {shlex.quote(project)} --format json",
            f"koru --init --project {shlex.quote(project)}",
            f"koru --doctor --repair --project {shlex.quote(project)}",
            "koru autopilot doctor --fix",
            (
                f"KORU_AUTOPILOT_INSTANCE={shlex.quote(ide)} "
                f"koru autopilot daemon --project {shlex.quote(project)}"
            ),
            f"koru autopilot status --ide {shlex.quote(ide)} --explain",
            f"koru autopilot drive --ide {shlex.quote(ide)} --require-plugin 'probe test'",
            f"koru autopilot trace --project {shlex.quote(project)} --format drive-dsl --limit 30",
            f"koru ide doctor --ide {shlex.quote(ide)} --fix --gc-sockets --explain",
            "koru autopilot setup-host --install --dry-run",
            "koru autopilot setup-host --install",
            "koru autopilot install-plugin --dry-run --format json",
            "koru autopilot install-plugin",
            "koru autopilot install-unit",
            f"koru autonomous safe-up --project {shlex.quote(project)}",
        ],
        "notes": [
            "`koru --doctor --fix` only prints guidance; it does not edit files.",
            "`setup-host --install` may run apt and needs sudo on Debian/Ubuntu.",
            "`install-plugin` mutates the selected IDE extension directory.",
            "After starting the daemon, reload/connect the IDE plugin if it is not listed by `status`.",
            "`--diagnostic-tickets` creates deduplicated planfile tickets for failed checks.",
        ],
    }


def _doctor_koru_bin() -> str:
    candidate = Path(sys.executable).with_name("koru")
    if candidate.exists():
        return str(candidate)
    return "koru"


def _start_autopilot_daemon_for_repair(*, ide: str, project: str) -> dict[str, object]:
    log_dir = Path(project) / ".planfile" / ".koru"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"doctor-autopilot-{ide}.log"
    env = os.environ.copy()
    env["KORU_AUTOPILOT_INSTANCE"] = ide
    command = [
        _doctor_koru_bin(),
        "autopilot",
        "daemon",
        "--idempotent",
        "--project",
        project,
    ]
    with log_path.open("ab") as stream:
        proc = subprocess.Popen(
            command,
            cwd=project,
            env=env,
            stdout=stream,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    socket_path = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / f"koru-autopilot-{ide}.sock"
    listening = False
    for _ in range(20):
        health = probe_socket_health(socket_path)
        listening = health.listening
        if listening:
            break
        time.sleep(0.1)
    return {
        "action": "start_daemon",
        "status": "started" if listening else "starting",
        "pid": proc.pid,
        "socket": str(socket_path),
        "log": str(log_path),
    }


def doctor_repair_payload(report: Any) -> dict[str, object]:
    project = str(report.project)
    ide = _doctor_selected_ide()
    install_report = repair_installation(ide=ide, dry_run=False)
    daemon_action = _start_autopilot_daemon_for_repair(ide=ide, project=project)
    return {
        "mode": "repair",
        "ide": ide,
        "writes_by_default": True,
        "actions": [
            {
                "action": "repair_installation",
                "ok": install_report.ok,
                "issues": [issue.to_dict() for issue in install_report.issues],
                "actions": install_report.actions,
            },
            daemon_action,
        ],
        "notes": [
            "The daemon was started in the background for the selected IDE lane.",
            "Reload the IDE window and run `koru: Connect autopilot daemon` if the plugin is not listed by `status`.",
        ],
    }


def render_doctor_with_fix(report: Any, fix_payload: dict[str, object] | None) -> str:
    text = render_doctor_text(report)
    if fix_payload is None:
        return text
    lines = [text, "", "Guided repair (--fix):"]
    for command in fix_payload.get("commands", []):
        lines.append(f"  - {command}")
    notes = fix_payload.get("notes")
    if isinstance(notes, list) and notes:
        lines.append("Notes:")
        for note in notes:
            lines.append(f"  - {note}")
    return "\n".join(lines)


def render_doctor_with_repair(report: Any, repair_payload: dict[str, object]) -> str:
    lines = [render_doctor_text(report), "", "Applied repair (--repair):"]
    for action in repair_payload.get("actions", []):
        if not isinstance(action, dict):
            continue
        name = action.get("action")
        status = action.get("status") or action.get("ok")
        detail = []
        if action.get("pid"):
            detail.append(f"pid={action['pid']}")
        if action.get("socket"):
            detail.append(f"socket={action['socket']}")
        if action.get("log"):
            detail.append(f"log={action['log']}")
        suffix = f"; {'; '.join(detail)}" if detail else ""
        lines.append(f"  - {name}: {status}{suffix}")
    notes = repair_payload.get("notes")
    if isinstance(notes, list) and notes:
        lines.append("Notes:")
        for note in notes:
            lines.append(f"  - {note}")
    return "\n".join(lines)


def _doctor_emit_management_event(report: Any, args: argparse.Namespace) -> None:
    emit_management_event(
        tool="koru.doctor",
        action="completed",
        status="failed" if report.has_failures else "completed",
        level="error" if report.has_failures else "info",
        message=", ".join(f"{k}={v}" for k, v in report.summary().items() if v),
        queue=args.queue_name,
        details={"project": str(args.project)},
    )


def doctor_main(args: argparse.Namespace, raw_args: list[str]) -> int:
    report = run_diagnostics(args.project)
    repair_payload = doctor_repair_payload(report) if getattr(args, "repair", False) else None
    if repair_payload is not None:
        report = run_diagnostics(args.project)
    fix_payload = doctor_fix_payload(report) if getattr(args, "fix", False) else None
    include_catalog = bool(getattr(args, "catalog", False))
    problems = doctor_detected_problems(report)
    explicit_format = "--format" in raw_args
    if explicit_format and args.output_format == "json":
        print(_doctor_json_output(report, problems, fix_payload, repair_payload, include_catalog))
    elif explicit_format and args.output_format == "markdown":
        print(_doctor_markdown_output(report, fix_payload, repair_payload, include_catalog))
    else:
        print(_doctor_text_output(report, fix_payload, repair_payload, include_catalog))
    _doctor_emit_management_event(report, args)
    return 1 if report.has_failures else 0


def _doctor_json_output(
    report: Any,
    problems: list[Any],
    fix_payload: dict[str, Any] | None,
    repair_payload: dict[str, Any] | None,
    include_catalog: bool,
) -> str:
    payload = report.to_dict()
    payload["detected_problems"] = problems
    if include_catalog:
        payload["problem_catalog"] = doctor_problem_catalog()
    if fix_payload is not None:
        payload["fix"] = fix_payload
    if repair_payload is not None:
        payload["repair"] = repair_payload
    return json.dumps(payload, indent=2, sort_keys=True)


def _doctor_markdown_output(
    report: Any,
    fix_payload: dict[str, Any] | None,
    repair_payload: dict[str, Any] | None,
    include_catalog: bool,
) -> str:
    return _doctor_text_output(report, fix_payload, repair_payload, include_catalog)


def _doctor_text_output(
    report: Any,
    fix_payload: dict[str, Any] | None,
    repair_payload: dict[str, Any] | None,
    include_catalog: bool,
) -> str:
    text = (
        render_doctor_with_repair(report, repair_payload)
        if repair_payload is not None
        else render_doctor_with_fix(report, fix_payload)
    )
    if include_catalog:
        return f"{text}\n\n{render_problem_catalog_text()}"
    return text


def build_doctor_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru doctor",
        description=(
            "Diagnose project environment, configuration, and known failure patterns."
        ),
    )
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["json", "markdown", "text"],
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Include guided repair commands without mutating files.",
    )
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Apply safe autopilot repairs, then rerun diagnostics.",
    )
    parser.add_argument(
        "--catalog",
        action="store_true",
        help="Include known problems catalog (check -> detection rule).",
    )
    parser.add_argument(
        "--queue-name",
        default=None,
        help=argparse.SUPPRESS,
    )
    return parser


def doctor_subcommand_main(argv: list[str]) -> int:
    args = build_doctor_parser().parse_args(argv)
    return doctor_main(args, argv)
