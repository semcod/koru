"""Ticket emission helpers for ``koru.scan --apply``."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from koru.scan_types import CreateTicketResult, ScanResult, Suggestion


def create_ticket(
    project: Path,
    suggestion: Suggestion,
    *,
    source: str,
    runner: Callable[[Sequence[str], Path], Any] | None,
    create_nl_task: Callable[..., Any],
    format_create_exception: Callable[[Exception], str],
    suggestion_dedupe_key: Callable[[str, Suggestion], str],
    default_runner: Callable[[Sequence[str], Path], Any],
) -> CreateTicketResult:
    """Create one ticket via ``create_nl_task`` or ``planfile ticket create``."""
    if runner is None:
        try:
            created = create_nl_task(
                project,
                suggestion.description,
                priority=suggestion.priority,
                scaffold={
                    "labels": suggestion.labels,
                    "files": suggestion.files,
                    "title": suggestion.title,
                    "source_tool": source,
                    "source_context": {
                        "signal": suggestion.signal,
                        "dedupe_key": suggestion_dedupe_key(source, suggestion),
                        **suggestion.source_context,
                    },
                    "executor_kind": "human",
                    "executor_mode": "interactive",
                },
            )
            if getattr(created, "reused", False):
                return CreateTicketResult(ok=False, detail="task already exists (reused)")
            return CreateTicketResult(ok=True)
        except Exception as exc:
            return CreateTicketResult(ok=False, detail=format_create_exception(exc))

    use_runner = runner or default_runner
    cmd: list[str] = [
        "planfile",
        "ticket",
        "create",
        suggestion.title,
        "--priority",
        suggestion.priority,
        "--source",
        source,
        "--description",
        suggestion.description,
    ]
    for label in suggestion.labels:
        cmd.extend(["--label", label])
    for file_path in suggestion.files:
        cmd.extend(["--files", file_path])
    try:
        result = use_runner(cmd, project)
    except (FileNotFoundError, OSError) as exc:
        return CreateTicketResult(ok=False, detail=format_create_exception(exc))
    if result.returncode == 0:
        return CreateTicketResult(ok=True)
    detail = (result.stderr or result.stdout or "").strip()
    return CreateTicketResult(ok=False, detail=detail)


def is_reused_create_detail(detail: str) -> bool:
    normalized = detail.strip().lower()
    return "reused" in normalized or "already exists" in normalized


def normalize_create_detail(detail: str) -> str:
    detail = (detail or "").strip()
    return detail.replace("\n", " ") if detail else ""


def log_scan_decision(
    suggestion: Suggestion,
    *,
    decision: str,
    reason: str | None,
    message: str,
    record_scan_activity: Callable[..., None],
) -> None:
    payload: dict[str, Any] = {
        "decision": decision,
        "signal": suggestion.signal,
        "title": suggestion.title,
        "priority": suggestion.priority,
    }
    if reason is not None:
        payload["reason"] = reason
    record_scan_activity(
        message,
        preview=suggestion.description,
        data=payload,
    )


def apply_create_result(
    suggestion: Suggestion,
    create_result: CreateTicketResult,
    *,
    applied: list[str],
    skipped: list[str],
    skipped_as_duplicate: list[str],
    skipped_create_failed: list[str],
    skipped_create_failed_details: list[str],
    log_scan_decision: Callable[..., None],
    is_reused_create_detail: Callable[[str], bool],
    normalize_create_detail: Callable[[str], str],
) -> None:
    if create_result.ok:
        applied.append(suggestion.title)
        log_scan_decision(
            suggestion,
            decision="applied",
            reason=None,
            message=f"ticket ze skanu: {suggestion.title} (priority={suggestion.priority})",
        )
        return

    skipped.append(suggestion.title)
    detail = normalize_create_detail(create_result.detail or "")
    if detail and is_reused_create_detail(detail):
        skipped_as_duplicate.append(suggestion.title)
        log_scan_decision(
            suggestion,
            decision="skipped",
            reason="duplicate_reused",
            message=(
                f"pomijam ze skanu (ticket już istnieje / reused): {suggestion.title} "
                f"(signal={suggestion.signal} — {detail[:180]})"
            ),
        )
        return

    skipped_create_failed.append(suggestion.title)
    if detail:
        skipped_create_failed_details.append(f"{suggestion.title}: {detail[:240]}")
    fallback_hint = " — sprawdź `.planfile/` uprawnienia/lock"
    log_scan_decision(
        suggestion,
        decision="skipped",
        reason="create_failed",
        message=(
            f"pomijam ze skanu (planfile odrzucił create): {suggestion.title} "
            f"(signal={suggestion.signal}"
            + (f" — {detail[:180]}" if detail else fallback_hint)
            + ")"
        ),
    )


def apply_scan_suggestions(
    project: Path,
    suggestions: list[Suggestion],
    *,
    source: str,
    runner: Callable[[Sequence[str], Path], Any] | None,
    existing_scan_titles: Callable[..., set[str]],
    scan_duplicate_skip: Callable[[Suggestion, set[str]], tuple[str, str] | None],
    create_ticket: Callable[..., CreateTicketResult],
    apply_create_result: Callable[..., None],
    log_scan_decision: Callable[..., None],
) -> ScanResult:
    existing = existing_scan_titles(project, source=source, runner=runner)
    applied: list[str] = []
    skipped: list[str] = []
    skipped_as_duplicate: list[str] = []
    skipped_create_failed: list[str] = []
    skipped_create_failed_details: list[str] = []

    for suggestion in suggestions:
        duplicate = scan_duplicate_skip(suggestion, existing)
        if duplicate is not None:
            reason, message = duplicate
            skipped.append(suggestion.title)
            skipped_as_duplicate.append(suggestion.title)
            log_scan_decision(suggestion, decision="skipped", reason=reason, message=message)
            continue

        create_result = create_ticket(project, suggestion, source=source, runner=runner)
        apply_create_result(
            suggestion,
            create_result,
            applied=applied,
            skipped=skipped,
            skipped_as_duplicate=skipped_as_duplicate,
            skipped_create_failed=skipped_create_failed,
            skipped_create_failed_details=skipped_create_failed_details,
        )

    return ScanResult(
        suggestions=suggestions,
        applied=applied,
        skipped=skipped,
        skipped_as_duplicate=skipped_as_duplicate,
        skipped_create_failed=skipped_create_failed,
        skipped_create_failed_details=skipped_create_failed_details,
    )
