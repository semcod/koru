"""Validate planfile ticket evidence snapshots.

Generated tickets can outlive the artifact that produced them. This module
keeps that honest by comparing ``source.context.evidence`` hashes against the
current workspace and surfacing the exact regeneration command.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

Runner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class EvidenceFileCheck:
    kind: str
    path: str
    expected_sha256: str
    actual_sha256: str | None
    expected_size_bytes: int | None = None
    actual_size_bytes: int | None = None
    expected_mtime_ns: int | None = None
    actual_mtime_ns: int | None = None
    status: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "path": self.path,
            "expected_sha256": self.expected_sha256,
            "actual_sha256": self.actual_sha256,
            "expected_size_bytes": self.expected_size_bytes,
            "actual_size_bytes": self.actual_size_bytes,
            "expected_mtime_ns": self.expected_mtime_ns,
            "actual_mtime_ns": self.actual_mtime_ns,
            "status": self.status,
        }


@dataclass(frozen=True)
class TicketEvidenceValidation:
    ticket_id: str
    name: str
    status: str
    evidence_status: str
    regenerate_command: str = ""
    checks: list[EvidenceFileCheck] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "name": self.name,
            "status": self.status,
            "evidence_status": self.evidence_status,
            "regenerate_command": self.regenerate_command,
            "checks": [check.to_dict() for check in self.checks],
            "reason": self.reason,
        }


@dataclass(frozen=True)
class TicketEvidenceReport:
    project: str
    validations: list[TicketEvidenceValidation]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "validations": [validation.to_dict() for validation in self.validations],
        }

    @property
    def stale_count(self) -> int:
        return sum(1 for item in self.validations if item.evidence_status == "stale")

    @property
    def missing_evidence_count(self) -> int:
        return sum(1 for item in self.validations if item.evidence_status == "missing_evidence")

    @property
    def current_count(self) -> int:
        return sum(1 for item in self.validations if item.evidence_status == "current")


def validate_ticket_evidence(
    project: Path,
    *,
    ticket_id: str | None = None,
    status: str = "open",
    runner: Runner | None = None,
) -> TicketEvidenceReport:
    use_runner = runner or _run
    tickets = _load_tickets(project, ticket_id=ticket_id, status=status, runner=use_runner)
    return TicketEvidenceReport(
        project=str(project.resolve()),
        validations=[_validate_one_ticket(project, ticket) for ticket in tickets],
    )


def render_ticket_evidence_report(report: TicketEvidenceReport) -> str:
    lines = [
        f"koru queue validate-evidence: {report.project}",
        (
            "summary: "
            f"tickets={len(report.validations)} "
            f"current={report.current_count} "
            f"stale={report.stale_count} "
            f"missing_evidence={report.missing_evidence_count}"
        ),
    ]
    if not report.validations:
        lines.append("No tickets matched.")
        return "\n".join(lines)
    for item in report.validations:
        lines.append(
            f"- {item.ticket_id} [{item.evidence_status}] {item.name}",
        )
        if item.reason:
            lines.append(f"    reason: {item.reason}")
        for check in item.checks:
            lines.append(
                f"    {check.kind}: {check.path} -> {check.status} "
                f"(sha={_short(check.actual_sha256)}/{_short(check.expected_sha256)})",
            )
        if item.regenerate_command:
            lines.append(f"    regenerate: {item.regenerate_command}")
        if item.evidence_status == "missing_evidence":
            lines.append(
                "    next: recreate/update ticket with source.context.evidence and regenerate_command",
            )
        elif item.evidence_status != "current":
            lines.append(
                "    next: rerun regenerate_command, inspect changed hashes, then update/close the ticket",
            )
    return "\n".join(lines)


def _load_tickets(
    project: Path,
    *,
    ticket_id: str | None,
    status: str,
    runner: Runner,
) -> list[dict[str, Any]]:
    if ticket_id:
        result = runner(["planfile", "ticket", "show", ticket_id, "--format", "json"], project)
        _raise_on_planfile_error(result, "planfile ticket show")
        data = json.loads(result.stdout or "{}")
        return [data] if isinstance(data, dict) else []
    cmd = ["planfile", "ticket", "list", "--format", "json"]
    if status:
        cmd[3:3] = ["--status", status]
    result = runner(cmd, project)
    _raise_on_planfile_error(result, "planfile ticket list")
    data = json.loads(result.stdout or "[]")
    if not isinstance(data, list):
        return []
    return [_load_ticket_detail(project, ticket, runner) for ticket in data if isinstance(ticket, dict)]


def _load_ticket_detail(
    project: Path,
    ticket: dict[str, Any],
    runner: Runner,
) -> dict[str, Any]:
    ticket_id = str(ticket.get("id") or ticket.get("ticket_id") or "").strip()
    if not ticket_id:
        return ticket
    result = runner(["planfile", "ticket", "show", ticket_id, "--format", "json"], project)
    if result.returncode != 0:
        return ticket
    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return ticket
    return data if isinstance(data, dict) else ticket


def _validate_one_ticket(project: Path, ticket: dict[str, Any]) -> TicketEvidenceValidation:
    ticket_id, name, status = _ticket_identity(ticket)
    evidence = _ticket_evidence_block(ticket)
    if not isinstance(evidence, dict):
        return TicketEvidenceValidation(
            ticket_id=ticket_id,
            name=name,
            status=status,
            evidence_status="missing_evidence",
            reason="ticket has no source.context.evidence block",
        )
    checks = _evidence_checks(project, evidence)
    evidence_status, reason = _evidence_status_and_reason(checks)
    return TicketEvidenceValidation(
        ticket_id=ticket_id,
        name=name,
        status=status,
        evidence_status=evidence_status,
        regenerate_command=str(evidence.get("regenerate_command") or ""),
        checks=checks,
        reason=reason,
    )


def _ticket_identity(ticket: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(ticket.get("id") or ticket.get("ticket_id") or "-"),
        str(ticket.get("name") or ticket.get("title") or ""),
        str(ticket.get("status") or ""),
    )


def _ticket_evidence_block(ticket: dict[str, Any]) -> Any:
    source = ticket.get("source") if isinstance(ticket.get("source"), dict) else {}
    context = source.get("context") if isinstance(source, dict) else None
    return context.get("evidence") if isinstance(context, dict) else None


def _evidence_status_and_reason(checks: list[EvidenceFileCheck]) -> tuple[str, str]:
    if not checks:
        return "missing_evidence", "source.context.evidence has no artifact/files hashes to validate"
    if any(check.status in {"missing", "changed"} for check in checks):
        return "stale", "one or more evidence files no longer match the ticket snapshot"
    return "current", "all evidence hashes match"


def _evidence_checks(project: Path, evidence: dict[str, Any]) -> list[EvidenceFileCheck]:
    checks: list[EvidenceFileCheck] = []
    for kind in ("artifact", "planfile_tickets"):
        raw = evidence.get(kind)
        if isinstance(raw, dict):
            check = _check_evidence_file(project, kind, raw)
            if check is not None:
                checks.append(check)
    raw_files = evidence.get("files")
    if isinstance(raw_files, list):
        for raw in raw_files:
            if isinstance(raw, dict):
                check = _check_evidence_file(project, "file", raw)
                if check is not None:
                    checks.append(check)
    return checks


def _check_evidence_file(project: Path, kind: str, evidence: dict[str, Any]) -> EvidenceFileCheck | None:
    rel = str(evidence.get("path") or "").strip()
    expected_sha = str(evidence.get("sha256") or "").strip()
    if not rel or not expected_sha:
        return None
    path = project / rel
    expected_size = _int_or_none(evidence.get("size_bytes"))
    expected_mtime = _int_or_none(evidence.get("mtime_ns"))
    if not path.is_file():
        return EvidenceFileCheck(
            kind=kind,
            path=rel,
            expected_sha256=expected_sha,
            actual_sha256=None,
            expected_size_bytes=expected_size,
            expected_mtime_ns=expected_mtime,
            status="missing",
        )
    stat = path.stat()
    actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    actual_size = stat.st_size
    status = "current" if actual_sha == expected_sha and (
        expected_size is None or expected_size == actual_size
    ) else "changed"
    return EvidenceFileCheck(
        kind=kind,
        path=rel,
        expected_sha256=expected_sha,
        actual_sha256=actual_sha,
        expected_size_bytes=expected_size,
        actual_size_bytes=actual_size,
        expected_mtime_ns=expected_mtime,
        actual_mtime_ns=stat.st_mtime_ns,
        status=status,
    )


def _run(cmd: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(cmd),
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )


def _raise_on_planfile_error(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode == 0:
        return
    detail = (result.stderr or result.stdout or "").strip()
    raise RuntimeError(f"{label} failed (exit {result.returncode}): {detail}")


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _short(value: str | None) -> str:
    return value[:12] if value else "-"


__all__ = [
    "EvidenceFileCheck",
    "TicketEvidenceReport",
    "TicketEvidenceValidation",
    "render_ticket_evidence_report",
    "validate_ticket_evidence",
]
