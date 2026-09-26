"""Sprint dedupe, ticket assembly and planfile filing for ``todo2code`` plans.

Turns useful grounded ``t2c`` plans into planfile tickets: reads the dedupe
identities already present in the target sprint, ranks plans by usefulness,
renders the ticket text and scaffold, and files each plan via
``create_nl_task`` under the resolved priority and ticket cap.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, NamedTuple

from koru.autonomy.code_change_usefulness import (
    is_useful_plan,
    plan_usefulness_score,
)
from koru.autonomy.todo2code_config import (
    DEFAULT_MIN_USEFULNESS,
    DEFAULT_SOURCE,
    _config_value,
    _env_flag,
    _out_dir,
)
from koru.autonomy.todo2code_plans import (
    _plan_dedupe_key,
    _plan_paths,
    _string_list,
    _truncate,
)

# t2c P0..P3 -> planfile priority accepted by create_nl_task.
_PRIORITY_MAP = {
    "P0": "high",
    "P1": "high",
    "P2": "normal",
    "P3": "low",
    "high": "high",
    "normal": "normal",
    "low": "low",
}


def _read_sprint_tickets(project: Path, sprint: str) -> dict[str, Any]:
    try:
        import yaml

        sprint_path = project / ".planfile" / "sprints" / f"{sprint}.yaml"
        data = yaml.safe_load(sprint_path.read_text(encoding="utf-8")) or {}
    except (OSError, Exception):  # noqa: BLE001 - best-effort duplicate guard
        return {}
    sprint_data = data.get("sprint") if isinstance(data, dict) else None
    tickets = sprint_data.get("tickets") if isinstance(sprint_data, dict) else None
    if not isinstance(tickets, dict):
        return {}
    return tickets


def _remember_todo2code_ticket(
    ticket: dict[str, Any],
    keys: set[str],
    title_files: set[tuple[str, tuple[str, ...]]],
) -> None:
    name = str(ticket.get("name") or "").strip()
    files = tuple(str(v) for v in (ticket.get("files") or []) if str(v).strip())
    if name.startswith("[todo2code]"):
        title_files.add((name, files))
    source = ticket.get("source")
    context = source.get("context") if isinstance(source, dict) else None
    if not isinstance(context, dict):
        return
    key = str(context.get("dedupe_key") or "").strip()
    if key.startswith("todo2code:"):
        keys.add(key)
    # Also remember title/files from source-tagged tickets without prefix.
    tool = str(source.get("tool") or "") if isinstance(source, dict) else ""
    if tool == DEFAULT_SOURCE and name:
        title_files.add((name, files))


class _ExistingPlanTickets(NamedTuple):
    """Dedupe identities of plan tickets already present in a sprint."""

    keys: set[str]
    title_files: set[tuple[str, tuple[str, ...]]]


def _existing_todo2code_keys(
    project: Path,
    *,
    sprint: str = "current",
) -> _ExistingPlanTickets:
    """Return plan dedupe keys and (title, files) pairs already in the sprint.

    Plan ids are content-bound and change when the intent graph fingerprint
    shifts, so title+files guards against re-filing the same work from a
    fresh pipeline run.
    """
    tickets = _read_sprint_tickets(project, sprint)
    keys: set[str] = set()
    title_files: set[tuple[str, tuple[str, ...]]] = set()
    for ticket in tickets.values():
        if isinstance(ticket, dict):
            _remember_todo2code_ticket(ticket, keys, title_files)
    return _ExistingPlanTickets(keys, title_files)


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


def _ticket_title(plan: dict[str, Any]) -> str:
    raw = str(plan.get("title") or "todo2code code-change plan").strip()
    return _truncate(f"[todo2code] {raw}", 160)


def _ticket_plan_lines(plan: dict[str, Any], *, plans_rel: str) -> list[str]:
    lines: list[str] = []
    plan_id = str(plan.get("id") or "").strip()
    plan_hash = str(plan.get("planHash") or "").strip()
    if plan_id or plan_hash:
        lines.append("")
        lines.append(f"Plan id: {plan_id or 'n/a'}")
        if plan_hash:
            lines.append(f"Plan hash: {plan_hash}")
        lines.append(f"Source artifact: {plans_rel}")

    paths = _plan_paths(plan)
    if paths:
        lines.append("")
        lines.append("Target paths:")
        lines.extend(f"- {path}" for path in paths)

    return lines


def _ticket_change_lines(plan: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    changes = plan.get("changes") if isinstance(plan.get("changes"), list) else []
    change_lines: list[str] = []
    for change in changes:
        if not isinstance(change, dict):
            continue
        path = str(change.get("path") or "").strip()
        action = str(change.get("action") or "modify").strip()
        rationale = str(change.get("rationale") or "").strip()
        symbols = _string_list(change.get("symbols"))
        piece = f"- {action} `{path}`"
        if symbols:
            piece += f" ({', '.join(symbols)})"
        if rationale:
            piece += f": {rationale}"
        change_lines.append(piece)
    if change_lines:
        lines.append("")
        lines.append("Proposed changes:")
        lines.extend(change_lines)

    return lines


def _ticket_risk_lines(plan: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    risk = plan.get("risk") if isinstance(plan.get("risk"), dict) else {}
    risk_level = str(risk.get("level") or "").strip()
    risk_reasons = _string_list(risk.get("reasons"))
    if risk_level or risk_reasons:
        lines.append("")
        lines.append(f"Risk: {risk_level or 'unknown'}")
        lines.extend(f"- {reason}" for reason in risk_reasons)

    return lines


def _ticket_recovery_lines(plan: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    rollback = str(plan.get("rollback") or "").strip()
    if rollback:
        lines.append("")
        lines.append(f"Rollback: {rollback}")

    evidence = plan.get("evidence") if isinstance(plan.get("evidence"), dict) else {}
    diagnostic_ids = _string_list(evidence.get("diagnosticIds"))
    if diagnostic_ids:
        lines.append("")
        lines.append("Diagnostics:")
        lines.extend(f"- {diag}" for diag in diagnostic_ids)

    return lines


def _ticket_text(plan: dict[str, Any], *, plans_rel: str) -> str:
    lines: list[str] = []
    description = str(plan.get("description") or "").strip()
    title = str(plan.get("title") or "").strip()
    lines.append(description or title or "Implement grounded todo2code code-change plan.")

    lines.extend(_ticket_plan_lines(plan, plans_rel=plans_rel))
    lines.extend(_ticket_change_lines(plan))

    criteria = _string_list(plan.get("acceptanceCriteria"))
    if criteria:
        lines.append("")
        lines.append("Acceptance criteria:")
        lines.extend(f"- {item}" for item in criteria)

    lines.extend(_ticket_risk_lines(plan))
    lines.extend(_ticket_recovery_lines(plan))

    lines.append("")
    lines.append(
        "Implement only the declared target paths, then re-run "
        "`t2c evaluate-code-change` / pipeline before marking the ticket done."
    )
    return "\n".join(lines)


def _ticket_scaffold(
    plan: dict[str, Any],
    *,
    project: Path,
    plans_path: Path,
    source: str,
) -> dict[str, Any]:
    paths = _plan_paths(plan)
    evidence = plan.get("evidence") if isinstance(plan.get("evidence"), dict) else {}
    risk = plan.get("risk") if isinstance(plan.get("risk"), dict) else {}
    # A model may execute only inside an explicit project-owned capability
    # contract. The default remains human review so discovery cannot grant its
    # own authority merely by creating a ticket.
    contract = _config_value("KORU_TODO2CODE_CONTRACT", project)
    use_llm = _env_flag("KORU_TODO2CODE_LLM_EXECUTOR", False, project) and bool(contract)
    inputs: dict[str, Any] = {
        # Preserved for older Planfile readers; hydration and ticket request
        # translation remove this metadata before the Cursor SDK call.
        "llm_max_tokens": 4000,
        "llm_timeout_seconds": 300,
        "include_project_context": True,
        "context_files": paths,
        "expect_files_changed": True,
        "patch_mode": True,
        "promotion_mode": "branch",
        "worktree": True,
        "max_patch_attempts": 3,
        "risk_class": "R1",
    }
    if contract:
        inputs["contract"] = contract
    return {
        "title": _ticket_title(plan),
        "labels": ["todo2code", "code-change", "discovery", "autonomous"],
        "files": paths,
        "source_tool": source,
        "source_context": {
            "signal": "todo2code_code_change_plan",
            "dedupe_key": _plan_dedupe_key(plan),
            "plan_id": str(plan.get("id") or "").strip() or None,
            "plan_hash": str(plan.get("planHash") or "").strip() or None,
            "priority": str(plan.get("priority") or "").strip() or None,
            "risk_level": str(risk.get("level") or "").strip() or None,
            "diagnostic_ids": _string_list(evidence.get("diagnosticIds")),
            "record_ids": _string_list(evidence.get("recordIds")),
            "graph_fingerprint": str(evidence.get("graphFingerprint") or "").strip() or None,
            "evidence": {
                "schema": "koru.ticket_evidence.v1",
                "kind": "todo2code_discovery",
                "artifact": _file_evidence(project, plans_path),
                "files": [
                    item
                    for path in paths
                    if (item := _file_evidence(project, project / path))
                ],
                "regenerate_command": (
                    "t2c pipeline . --nl-mode deterministic "
                    f"--markdown-mode deterministic --no-docs-llm --no-summary-llm "
                    "--communication-mode deterministic --project-dir project "
                    f"--out {_out_dir(project).relative_to(project)}"
                ),
                "staleness_check": (
                    "Regenerate code-change-plans.json and compare planHash / "
                    "artifact.sha256 before assuming this ticket is still current."
                ),
            },
        },
        "executor_kind": "llm" if use_llm else "human",
        "executor_mode": "automatic" if use_llm else "interactive",
        "max_attempts": 3 if use_llm else 1,
        "inputs": inputs,
        "prompt_suffix": (
            "Autonomous code-change ticket. Implement only the declared paths. "
            "When patch_mode is on, emit a single unified diff (no prose) so Koru "
            "can apply it without a human. After verify succeeds the queue marks "
            "the ticket done."
        ),
    }


class _RankedPlans(NamedTuple):
    """Usefulness ranking of one plan set."""

    useful: list[dict[str, Any]]
    filtered_out: int


def _rank_useful_plans(
    project: Path, plan_set: dict[str, Any], min_usefulness: float,
) -> _RankedPlans:
    raw_plans = [p for p in (plan_set.get("plans") or []) if isinstance(p, dict)]
    useful: list[dict[str, Any]] = []
    filtered_out = 0
    for plan in raw_plans:
        if not _plan_paths(plan) or not is_useful_plan(
            plan, project=project, min_score=min_usefulness
        ):
            filtered_out += 1
            continue
        useful.append(plan)
    # Highest usefulness first so the ticket cap prefers real code work.
    useful.sort(key=lambda p: plan_usefulness_score(p, project=project), reverse=True)

    return _RankedPlans(useful, filtered_out)


def _relative_plans_path(project: Path, plans_path: Path) -> str:
    try:
        return str(plans_path.relative_to(project))
    except ValueError:
        return str(plans_path)


class _PlanIdentity(NamedTuple):
    """Scaffold-derived identity of the ticket one plan would produce."""

    title: str
    key: str
    title_key: tuple[str, tuple[str, ...]]


def _plan_identity(scaffold: dict[str, Any]) -> _PlanIdentity:
    title = str(scaffold["title"])
    key = str(scaffold["source_context"]["dedupe_key"])
    files = tuple(str(v) for v in (scaffold.get("files") or []) if str(v).strip())
    return _PlanIdentity(title, key, (title, files))


def _resolve_plan_priority(plan: dict[str, Any]) -> str:
    raw = str(plan.get("priority") or "")
    priority = _PRIORITY_MAP.get(raw.upper(), "normal")
    if priority not in {"high", "normal", "low"}:
        priority = _PRIORITY_MAP.get(raw.lower(), "normal")
    return priority


def _enrich_plan_scaffold(scaffold: dict[str, Any], plan: dict[str, Any], project: Path) -> None:
    score = plan_usefulness_score(plan, project=project)
    scaffold["source_context"]["usefulness_score"] = round(score, 2)
    scaffold["labels"] = list(
        dict.fromkeys([*scaffold.get("labels", []), "useful-code-change"])
    )


class _PlanDispatch(NamedTuple):
    """Outcome of creating one plan's task via create_nl_task."""

    created: bool
    error: str | None


