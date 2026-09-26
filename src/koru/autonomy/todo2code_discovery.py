"""Automatic code-change ticket generation via ``todo2code`` (``t2c``).

When ``koru auto`` finds an empty planfile queue, after intake scan (and
optionally after ``code2llm``), Koru can run the grounded NL→DSL→plan path:

1. Detect a working ``t2c`` binary on ``PATH`` (or ``KORU_TODO2CODE_BIN``).
2. Run ``t2c pipeline`` in deterministic modes (no LLM required for plans).
3. Load the latest ``.intent/runs/*/code-change-plans.json``.
4. Apply each grounded plan as a planfile ticket through ``create_nl_task``.

Plans come from ``PLANNED_NOT_IMPLEMENTED`` / ``CHANGELOG_WITHOUT_IMPLEMENTATION``
diagnostics that already name concrete ``target.paths``. Runtime does **not**
apply source patches; tickets ask the IDE LLM (or human) to implement the plan.

Module layout: the ``KORU_TODO2CODE_*`` environment/.env knobs, output-dir
containment and discovery limits live in
:mod:`koru.autonomy.todo2code_config`, plan artifact discovery and
plan-field normalization in :mod:`koru.autonomy.todo2code_plans`, and sprint
dedupe plus ticket assembly and planfile filing in
:mod:`koru.autonomy.todo2code_tickets`. This module keeps the pipeline
(:func:`run_todo2code_discovery` → binary/limits/freshness preflight →
``_run_t2c_pipeline`` → ``_consume_plan_set``) and re-exports the moved
names (redundant aliases) so every pre-split
``koru.autonomy.todo2code_discovery`` import — including the private
``_t2c_executable`` patch target and the ``_PRIORITY_MAP`` /
``_plan_dedupe_key`` / ``_config_value`` / ``_out_dir`` names used by
``koru.scan`` and ``koru.autonomy.code_change_autonomy`` — keeps working
unchanged.

Environment knobs (``os.environ`` first, then project ``.env``):

- ``KORU_TODO2CODE_ENABLE``: ``0``/``false`` disables the generator (default on).
- ``KORU_TODO2CODE_BIN``: explicit path to the ``t2c`` executable.
- ``KORU_TODO2CODE_MAX_TICKETS``: cap of tickets created per run (default 10).
- ``KORU_TODO2CODE_STALE_MINUTES``: reuse fresh plans without re-running
  pipeline (default 60).
- ``KORU_TODO2CODE_TIMEOUT_SECONDS``: subprocess timeout (default 900).
- ``KORU_TODO2CODE_OUT``: pipeline output directory under the project
  (default ``.intent``).
- ``KORU_TODO2CODE_LLM_EXECUTOR``: request autonomous LLM execution (default
  off). It is honored only together with ``KORU_TODO2CODE_CONTRACT``.
- ``KORU_TODO2CODE_CONTRACT``: capability contract defined by the target
  project's ``koru.yaml`` and named by autonomous todo2code tickets.
"""

from __future__ import annotations

