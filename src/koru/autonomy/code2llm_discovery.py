"""Automatic broad project discovery via ``code2llm`` when the queue is idle.

When ``koru auto`` finds an empty planfile queue, instead of asking an IDE
operator to run ``code2llm`` manually we attempt to:

1. Detect a working ``code2llm`` binary on ``PATH``.
2. Generate fresh analysis artifacts (``analysis.toon.yaml``, ``map.toon.yaml``,
   ``planfile-tickets.yaml`` etc.) under ``./project/``.
3. Apply the planfile-tickets directly through ``planfile ticket create``.

Each step is best-effort: any failure is reported as a structured outcome so
the caller can fall back to the legacy "create operator ticket" flow.
"""

from __future__ import annotations

import json
import hashlib
import shutil
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

Runner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]

DEFAULT_OUTPUT_SUBDIR = "project"
DEFAULT_FORMATS = "all"
# Default exclude patterns for ``code2llm`` runs.
#
# - ``*.md``: markdown files (docs) — analysing them adds noise to the
#   refactor candidates and bloats the artifact size.
# - ``plugins``: the IDE plugin folder. Each IDE has its own dedicated
#   VSIX (cursor / vscode / vscodium / windsurf / antigravity) and the
#   ``AutopilotBridge`` class is *intentionally* duplicated across the
#   five plugins. That is the whole point of the per-IDE split — a
#   regression in one IDE pipeline cannot leak into another's runtime.
#   Without this exclude code2llm flagged 10 duplicated classes every
#   cycle and created a "Remove duplicated classes" planfile ticket
#   (STARTER-276) that would only be fixable by re-collapsing the
#   plugins, undoing the whole split. Shared TypeScript that *is* safe
#   to deduplicate already lives in ``plugins/koru-autopilot-shared/``
#   and is copied into each plugin's ``src/_shared/`` at build time;
#   code2llm sees both copies as duplicates too, which is why we exclude
#   the whole ``plugins/`` tree rather than a glob below it. code2llm's
#   ``--exclude`` argument matches by directory name / simple pattern,
#   not full glob, so the literal ``plugins`` is what works.
DEFAULT_EXCLUDES: tuple[str, ...] = (
    "*.md",
    "plugins",
)
DEFAULT_STALE_MINUTES = 60.0
DEFAULT_SOURCE = "koru-project-discovery"


@dataclass
class DiscoveryOutcome:
    """Result of an automatic ``code2llm`` discovery cycle."""

    ran: bool = False
    skipped_reason: str | None = None
    code2llm_path: str | None = None
    code2llm_returncode: int | None = None
    code2llm_duration_s: float | None = None
    artifacts_dir: str | None = None
    applied_titles: list[str] = field(default_factory=list)
    skipped_titles: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ran": self.ran,
            "skipped_reason": self.skipped_reason,
            "code2llm_path": self.code2llm_path,
            "code2llm_returncode": self.code2llm_returncode,
            "code2llm_duration_s": self.code2llm_duration_s,
            "artifacts_dir": self.artifacts_dir,
            "applied": list(self.applied_titles),
            "skipped": list(self.skipped_titles),
            "error": self.error,
        }


def _default_runner(cmd: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(cmd),
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=900,
    )


def _artifacts_fresh(artifacts_dir: Path, *, stale_minutes: float) -> bool:
    analysis = artifacts_dir / "analysis.toon.yaml"
    if not analysis.is_file():
        return False
    age_s = max(0.0, time.time() - analysis.stat().st_mtime)
    return age_s < stale_minutes * 60.0


def _code2llm_executable() -> str | None:
    return shutil.which("code2llm")


def _build_code2llm_cmd(
    binary: str,
    *,
    project: Path,
    output_dir: Path,
    formats: str,
    excludes: Sequence[str],
    apply_planfile: bool,
    planfile_source: str,
    planfile_sprint: str,
    planfile_limit: int | None,
) -> list[str]:
    cmd = [
        binary,
        str(project),
        "-f",
        formats,
        "-o",
        str(output_dir),
        "--no-chunk",
    ]
    for pattern in excludes:
        cmd.extend(["--exclude", pattern])
    if apply_planfile:
        cmd.append("--planfile-apply")
        cmd.extend(["--planfile-source", planfile_source])
        cmd.extend(["--planfile-sprint", planfile_sprint])
        cmd.extend(["--planfile-project", str(project)])
        if planfile_limit is not None and planfile_limit > 0:
            cmd.extend(["--planfile-limit", str(planfile_limit)])
    return cmd


def _file_evidence(project: Path, path: Path) -> dict[str, object]:
    try:
        stat = path.stat()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rel = str(path.relative_to(project))
    except (OSError, ValueError):
        return {}
    return {
        "path": rel,
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": digest,
    }