def _dispatch_plan_task(
    project: Path,
    plan: dict[str, Any],
    scaffold: dict[str, Any],
    plans_rel: str,
    sprint: str,
) -> _PlanDispatch:
    """Create task via create_nl_task; reports the creation outcome."""
    from koru.tasks import create_nl_task

    priority = _resolve_plan_priority(plan)
    _enrich_plan_scaffold(scaffold, plan, project)
    try:
        created = create_nl_task(
            project,
            _ticket_text(plan, plans_rel=plans_rel),
            sprint=sprint,
            priority=priority,
            scaffold=scaffold,
        )
    except (OSError, ValueError) as exc:
        return _PlanDispatch(False, str(exc))
    if getattr(created, "reused", False):
        return _PlanDispatch(False, None)
    return _PlanDispatch(True, None)


def _file_plan_ticket(
    project: Path,
    plan: dict[str, Any],
    created_titles: list[str],
    skipped_titles: list[str],
    *,
    existing: _ExistingPlanTickets,
    plans_path: Path,
    source: str,
    plans_rel: str,
    sprint: str,
) -> None:
    """File one useful plan as a sprint ticket, or record why it was skipped."""
    scaffold = _ticket_scaffold(plan, project=project, plans_path=plans_path, source=source)
    identity = _plan_identity(scaffold)
    if identity.key in existing.keys or identity.title_key in existing.title_files:
        skipped_titles.append(identity.title)
        return
    dispatched = _dispatch_plan_task(project, plan, scaffold, plans_rel, sprint)
    _record_plan_dispatch(dispatched, identity, created_titles, skipped_titles, existing)


