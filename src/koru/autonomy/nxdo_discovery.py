"""Idle-time ticket generation via ``nxdo`` (LLM next-task planner).

When ``koru auto`` finds the queue idle and neither ``koru scan`` nor the
``code2llm`` discovery produced runnable tickets, ask ``nxdo`` to plan the
next engineering tasks and file them as planfile tickets — instead of
letting the loop wait. ``nxdo`` can also plan for sibling repos
(``KORU_NXDO_REPOS``), so the loop generates cross-repo work when the
current project has nothing actionable.

Module layout: the ``KORU_NXDO_*`` environment/.env knobs, binary
resolution and target-repo selection live in
:mod:`koru.autonomy.nxdo_config`, the per-repo cooldown stamps in
:mod:`koru.autonomy.nxdo_cooldown`, and TaskPlan parsing plus planfile
ticket filing in :mod:`koru.autonomy.nxdo_tickets`. This module keeps the
pipeline (:func:`run_nxdo_discovery` → ``_preflight`` → ``_execute`` →
``_record_attempt`` → ``_interpret_plan``) and re-exports the moved names
(redundant aliases) so every pre-split ``koru.autonomy.nxdo_discovery``
import — including the private ``_nxdo_executable`` patch target and
``_dedupe_key`` used by tests — keeps working unchanged.
"""

from __future__ import annotations

import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple

from koru.autonomy.nxdo_config import DEFAULT_TIMEOUT_SECONDS as DEFAULT_TIMEOUT_SECONDS
from koru.autonomy.nxdo_config import Runner as Runner
from koru.autonomy.nxdo_config import _api_key_available as _api_key_available
from koru.autonomy.nxdo_config import _config_value as _config_value
from koru.autonomy.nxdo_config import _default_runner as _default_runner
from koru.autonomy.nxdo_config import _dotenv_value as _dotenv_value
from koru.autonomy.nxdo_config import _env_flag as _env_flag
from koru.autonomy.nxdo_config import _env_float as _env_float
from koru.autonomy.nxdo_config import _env_int as _env_int
from koru.autonomy.nxdo_config import _nxdo_executable as _nxdo_executable
from koru.autonomy.nxdo_config import nxdo_enabled as nxdo_enabled
from koru.autonomy.nxdo_config import nxdo_target_repos as nxdo_target_repos
from koru.autonomy.nxdo_cooldown import DEFAULT_COOLDOWN_SECONDS as DEFAULT_COOLDOWN_SECONDS
from koru.autonomy.nxdo_cooldown import STAMP_RELPATH as STAMP_RELPATH
from koru.autonomy.nxdo_cooldown import _CooldownSelection as _CooldownSelection
from koru.autonomy.nxdo_cooldown import _load_stamps as _load_stamps
from koru.autonomy.nxdo_cooldown import _save_stamps as _save_stamps
from koru.autonomy.nxdo_cooldown import _select_target_repo as _select_target_repo
from koru.autonomy.nxdo_cooldown import _stamp_path as _stamp_path
from koru.autonomy.nxdo_tickets import _PRIORITY_MAP as _PRIORITY_MAP
from koru.autonomy.nxdo_tickets import DEFAULT_MAX_TICKETS as DEFAULT_MAX_TICKETS
from koru.autonomy.nxdo_tickets import DEFAULT_SOURCE as DEFAULT_SOURCE
from koru.autonomy.nxdo_tickets import _apply_plan_tickets as _apply_plan_tickets
from koru.autonomy.nxdo_tickets import _dedupe_key as _dedupe_key
from koru.autonomy.nxdo_tickets import (
    _existing_nxdo_dedupe_keys as _existing_nxdo_dedupe_keys,
)
from koru.autonomy.nxdo_tickets import _plan_from_output as _plan_from_output
from koru.autonomy.nxdo_tickets import _PlanFiling as _PlanFiling
from koru.autonomy.nxdo_tickets import _slug as _slug
from koru.autonomy.nxdo_tickets import _ticket_scaffold as _ticket_scaffold
from koru.autonomy.nxdo_tickets import _ticket_text as _ticket_text


class _Preflight(NamedTuple):
    """What :func:`_preflight` resolved: a skip reason or the run inputs.

    ``binary``/``repo``/``started`` are only meaningful when ``reason`` is
    ``None``; the cooldown stamp must reuse the ``started`` timestamp that
    gated repo selection.
    """

    reason: str | None
    binary: str | None
    repo: Path | None
    started: float


@dataclass
class NxdoDiscoveryOutcome:
    """Result of an automatic ``nxdo`` planning cycle."""

    ran: bool = False
    skipped_reason: str | None = None
    nxdo_path: str | None = None
    target_repo: str | None = None
    nxdo_returncode: int | None = None
    nxdo_duration_s: float | None = None
    applied_titles: list[str] = field(default_factory=list)
    skipped_titles: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ran": self.ran,
            "skipped_reason": self.skipped_reason,
            "nxdo_path": self.nxdo_path,
            "target_repo": self.target_repo,
            "nxdo_returncode": self.nxdo_returncode,
            "nxdo_duration_s": self.nxdo_duration_s,
            "applied": list(self.applied_titles),
            "skipped": list(self.skipped_titles),
            "error": self.error,
        }