def _source_evidence_context(project: Path, artifacts_dir: Path, item: dict[str, Any]) -> dict[str, Any]:
    source_files = _string_list(item.get("files"))
    return {
        "evidence": {
            "schema": "koru.ticket_evidence.v1",
            "kind": "code2llm_discovery",
            "artifact": _file_evidence(project, artifacts_dir / "analysis.toon.yaml"),
            "planfile_tickets": _file_evidence(project, artifacts_dir / "planfile-tickets.yaml"),
            "files": [
                evidence
                for rel in source_files
                if (evidence := _file_evidence(project, project / rel))
            ],
            "regenerate_command": " ".join(
                _build_code2llm_cmd(
                    "code2llm",
                    project=project,
                    output_dir=artifacts_dir,
                    formats=DEFAULT_FORMATS,
                    excludes=DEFAULT_EXCLUDES,
                    apply_planfile=True,
                    planfile_source=str(item.get("source") or "koru-project-discovery"),
                    planfile_sprint="current",
                    planfile_limit=20,
                )
            ),
            "staleness_check": (
                "Regenerate artifacts and compare artifact.sha256 / files[].sha256 "
                "before assuming this ticket is still current."
            ),
        }
    }


def _read_planfile_tickets_output(artifacts_dir: Path) -> tuple[list[str], list[str]]:
    """Parse ``planfile-tickets.yaml`` for the applied/skipped lists."""
    path = artifacts_dir / "planfile-tickets.yaml"
    if not path.is_file():
        return [], []
    try:
        import yaml  # local import; yaml is already a runtime dep of koru

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, Exception):  # noqa: BLE001 — best-effort
        return [], []
    if not isinstance(data, dict):
        return [], []
    applied_titles = [str(item) for item in (data.get("applied") or []) if isinstance(item, str)]
    skipped_titles = [str(item) for item in (data.get("skipped") or []) if isinstance(item, str)]
    return applied_titles, skipped_titles


def _read_planfile_ticket_items(artifacts_dir: Path) -> tuple[str, list[dict[str, Any]]]:
    path = artifacts_dir / "planfile-tickets.yaml"
    if not path.is_file():
        return DEFAULT_SOURCE, []
    try:
        import yaml  # local import; yaml is already a runtime dep of koru

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, Exception):  # noqa: BLE001 - best-effort
        return DEFAULT_SOURCE, []
    if not isinstance(data, dict):
        return DEFAULT_SOURCE, []
    source = str(data.get("source") or DEFAULT_SOURCE).strip() or DEFAULT_SOURCE
    raw_tickets = data.get("tickets")
    if not isinstance(raw_tickets, list):
        return source, []
    return source, [item for item in raw_tickets if isinstance(item, dict)]


def _ticket_item_text(item: dict[str, Any]) -> str:
    description = str(item.get("description") or "").strip()
    return description or str(item.get("title") or "code2llm discovery ticket").strip()


