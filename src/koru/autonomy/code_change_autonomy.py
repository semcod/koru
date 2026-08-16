"""Governed code-change loop: archive junk, quarantine patches, prepare tickets.

Designed so ``koru auto`` can prepare the todo2code lane without granting
itself mutation authority:

1. **Hygiene** — close tickets whose paths are non-implementable.
2. **Quarantine ready source patches** — fully diffed ``t2c`` patches are kept
   as evidence and must enter through a Planfile manifest transaction.
3. **ticket2dsl** — refresh work-unit DSL for remaining open tickets.
4. Remaining useful tickets wait for a human unless the target repository
   explicitly names an LLM capability contract.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from koru.autonomy.code_change_usefulness import is_useful_code_change_path
from koru.autonomy.ticket2dsl import run_ticket2dsl
from koru.autonomy.ticket_hygiene import run_ticket_hygiene
from koru.autonomy.todo2code_discovery import (
    _config_value,
    _out_dir,
    find_latest_plans_path,
)

DEFAULT_ACTOR = "koru-autonomy"


@dataclass
class CodeChangeAutonomyOutcome:
    ran: bool = False
    hygiene: dict[str, Any] = field(default_factory=dict)
    applied_patches: list[str] = field(default_factory=list)
    skipped_patches: list[str] = field(default_factory=list)
    ticket2dsl: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ran": self.ran,
            "hygiene": dict(self.hygiene),
            "applied_patches": list(self.applied_patches),
            "skipped_patches": list(self.skipped_patches),
            "ticket2dsl": dict(self.ticket2dsl),
            "error": self.error,
        }


def autonomy_enabled(project: Path | None = None) -> bool:
    raw = (os.environ.get("KORU_CODE_CHANGE_AUTONOMY") or "").strip().lower()
    if not raw and project is not None:
        try:
            text = (project / ".env").read_text(encoding="utf-8")
        except OSError:
            text = ""
        import re

        match = re.search(r"^\s*KORU_CODE_CHANGE_AUTONOMY\s*=\s*(.+?)\s*$", text, re.M)
        raw = (match.group(1).strip().strip("'\"") if match else "").lower()
    if not raw:
        return True
    return raw in {"1", "true", "yes", "on"}


def _find_source_patches(project: Path) -> Path | None:
    try:
        output = _out_dir(project.resolve())
    except ValueError:
        return None
    runs = output / "runs"
    if not runs.is_dir():
        # also check plans parent for source-patches next to plans
        plans = find_latest_plans_path(output)
        if plans is not None:
            candidate = plans.parent / "code-change-source-patches.json"
            if candidate.is_file():
                return candidate
        return None
    candidates = sorted(
        runs.glob("*/code-change-source-patches.json"),
        key=lambda p: p.stat().st_mtime if p.is_file() else 0.0,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _patch_is_fully_diffed(patch: dict[str, Any], *, project: Path) -> bool:
    edits = patch.get("edits") if isinstance(patch.get("edits"), list) else []
    if not edits:
        return False
    for edit in edits:
        if not isinstance(edit, dict):
            return False
        path = str(edit.get("path") or "").strip()
        if not path or not is_useful_code_change_path(path, project=project):
            return False
        if not isinstance(edit.get("unifiedDiff"), str) or not str(edit.get("unifiedDiff")).strip():
            return False
    return True


def apply_ready_source_patches(
    project: Path,
    *,
    actor: str = DEFAULT_ACTOR,
    limit: int = 20,
) -> tuple[list[str], list[str]]:
    """Refuse direct application; source patches require a queue transaction."""
    patches_path = _find_source_patches(project)
    if patches_path is None:
        return [], ["no code-change-source-patches.json found"]

    try:
        data = json.loads(patches_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [], [f"unreadable patches: {exc}"]

    patches = [p for p in (data.get("patches") or []) if isinstance(p, dict)]
    applied: list[str] = []
    skipped: list[str] = []
    for patch in patches:
        if len(skipped) >= limit:
            break
        patch_id = str(patch.get("id") or "patch")
        if not _patch_is_fully_diffed(patch, project=project):
            skipped.append(f"{patch_id}: instruction-only (no unifiedDiff)")
            continue
        skipped.append(
            f"{patch_id}: direct apply disabled; submit through the "
            "Planfile manifest transaction after approval"
        )
    return applied, skipped


def _promote_todo2code_tickets_to_llm(project: Path, *, sprint: str = "current") -> int:
    """Promote tickets only under the target's explicit executor flag and contract."""
    enabled = _config_value("KORU_TODO2CODE_LLM_EXECUTOR", project).lower()
    contract = _config_value("KORU_TODO2CODE_CONTRACT", project)
    if enabled not in {"1", "true", "yes", "on"} or not contract:
        return 0
    try:
        import yaml
    except Exception:  # noqa: BLE001
        return 0
    path = project / ".planfile" / "sprints" / f"{sprint}.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, Exception):  # noqa: BLE001
        return 0
    sprint_data = data.get("sprint") if isinstance(data, dict) else None
    tickets = sprint_data.get("tickets") if isinstance(sprint_data, dict) else None
    if not isinstance(tickets, dict):
        return 0

    changed = 0
    for ticket in tickets.values():
        if not isinstance(ticket, dict):
            continue
        status = str(ticket.get("status") or "").strip().lower()
        if status in {"done", "closed", "cancelled", "canceled", "failed"}:
            continue
        name = str(ticket.get("name") or "")
        source = ticket.get("source") if isinstance(ticket.get("source"), dict) else {}
        tool = str(source.get("tool") or "")
        if not (name.startswith("[todo2code]") or "todo2code" in tool):
            continue
        executor = ticket.get("executor") if isinstance(ticket.get("executor"), dict) else {}
        kind = str(executor.get("kind") or "human").lower()
        if kind == "llm" and str(executor.get("mode") or "").lower() == "automatic":
            continue
        files = [str(f) for f in (ticket.get("files") or []) if str(f).strip()]
        if not files or not all(
            is_useful_code_change_path(path, project=project) for path in files
        ):
            continue
        ticket["executor"] = {"kind": "llm", "mode": "automatic"}
        inputs = dict(ticket.get("inputs") or {})
        inputs.pop("llm_model", None)
        inputs.pop("llm_max_tokens", None)
        inputs.setdefault("include_project_context", True)
        inputs.setdefault("context_files", files)
        inputs["patch_mode"] = True
        inputs.setdefault("max_patch_attempts", 3)
        inputs.setdefault("risk_class", "R1")
        inputs["contract"] = contract
        ticket["inputs"] = inputs
        execution = dict(ticket.get("execution") or {})
        execution.setdefault("state", "ready")
        execution["max_attempts"] = max(3, int(execution.get("max_attempts") or 1))
        ticket["execution"] = execution
        labels = list(ticket.get("labels") or [])
        if "autonomous" not in labels:
            labels.append("autonomous")
        ticket["labels"] = labels
        changed += 1
    if changed:
        try:
            path.write_text(
                yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
        except OSError:
            return 0
    return changed


def run_code_change_autonomy(
    project: Path,
    *,
    sprint: str = "current",
    apply_patches: bool = True,
    hygiene: bool = True,
    ticket2dsl: bool = True,
    promote_llm: bool = True,
    actor: str = DEFAULT_ACTOR,
) -> CodeChangeAutonomyOutcome:
    project = project.resolve()
    outcome = CodeChangeAutonomyOutcome()

    if not autonomy_enabled(project):
        outcome.error = None
        outcome.ran = False
        return outcome

    outcome.ran = True

    if hygiene:
        hy = run_ticket_hygiene(project, sprint=sprint, actor=f"{actor}-hygiene")
        outcome.hygiene = hy.to_dict()

    if promote_llm:
        promoted = _promote_todo2code_tickets_to_llm(project, sprint=sprint)
        outcome.hygiene = dict(outcome.hygiene or {})
        outcome.hygiene["promoted_to_llm"] = promoted

    if apply_patches:
        applied, skipped = apply_ready_source_patches(project, actor=actor)
        outcome.applied_patches = applied
        outcome.skipped_patches = skipped

    if ticket2dsl:
        t2d = run_ticket2dsl(project, sprint=sprint)
        outcome.ticket2dsl = t2d.to_dict()

    return outcome


def format_autonomy_summary(outcome: CodeChangeAutonomyOutcome) -> str:
    if not outcome.ran:
        return "code-change autonomy skipped (disabled)"
    archived = len(outcome.hygiene.get("archived") or []) if outcome.hygiene else 0
    kept = len(outcome.hygiene.get("kept") or []) if outcome.hygiene else 0
    promoted = int((outcome.hygiene or {}).get("promoted_to_llm") or 0)
    units = int((outcome.ticket2dsl or {}).get("units_count") or 0)
    pieces = [
        f"hygiene archived={archived} kept={kept} promoted_llm={promoted}",
        f"applied_patches={len(outcome.applied_patches)}",
        f"skipped_patches={len(outcome.skipped_patches)}",
        f"ticket2dsl_units={units}",
    ]
    if outcome.error:
        pieces.append(f"error={outcome.error}")
    return "code-change autonomy: " + "; ".join(pieces)


__all__ = [
    "CodeChangeAutonomyOutcome",
    "apply_ready_source_patches",
    "autonomy_enabled",
    "format_autonomy_summary",
    "run_code_change_autonomy",
]