import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from koru.autonomy.code_change_usefulness import is_useful_plan
from koru.autonomy.todo2code_config import DEFAULT_MAX_TICKETS as DEFAULT_MAX_TICKETS
from koru.autonomy.todo2code_config import DEFAULT_MIN_USEFULNESS as DEFAULT_MIN_USEFULNESS
from koru.autonomy.todo2code_config import DEFAULT_OUT_SUBDIR as DEFAULT_OUT_SUBDIR
from koru.autonomy.todo2code_config import DEFAULT_SOURCE as DEFAULT_SOURCE
from koru.autonomy.todo2code_config import DEFAULT_STALE_MINUTES as DEFAULT_STALE_MINUTES
from koru.autonomy.todo2code_config import DEFAULT_TIMEOUT_SECONDS as DEFAULT_TIMEOUT_SECONDS
from koru.autonomy.todo2code_config import _config_value as _config_value
from koru.autonomy.todo2code_config import _discovery_limits as _discovery_limits
from koru.autonomy.todo2code_config import _env_flag as _env_flag
from koru.autonomy.todo2code_config import _env_float as _env_float
from koru.autonomy.todo2code_config import _env_int as _env_int
from koru.autonomy.todo2code_config import _out_dir as _out_dir
from koru.autonomy.todo2code_config import todo2code_enabled as todo2code_enabled
from koru.autonomy.todo2code_plans import PLANS_FILENAME as PLANS_FILENAME
from koru.autonomy.todo2code_plans import _load_plan_set as _load_plan_set
from koru.autonomy.todo2code_plans import _plan_dedupe_key as _plan_dedupe_key
from koru.autonomy.todo2code_plans import _plan_paths as _plan_paths
from koru.autonomy.todo2code_plans import _plans_fresh as _plans_fresh
from koru.autonomy.todo2code_plans import _slug as _slug
from koru.autonomy.todo2code_plans import _string_list as _string_list
from koru.autonomy.todo2code_plans import _truncate as _truncate
from koru.autonomy.todo2code_plans import find_latest_plans_path as find_latest_plans_path
from koru.autonomy.todo2code_tickets import _PRIORITY_MAP as _PRIORITY_MAP
from koru.autonomy.todo2code_tickets import _ExistingPlanTickets as _ExistingPlanTickets
from koru.autonomy.todo2code_tickets import _PlanDispatch as _PlanDispatch
from koru.autonomy.todo2code_tickets import _PlanIdentity as _PlanIdentity
from koru.autonomy.todo2code_tickets import _RankedPlans as _RankedPlans
from koru.autonomy.todo2code_tickets import _apply_plan_tickets as _apply_plan_tickets
from koru.autonomy.todo2code_tickets import _dispatch_plan_task as _dispatch_plan_task
from koru.autonomy.todo2code_tickets import _enrich_plan_scaffold as _enrich_plan_scaffold
from koru.autonomy.todo2code_tickets import _existing_todo2code_keys as _existing_todo2code_keys
from koru.autonomy.todo2code_tickets import _file_evidence as _file_evidence
from koru.autonomy.todo2code_tickets import _file_plan_ticket as _file_plan_ticket
from koru.autonomy.todo2code_tickets import _plan_identity as _plan_identity
from koru.autonomy.todo2code_tickets import _rank_useful_plans as _rank_useful_plans
from koru.autonomy.todo2code_tickets import _read_sprint_tickets as _read_sprint_tickets
from koru.autonomy.todo2code_tickets import _record_plan_dispatch as _record_plan_dispatch
from koru.autonomy.todo2code_tickets import (
    _remember_todo2code_ticket as _remember_todo2code_ticket,
)
from koru.autonomy.todo2code_tickets import _relative_plans_path as _relative_plans_path
from koru.autonomy.todo2code_tickets import (
    _resolve_plan_priority as _resolve_plan_priority,
)
from koru.autonomy.todo2code_tickets import (
    _ticket_change_lines as _ticket_change_lines,
)
from koru.autonomy.todo2code_tickets import _ticket_plan_lines as _ticket_plan_lines
from koru.autonomy.todo2code_tickets import (
    _ticket_recovery_lines as _ticket_recovery_lines,
)
from koru.autonomy.todo2code_tickets import _ticket_risk_lines as _ticket_risk_lines
from koru.autonomy.todo2code_tickets import _ticket_scaffold as _ticket_scaffold
from koru.autonomy.todo2code_tickets import _ticket_text as _ticket_text
from koru.autonomy.todo2code_tickets import _ticket_title as _ticket_title
from koru.queue.todo2code_support import build_pipeline_cmd as _build_pipeline_cmd
from koru.queue.todo2code_support import t2c_executable as _t2c_executable

Runner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]