def _ticket_item_match_key(item: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    title = str(item.get("title") or "").strip()
    files = tuple(str(v) for v in (item.get("files") or []) if str(v).strip())
    return title, files


def _backfill_existing_dedupe_keys(
    project: Path,
    artifacts_dir: Path,
    *,
    source: str,
    sprint: str,
) -> int:
    try:
        import yaml

        _file_source, items = _read_planfile_ticket_items(artifacts_dir)
        by_key = {_ticket_item_match_key(item): item for item in items}
        if not by_key:
            return 0
        sprint_path = project / ".planfile" / "sprints" / f"{sprint}.yaml"
        data = yaml.safe_load(sprint_path.read_text(encoding="utf-8")) or {}
    except (OSError, Exception):  # noqa: BLE001 - best-effort backfill
        return 0
    sprint_data = data.get("sprint") if isinstance(data, dict) else None
    tickets = sprint_data.get("tickets") if isinstance(sprint_data, dict) else None
    if not isinstance(tickets, dict):
        return 0
    changed = 0
    for ticket in tickets.values():
        if _backfill_ticket_dedupe_key(
            ticket,
            by_key,
            source,
            project=project,
            artifacts_dir=artifacts_dir,
        ):
            changed += 1
    if changed:
        try:
            sprint_path.write_text(
                yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
        except OSError:
            return 0
    return changed


def _backfill_ticket_dedupe_key(
    ticket: Any,
    by_key: dict[tuple[str, tuple[str, ...]], dict[str, Any]],
    source: str,
    *,
    project: Path,
    artifacts_dir: Path,
) -> bool:
    if not isinstance(ticket, dict):
        return False
    ticket_source = ticket.get("source")
    if not _ticket_source_matches(ticket_source, source):
        return False
    context = ticket_source.get("context")
    if isinstance(context, dict) and context.get("dedupe_key") and context.get("evidence"):
        return False
    item = by_key.get(_existing_ticket_match_key(ticket))
    if not item:
        return False
    dedupe_key = str(item.get("dedupe_key") or "").strip()
    if not dedupe_key:
        return False
    ticket_source["context"] = _merged_ticket_source_context(
        context,
        item,
        dedupe_key,
        project=project,
        artifacts_dir=artifacts_dir,
    )
    return True


def _ticket_source_matches(ticket_source: Any, source: str) -> bool:
    return isinstance(ticket_source, dict) and ticket_source.get("tool") == source


def _existing_ticket_match_key(ticket: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    return (
        str(ticket.get("name") or "").strip(),
        tuple(str(v) for v in (ticket.get("files") or []) if str(v).strip()),
    )


def _merged_ticket_source_context(
    context: Any,
    item: dict[str, Any],
    dedupe_key: str,
    *,
    project: Path,
    artifacts_dir: Path,
) -> dict[str, Any]:
    new_context = dict(context) if isinstance(context, dict) else {}
    signal = str(item.get("signal") or "").strip()
    if signal:
        new_context.setdefault("signal", signal)
    new_context["dedupe_key"] = dedupe_key
    new_context.update(_source_evidence_context(project, artifacts_dir, item))
    return new_context


def _apply_planfile_ticket_items(
    project: Path,
    artifacts_dir: Path,
    *,
    source: str,
    sprint: str,
    limit: int | None,
) -> tuple[list[str], list[str]]:
    from koru.tasks import create_nl_task

    _backfill_existing_dedupe_keys(project, artifacts_dir, source=source, sprint=sprint)
    _file_source, items = _read_planfile_ticket_items(artifacts_dir)
    if not items:
        return _read_planfile_tickets_output(artifacts_dir)
    created_titles: list[str] = []
    skipped_titles: list[str] = []
    selected = items[:limit] if limit is not None and limit > 0 else items
    for item in selected:
        scaffold = _ticket_item_scaffold(
            item,
            source,
            project=project,
            artifacts_dir=artifacts_dir,
        )
        title = str(scaffold["title"])
        try:
            created = create_nl_task(
                project,
                _ticket_item_text(item),
                sprint=sprint,
                priority=str(item.get("priority") or "normal"),
                scaffold=scaffold,
            )
        except (OSError, ValueError) as exc:
            skipped_titles.append(f"{title}: {exc}")
            continue
        if getattr(created, "reused", False):
            skipped_titles.append(title)
        else:
            created_titles.append(title)
    return created_titles, skipped_titles


def _ticket_item_scaffold(
    item: dict[str, Any],
    source: str,
    *,
    project: Path | None = None,
    artifacts_dir: Path | None = None,
) -> dict[str, Any]:
    return {
        "title": str(item.get("title") or "code2llm discovery ticket").strip(),
        "labels": _string_list(item.get("labels")),
        "files": _string_list(item.get("files")),
        "source_tool": source,
        "source_context": _ticket_item_source_context(
            item,
            project=project,
            artifacts_dir=artifacts_dir,
        ),
        "executor_kind": "human",
        "executor_mode": "interactive",
    }


def _ticket_item_source_context(
    item: dict[str, Any],
    *,
    project: Path | None = None,
    artifacts_dir: Path | None = None,
) -> dict[str, Any]:
    source_context: dict[str, Any] = {}
    for key in ("signal", "dedupe_key"):
        value = str(item.get(key) or "").strip()
        if value:
            source_context[key] = value
    if project is not None and artifacts_dir is not None:
        source_context.update(_source_evidence_context(project, artifacts_dir, item))
    return source_context


def _string_list(value: Any) -> list[str]:
    return [str(v) for v in (value or []) if str(v).strip()]


def _apply_or_read_planfile_tickets(
    project: Path,
    artifacts_dir: Path,
    *,
    apply_planfile: bool,
    planfile_source: str,
    planfile_sprint: str,
    planfile_limit: int | None,
) -> tuple[list[str], list[str]]:
    if apply_planfile:
        return _apply_planfile_ticket_items(
            project,
            artifacts_dir,
            source=planfile_source,
            sprint=planfile_sprint,
            limit=planfile_limit,
        )
    return _read_planfile_tickets_output(artifacts_dir)


def _handle_fresh_artifacts(
    outcome: DiscoveryOutcome,
    project: Path,
    artifacts_dir: Path,
    *,
    stale_minutes: float,
    apply_planfile: bool,
    planfile_source: str,
    planfile_sprint: str,
    planfile_limit: int | None,
) -> DiscoveryOutcome:
    outcome.skipped_reason = f"artifacts younger than {stale_minutes:.0f}m in {artifacts_dir}"
    applied_titles, skipped_titles = _apply_or_read_planfile_tickets(
        project,
        artifacts_dir,
        apply_planfile=apply_planfile,
        planfile_source=planfile_source,
        planfile_sprint=planfile_sprint,
        planfile_limit=planfile_limit,
    )
    outcome.applied_titles = applied_titles
    outcome.skipped_titles = skipped_titles
    return outcome


def _run_code2llm_command(
    outcome: DiscoveryOutcome,
    cmd: Sequence[str],
    project: Path,
    runner: Runner,
) -> subprocess.CompletedProcess[str] | None:
    start = time.monotonic()
    try:
        result = runner(cmd, project)
    except subprocess.TimeoutExpired as exc:
        outcome.error = f"code2llm timed out after {exc.timeout}s"
        outcome.code2llm_duration_s = time.monotonic() - start
        return None
    except (OSError, ValueError) as exc:
        outcome.error = f"code2llm exec failed: {exc}"
        outcome.code2llm_duration_s = time.monotonic() - start
        return None
    outcome.code2llm_duration_s = time.monotonic() - start
    outcome.code2llm_returncode = result.returncode
    outcome.ran = True
    return result


def _record_code2llm_failure(
    outcome: DiscoveryOutcome,
    result: subprocess.CompletedProcess[str],
) -> DiscoveryOutcome:
    lines = (result.stderr or result.stdout or "").strip().splitlines()
    fallback = f"code2llm rc={result.returncode}"
    outcome.error = (lines[-1:] or [fallback])[0]
    return outcome


def run_code2llm_discovery(
    project: Path,
    *,
    output_subdir: str = DEFAULT_OUTPUT_SUBDIR,
    formats: str = DEFAULT_FORMATS,
    excludes: Sequence[str] = DEFAULT_EXCLUDES,
    apply_planfile: bool = True,
    planfile_source: str = DEFAULT_SOURCE,
    planfile_sprint: str = "current",
    planfile_limit: int | None = 20,
    stale_minutes: float = DEFAULT_STALE_MINUTES,
    force: bool = False,
    runner: Runner = _default_runner,
) -> DiscoveryOutcome:
    """Run ``code2llm`` to refresh project artifacts and apply planfile tickets.

    Returns a structured :class:`DiscoveryOutcome` so callers can branch on the
    result without parsing logs.
    """
    project = project.resolve()
    artifacts_dir = (project / output_subdir).resolve()
    outcome = DiscoveryOutcome(artifacts_dir=str(artifacts_dir))

    binary = _code2llm_executable()
    if binary is None:
        outcome.skipped_reason = "code2llm not on PATH"
        return outcome
    outcome.code2llm_path = binary

    if not force and _artifacts_fresh(artifacts_dir, stale_minutes=stale_minutes):
        return _handle_fresh_artifacts(
            outcome,
            project,
            artifacts_dir,
            stale_minutes=stale_minutes,
            apply_planfile=apply_planfile,
            planfile_source=planfile_source,
            planfile_sprint=planfile_sprint,
            planfile_limit=planfile_limit,
        )

    cmd = _build_code2llm_cmd(
        binary,
        project=project,
        output_dir=artifacts_dir,
        formats=formats,
        excludes=excludes,
        apply_planfile=False,
        planfile_source=planfile_source,
        planfile_sprint=planfile_sprint,
        planfile_limit=planfile_limit,
    )
    result = _run_code2llm_command(outcome, cmd, project, runner)
    if result is None:
        return outcome
    if result.returncode != 0:
        return _record_code2llm_failure(outcome, result)

    applied_titles, skipped_titles = _apply_or_read_planfile_tickets(
        project,
        artifacts_dir,
        apply_planfile=apply_planfile,
        planfile_source=planfile_source,
        planfile_sprint=planfile_sprint,
        planfile_limit=planfile_limit,
    )
    outcome.applied_titles = applied_titles
    outcome.skipped_titles = skipped_titles
    return outcome


def format_discovery_summary(outcome: DiscoveryOutcome) -> str:
    """One-line summary suitable for the koru activity log."""
    if outcome.skipped_reason and not outcome.ran:
        return f"code2llm discovery skipped: {outcome.skipped_reason}"
    if outcome.error:
        return f"code2llm discovery error: {outcome.error}"
    pieces: list[str] = []
    if outcome.code2llm_duration_s is not None:
        pieces.append(f"code2llm {outcome.code2llm_duration_s:.1f}s")
    pieces.append(f"applied={len(outcome.applied_titles)}")
    pieces.append(f"skipped={len(outcome.skipped_titles)}")
    if outcome.artifacts_dir:
        pieces.append(f"artifacts={outcome.artifacts_dir}")
    return "code2llm discovery: " + " ".join(pieces)


__all__ = [
    "DiscoveryOutcome",
    "Runner",
    "format_discovery_summary",
    "run_code2llm_discovery",
]