def _record_plan_dispatch(
    dispatched: _PlanDispatch,
    identity: _PlanIdentity,
    created_titles: list[str],
    skipped_titles: list[str],
    existing: _ExistingPlanTickets,
) -> None:
    """Record a dispatched plan ticket as created, or as skipped with its error."""
    if not dispatched.created:
        skipped_titles.append(f"{identity.title}: {dispatched.error}" if dispatched.error else identity.title)
        return
    created_titles.append(identity.title)
    existing.keys.add(identity.key)
    existing.title_files.add(identity.title_key)


def _apply_plan_tickets(
    project: Path,
    plan_set: dict[str, Any],
    *,
    plans_path: Path,
    source: str,
    limit: int,
    sprint: str = "current",
    min_usefulness: float = DEFAULT_MIN_USEFULNESS,
) -> tuple[list[str], list[str], int, int]:
    """Return (created, skipped, useful_count, filtered_out_count)."""
    ranked = _rank_useful_plans(project, plan_set, min_usefulness)
    existing = _existing_todo2code_keys(project, sprint=sprint)
    plans_rel = _relative_plans_path(project, plans_path)
    created_titles: list[str] = []
    skipped_titles: list[str] = []

    for plan in ranked.useful:
        if len(created_titles) >= limit:
            break
        _file_plan_ticket(
            project,
            plan,
            created_titles,
            skipped_titles,
            existing=existing,
            plans_path=plans_path,
            source=source,
            plans_rel=plans_rel,
            sprint=sprint,
        )
    return created_titles, skipped_titles, len(ranked.useful), ranked.filtered_out