@dataclass
class Todo2codeDiscoveryOutcome:
    """Result of an automatic ``todo2code`` discovery cycle."""

    ran: bool = False
    skipped_reason: str | None = None
    t2c_path: str | None = None
    t2c_returncode: int | None = None
    t2c_duration_s: float | None = None
    artifacts_dir: str | None = None
    plans_path: str | None = None
    plans_count: int = 0
    useful_plans_count: int = 0
    filtered_out_count: int = 0
    applied_titles: list[str] = field(default_factory=list)
    skipped_titles: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ran": self.ran,
            "skipped_reason": self.skipped_reason,
            "t2c_path": self.t2c_path,
            "t2c_returncode": self.t2c_returncode,
            "t2c_duration_s": self.t2c_duration_s,
            "artifacts_dir": self.artifacts_dir,
            "plans_path": self.plans_path,
            "plans_count": self.plans_count,
            "useful_plans_count": self.useful_plans_count,
            "filtered_out_count": self.filtered_out_count,
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
        timeout=_env_float("KORU_TODO2CODE_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
    )


def _run_t2c_pipeline(
    outcome: Todo2codeDiscoveryOutcome,
    cmd: Sequence[str],
    project: Path,
    runner: Runner,
) -> subprocess.CompletedProcess[str] | None:
    start = time.monotonic()
    try:
        result = runner(cmd, project)
    except subprocess.TimeoutExpired as exc:
        outcome.error = f"t2c timed out after {exc.timeout}s"
        outcome.t2c_duration_s = time.monotonic() - start
        return None
    except (OSError, ValueError) as exc:
        outcome.error = f"t2c exec failed: {exc}"
        outcome.t2c_duration_s = time.monotonic() - start
        return None
    outcome.t2c_duration_s = time.monotonic() - start
    outcome.t2c_returncode = result.returncode
    outcome.ran = True
    return result


def _consume_plan_set(
    outcome: Todo2codeDiscoveryOutcome,
    project: Path,
    plan_set: dict[str, Any],
    *,
    plans_path: Path,
    apply_planfile: bool,
    source: str,
    limit: int,
    sprint: str,
    min_usefulness: float,
) -> None:
    """Record plan counts and optionally apply useful plans to the sprint."""
    plans = [p for p in (plan_set.get("plans") or []) if isinstance(p, dict)]
    outcome.plans_count = len(plans)
    if apply_planfile:
        applied, skipped, useful, filtered = _apply_plan_tickets(
            project, plan_set, plans_path=plans_path, source=source,
            limit=limit, sprint=sprint, min_usefulness=min_usefulness,
        )
        outcome.applied_titles = applied
        outcome.skipped_titles = skipped
        outcome.useful_plans_count = useful
        outcome.filtered_out_count = filtered
    else:
        useful = [p for p in plans if is_useful_plan(p, project=project, min_score=min_usefulness)]
        outcome.useful_plans_count = len(useful)
        outcome.filtered_out_count = len(plans) - len(useful)


