"""CLI command for running diagnostics."""

from __future__ import annotations

import argparse
import json
import shlex
from typing import Any

from koru.doctor import detected_problems as doctor_detected_problems
from koru.doctor import problem_catalog as doctor_problem_catalog
from koru.doctor import render_problem_catalog_text
from koru.doctor import render_text as render_doctor_text
from koru.doctor import run_diagnostics
from koru.events import emit_management_event


def doctor_fix_payload(report: Any) -> dict[str, object]:
    """Guided remediation for ``koru --doctor --fix``.

    The root doctor is intentionally read-only. This payload tells a human or
    LLM operator which explicit commands may mutate the host/project.
    """
    project = str(report.project)
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
            "koru autopilot doctor --fix",
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
            "`--diagnostic-tickets` creates deduplicated planfile tickets for failed checks.",
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


def doctor_main(args: argparse.Namespace, raw_args: list[str]) -> int:
    report = run_diagnostics(args.project)
    fix_payload = doctor_fix_payload(report) if getattr(args, "fix", False) else None
    include_catalog = bool(getattr(args, "catalog", False))
    problems = doctor_detected_problems(report)
    explicit_format = "--format" in raw_args
    if explicit_format and args.output_format == "json":
        payload = report.to_dict()
        payload["detected_problems"] = problems
        if include_catalog:
            payload["problem_catalog"] = doctor_problem_catalog()
        if fix_payload is not None:
            payload["fix"] = fix_payload
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif explicit_format and args.output_format == "markdown":
        text = render_doctor_with_fix(report, fix_payload)
        if include_catalog:
            text = f"{text}\n\n{render_problem_catalog_text()}"
        print(text)
    else:
        text = render_doctor_with_fix(report, fix_payload)
        if include_catalog:
            text = f"{text}\n\n{render_problem_catalog_text()}"
        print(text)
    emit_management_event(
        tool="koru.doctor",
        action="completed",
        status="failed" if report.has_failures else "completed",
        level="error" if report.has_failures else "info",
        message=", ".join(f"{k}={v}" for k, v in report.summary().items() if v),
        queue=args.queue_name,
        details={"project": str(args.project)},
    )
    return 1 if report.has_failures else 0