def _preflight(
    project: Path,
    *,
    now: Callable[[], float],
    outcome: NxdoDiscoveryOutcome,
) -> _Preflight:
    """Run the guard checks; record the resolved binary/repo on ``outcome``.

    Returns the skip ``reason``, or the inputs the run needs (binary, target
    repo and the ``started`` timestamp used for cooldown stamping).
    """
    if not nxdo_enabled(project):
        return _Preflight("disabled via KORU_NXDO_ENABLE", None, None, 0.0)
    binary = _nxdo_executable(project)
    if binary is None:
        return _Preflight("nxdo not on PATH (set KORU_NXDO_BIN)", None, None, 0.0)
    outcome.nxdo_path = binary
    if not _api_key_available(project):
        return _Preflight("no OPENROUTER_API_KEY/OPENAI_API_KEY (env or project .env)", None, None, 0.0)
    started = now()
    selection = _select_target_repo(project, now=started)
    if selection.repo is None:
        return _Preflight(
            f"cooldown active for all repos (~{selection.remaining:.0f}s remaining)",
            None,
            None,
            0.0,
        )
    outcome.target_repo = str(selection.repo)
    return _Preflight(None, binary, selection.repo, started)


def _nxdo_command(binary: str, repo: Path, project: Path) -> list[str]:
    """``nxdo plan`` argv including the optional model/extra-context knobs."""
    cmd = [binary, "plan", str(repo), "--json"]
    model = _config_value("KORU_NXDO_MODEL", project)
    if model:
        cmd.extend(["--model", model])
    extra_context = _config_value("KORU_NXDO_EXTRA_CONTEXT", project)
    if extra_context:
        cmd.extend(["--extra-context", extra_context])
    return cmd


def _execute(
    pre: _Preflight,
    project: Path,
    *,
    runner: Runner,
    outcome: NxdoDiscoveryOutcome,
) -> subprocess.CompletedProcess[str] | None:
    """Run ``nxdo plan`` and time it; record duration (and exec errors).

    Returns the completed process, or ``None`` when the subprocess could not
    run at all (timeout or exec failure) — those paths must not stamp the
    cooldown, so the caller stops before :func:`_record_attempt`.
    """
    cmd = _nxdo_command(pre.binary, pre.repo, project)
    start = time.monotonic()
    try:
        result = runner(cmd, project)
    except subprocess.TimeoutExpired as exc:
        outcome.error = f"nxdo timed out after {exc.timeout}s"
    except (OSError, ValueError) as exc:
        outcome.error = f"nxdo exec failed: {exc}"
    finally:
        outcome.nxdo_duration_s = time.monotonic() - start
    if outcome.error is not None:
        return None
    return result


def _record_attempt(
    project: Path,
    repo: Path,
    started: float,
    result: subprocess.CompletedProcess[str],
    *,
    outcome: NxdoDiscoveryOutcome,
) -> None:
    """Record the run on ``outcome`` and stamp the per-repo cooldown.

    The attempt is stamped even on failure: a failing repo must not burn an
    LLM call every idle cycle.
    """
    outcome.nxdo_returncode = result.returncode
    outcome.ran = True
    stamps = _load_stamps(project)
    stamps[str(repo)] = started
    _save_stamps(project, stamps)


def _failure_message(result: subprocess.CompletedProcess[str]) -> str:
    """Last stderr/stdout line of a failed run, or an rc fallback."""
    lines = (result.stderr or result.stdout or "").strip().splitlines()
    return (lines[-1:] or [f"nxdo rc={result.returncode}"])[0]


def _interpret_plan(
    project: Path,
    repo: Path,
    result: subprocess.CompletedProcess[str],
    *,
    outcome: NxdoDiscoveryOutcome,
) -> None:
    """Turn a completed ``nxdo`` run into error or ticket fields."""
    if result.returncode != 0:
        outcome.error = _failure_message(result)
        return
    plan = _plan_from_output(result.stdout)
    if plan is None:
        outcome.error = "nxdo produced no parseable TaskPlan JSON"
        return
    filed = _apply_plan_tickets(
        project,
        repo,
        plan,
        limit=max(1, _env_int("KORU_NXDO_MAX_TICKETS", DEFAULT_MAX_TICKETS, project)),
    )
    outcome.applied_titles = filed.applied
    outcome.skipped_titles = filed.skipped


def run_nxdo_discovery(
    project: Path,
    *,
    runner: Runner = _default_runner,
    now: Callable[[], float] = time.time,
) -> NxdoDiscoveryOutcome:
    """Ask ``nxdo`` for next tasks and file them as planfile tickets.

    Returns a structured :class:`NxdoDiscoveryOutcome` so callers can branch
    on the result without parsing logs.
    """
    project = project.resolve()
    outcome = NxdoDiscoveryOutcome()

    pre = _preflight(project, now=now, outcome=outcome)
    if pre.reason is not None:
        outcome.skipped_reason = pre.reason
        return outcome

    result = _execute(pre, project, runner=runner, outcome=outcome)
    if result is None:
        return outcome

    _record_attempt(project, pre.repo, pre.started, result, outcome=outcome)
    _interpret_plan(project, pre.repo, result, outcome=outcome)
    return outcome


def format_nxdo_summary(outcome: NxdoDiscoveryOutcome) -> str:
    """One-line summary suitable for the koru activity log."""
    if outcome.skipped_reason and not outcome.ran:
        return f"nxdo discovery skipped: {outcome.skipped_reason}"
    if outcome.error:
        return f"nxdo discovery error: {outcome.error}"
    pieces: list[str] = []
    if outcome.nxdo_duration_s is not None:
        pieces.append(f"nxdo {outcome.nxdo_duration_s:.1f}s")
    if outcome.target_repo:
        pieces.append(f"repo={outcome.target_repo}")
    pieces.append(f"applied={len(outcome.applied_titles)}")
    pieces.append(f"skipped={len(outcome.skipped_titles)}")
    return "nxdo discovery: " + " ".join(pieces)


__all__ = [
    "NxdoDiscoveryOutcome",
    "Runner",
    "format_nxdo_summary",
    "nxdo_enabled",
    "nxdo_target_repos",
    "run_nxdo_discovery",
]