def run_todo2code_discovery(
    project: Path,
    *,
    apply_planfile: bool = True,
    planfile_source: str = DEFAULT_SOURCE,
    planfile_sprint: str = "current",
    planfile_limit: int | None = None,
    stale_minutes: float | None = None,
    force: bool = False,
    runner: Runner = _default_runner,
) -> Todo2codeDiscoveryOutcome:
    """Run ``t2c pipeline`` and turn code-change plans into planfile tickets."""
    project = project.resolve()
    outcome = Todo2codeDiscoveryOutcome()

    if not todo2code_enabled(project):
        outcome.skipped_reason = "disabled via KORU_TODO2CODE_ENABLE"
        return outcome

    try:
        out_dir = _out_dir(project)
    except ValueError as exc:
        outcome.error = str(exc)
        return outcome
    outcome.artifacts_dir = str(out_dir)

    binary = _t2c_executable(project)
    if binary is None:
        outcome.skipped_reason = "t2c not on PATH (set KORU_TODO2CODE_BIN)"
        return outcome
    outcome.t2c_path = binary
    stale, limit, min_usefulness = _discovery_limits(project, stale_minutes, planfile_limit)

    existing_plans = find_latest_plans_path(out_dir)
    if existing_plans is not None and not force and _plans_fresh(existing_plans, stale_minutes=stale):
        outcome.skipped_reason = (
            f"plans younger than {stale:.0f}m at {existing_plans}"
        )
        outcome.plans_path = str(existing_plans)
        plan_set = _load_plan_set(existing_plans)
        if plan_set is None:
            outcome.error = f"unreadable plans artifact: {existing_plans}"
            return outcome
        _consume_plan_set(outcome, project, plan_set, plans_path=existing_plans,
                          apply_planfile=apply_planfile, source=planfile_source,
                          limit=limit, sprint=planfile_sprint, min_usefulness=min_usefulness)
        return outcome

    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = _build_pipeline_cmd(binary, project, out_dir=out_dir)
    result = _run_t2c_pipeline(outcome, cmd, project, runner)
    if result is None:
        return outcome
    if result.returncode != 0:
        lines = (result.stderr or result.stdout or "").strip().splitlines()
        outcome.error = (lines[-1:] or [f"t2c rc={result.returncode}"])[0]
        return outcome

    plans_path = find_latest_plans_path(out_dir)
    if plans_path is None:
        outcome.error = f"t2c produced no {PLANS_FILENAME} under {out_dir}"
        return outcome
    outcome.plans_path = str(plans_path)

    plan_set = _load_plan_set(plans_path)
    if plan_set is None:
        outcome.error = f"unreadable plans artifact: {plans_path}"
        return outcome

    _consume_plan_set(outcome, project, plan_set, plans_path=plans_path,
                      apply_planfile=apply_planfile, source=planfile_source,
                      limit=limit, sprint=planfile_sprint, min_usefulness=min_usefulness)
    return outcome


def format_todo2code_summary(outcome: Todo2codeDiscoveryOutcome) -> str:
    """One-line summary suitable for the koru activity log."""
    if outcome.skipped_reason and not outcome.ran:
        # Fresh-artifact reuse still reports applied counts.
        if (
            outcome.applied_titles
            or outcome.skipped_titles
            or outcome.plans_count
            or outcome.useful_plans_count
        ):
            pieces = [
                f"plans={outcome.plans_count}",
                f"useful={outcome.useful_plans_count}",
                f"filtered={outcome.filtered_out_count}",
                f"applied={len(outcome.applied_titles)}",
                f"skipped={len(outcome.skipped_titles)}",
            ]
            return (
                f"todo2code discovery (fresh artifacts): {outcome.skipped_reason}; "
                + " ".join(pieces)
            )
        return f"todo2code discovery skipped: {outcome.skipped_reason}"
    if outcome.error:
        return f"todo2code discovery error: {outcome.error}"
    pieces: list[str] = []
    if outcome.t2c_duration_s is not None:
        pieces.append(f"t2c {outcome.t2c_duration_s:.1f}s")
    pieces.append(f"plans={outcome.plans_count}")
    pieces.append(f"useful={outcome.useful_plans_count}")
    pieces.append(f"filtered={outcome.filtered_out_count}")
    pieces.append(f"applied={len(outcome.applied_titles)}")
    pieces.append(f"skipped={len(outcome.skipped_titles)}")
    if outcome.plans_path:
        pieces.append(f"artifact={outcome.plans_path}")
    return "todo2code discovery: " + " ".join(pieces)


__all__ = [
    "Todo2codeDiscoveryOutcome",
    "Runner",
    "find_latest_plans_path",
    "format_todo2code_summary",
    "run_todo2code_discovery",
    "todo2code_enabled",
]
