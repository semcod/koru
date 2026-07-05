"""Idle-time ticket generation via ``nxdo`` (LLM next-task planner).

When ``koru auto`` finds the queue idle and neither ``koru scan`` nor the
``code2llm`` discovery produced runnable tickets, ask ``nxdo`` to plan the
next engineering tasks and file them as planfile tickets — instead of
letting the loop wait. ``nxdo`` can also plan for sibling repos
(``KORU_NXDO_REPOS``), so the loop generates cross-repo work when the
current project has nothing actionable.

Environment knobs (looked up in ``os.environ`` first, then in the
project's ``.env`` file — ``koru auto`` does not load ``.env`` into the
process environment, so the fallback keeps configuration in the repo):

- ``KORU_NXDO_ENABLE``: ``0``/``false`` disables the generator (default on).
- ``KORU_NXDO_BIN``: explicit path to the ``nxdo`` executable. Fallbacks:
  ``PATH`` lookup, then ``~/.venv/bin/nxdo`` (the shared semcod venv).
- ``KORU_NXDO_REPOS``: ``:``/``,``-separated extra repos (globs allowed,
  e.g. ``/home/tom/github/semcod/*``) to plan for after the project itself.
  Only directories containing ``.git`` qualify.
- ``KORU_NXDO_MAX_TICKETS``: cap of tickets created per run (default 5).
- ``KORU_NXDO_COOLDOWN_SECONDS``: per-repo cooldown between LLM planning
  runs (default 3600). Each run is a paid LLM call — the cooldown is the
  cost control.
- ``KORU_NXDO_EXTRA_CONTEXT``: extra prompt context passed to ``nxdo``.
- ``KORU_NXDO_MODEL``: LLM model id passed as ``nxdo --model`` (OpenRouter
  id without the ``openrouter/`` prefix, e.g. ``qwen/qwen3-coder-next``).
  Without it nxdo falls back to its own ``LLM_MODEL``/default.
- ``KORU_NXDO_TIMEOUT_SECONDS``: subprocess timeout (default 300).

Tickets are created through :func:`koru.tasks.create_nl_task` (same path as
code2llm discovery), so they carry proper ``execution``/``executor`` fields
and STARTER-prefixed ids that the queue loop can pick up. ``nxdo``'s own
``--sync-planfile`` is intentionally not used: it writes ``LANE-*`` tickets
without an ``execution`` block, which the queue would never select.
"""

from __future__ import annotations

import glob as _glob
import json
import os
import re
import shutil
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

Runner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]

DEFAULT_SOURCE = "koru-nxdo-discovery"
DEFAULT_MAX_TICKETS = 5
DEFAULT_COOLDOWN_SECONDS = 3600.0
DEFAULT_TIMEOUT_SECONDS = 300.0
STAMP_RELPATH = Path(".planfile") / ".koru" / "nxdo-discovery.json"

# nxdo Priority -> planfile priority accepted by create_nl_task.
_PRIORITY_MAP = {"high": "high", "medium": "normal", "low": "low"}


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


def _default_runner(cmd: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(cmd),
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=_env_float("KORU_NXDO_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
    )


def _dotenv_value(project: Path | None, name: str) -> str:
    """Read ``name`` from ``<project>/.env`` (simple ``KEY=VALUE`` lines)."""
    if project is None:
        return ""
    try:
        text = (project / ".env").read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(rf"^\s*{re.escape(name)}\s*=\s*(.+?)\s*$", text, re.M)
    return match.group(1).strip().strip("'\"") if match else ""


def _config_value(name: str, project: Path | None = None) -> str:
    return (os.environ.get(name) or "").strip() or _dotenv_value(project, name)


def _env_flag(name: str, default: bool, project: Path | None = None) -> bool:
    raw = _config_value(name, project).lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float, project: Path | None = None) -> float:
    try:
        return float(_config_value(name, project) or default)
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int, project: Path | None = None) -> int:
    try:
        return int(_config_value(name, project) or default)
    except (TypeError, ValueError):
        return default


def nxdo_enabled(project: Path | None = None) -> bool:
    return _env_flag("KORU_NXDO_ENABLE", True, project)


def _nxdo_executable(project: Path | None = None) -> str | None:
    override = _config_value("KORU_NXDO_BIN", project)
    if override:
        return override if Path(override).is_file() else None
    found = shutil.which("nxdo")
    if found:
        return found
    fallback = Path.home() / ".venv" / "bin" / "nxdo"
    return str(fallback) if fallback.is_file() else None


def _api_key_available(project: Path) -> bool:
    for key in ("OPENROUTER_API_KEY", "OPENAI_API_KEY"):
        if (os.environ.get(key) or "").strip():
            return True
    env_file = project / ".env"
    try:
        text = env_file.read_text(encoding="utf-8")
    except OSError:
        return False
    return bool(re.search(r"^\s*(OPENROUTER_API_KEY|OPENAI_API_KEY)\s*=\s*\S", text, re.M))


def nxdo_target_repos(project: Path) -> list[Path]:
    """The project itself plus ``KORU_NXDO_REPOS`` extras (globs expanded)."""
    project = project.resolve()
    repos: list[Path] = [project]
    raw = _config_value("KORU_NXDO_REPOS", project)
    if not raw:
        return repos
    for spec in re.split(r"[:,]", raw):
        spec = os.path.expanduser(spec.strip())
        if not spec:
            continue
        for hit in sorted(_glob.glob(spec)):
            path = Path(hit).resolve()
            if path == project or path in repos:
                continue
            if path.is_dir() and (path / ".git").exists():
                repos.append(path)
    return repos


def _stamp_path(project: Path) -> Path:
    return project / STAMP_RELPATH


def _load_stamps(project: Path) -> dict[str, float]:
    try:
        data = json.loads(_stamp_path(project).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): float(v) for k, v in data.items() if isinstance(v, (int, float))}


def _save_stamps(project: Path, stamps: dict[str, float]) -> None:
    path = _stamp_path(project)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(stamps, indent=2, sort_keys=True), encoding="utf-8")
    except OSError:
        pass


def _select_target_repo(project: Path, *, now: float) -> tuple[Path | None, float]:
    """First repo whose per-repo cooldown has expired (project first)."""
    cooldown = _env_float("KORU_NXDO_COOLDOWN_SECONDS", DEFAULT_COOLDOWN_SECONDS, project)
    stamps = _load_stamps(project)
    best_remaining = float("inf")
    for repo in nxdo_target_repos(project):
        last = stamps.get(str(repo), 0.0)
        remaining = cooldown - (now - last)
        if remaining <= 0:
            return repo, 0.0
        best_remaining = min(best_remaining, remaining)
    return None, best_remaining


def _plan_from_output(stdout: str) -> dict[str, Any] | None:
    """Extract the TaskPlan JSON object from ``nxdo plan --json`` output."""
    text = (stdout or "").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:80]


def _dedupe_key(repo: Path, task: dict[str, Any]) -> str:
    return f"nxdo:{repo.name}:{_slug(str(task.get('title') or ''))}"


def _existing_nxdo_dedupe_keys(project: Path, *, sprint: str = "current") -> set[str]:
    try:
        import yaml  # local import; yaml is already a runtime dep of koru

        sprint_path = project / ".planfile" / "sprints" / f"{sprint}.yaml"
        data = yaml.safe_load(sprint_path.read_text(encoding="utf-8")) or {}
    except (OSError, Exception):  # noqa: BLE001 - best-effort duplicate guard
        return set()
    sprint_data = data.get("sprint") if isinstance(data, dict) else None
    tickets = sprint_data.get("tickets") if isinstance(sprint_data, dict) else None
    if not isinstance(tickets, dict):
        return set()
    keys: set[str] = set()
    for ticket in tickets.values():
        if not isinstance(ticket, dict):
            continue
        source = ticket.get("source")
        context = source.get("context") if isinstance(source, dict) else None
        if not isinstance(context, dict):
            continue
        key = str(context.get("dedupe_key") or "").strip()
        if key.startswith("nxdo:"):
            keys.add(key)
    return keys


def _ticket_text(task: dict[str, Any], *, repo: Path, project: Path) -> str:
    lines: list[str] = []
    if repo != project:
        lines.append(f"[repo: {repo}] Zadanie dotyczy repozytorium {repo} (nie {project.name}).")
    description = str(task.get("description") or "").strip()
    lines.append(description or str(task.get("title") or "nxdo task").strip())
    criteria = [str(c).strip() for c in (task.get("acceptance_criteria") or []) if str(c).strip()]
    if criteria:
        lines.append("Acceptance criteria:")
        lines.extend(f"- {c}" for c in criteria)
    return "\n".join(lines)


def _ticket_scaffold(task: dict[str, Any], *, repo: Path, project: Path) -> dict[str, Any]:
    labels = ["nxdo", "discovery"]
    task_type = str(task.get("task_type") or "").strip()
    if task_type:
        labels.append(task_type)
    if repo != project:
        labels.append("cross-repo")
    return {
        "title": str(task.get("title") or "nxdo discovery ticket").strip(),
        "labels": labels,
        "files": [],
        "source_tool": DEFAULT_SOURCE,
        "source_context": {
            "signal": "nxdo_plan",
            "dedupe_key": _dedupe_key(repo, task),
            "repo": str(repo),
        },
        "executor_kind": "human",
        "executor_mode": "interactive",
    }


def _apply_plan_tickets(
    project: Path,
    repo: Path,
    plan: dict[str, Any],
    *,
    limit: int,
) -> tuple[list[str], list[str]]:
    from koru.tasks import create_nl_task

    tasks = [t for t in (plan.get("tasks") or []) if isinstance(t, dict)]
    created_titles: list[str] = []
    skipped_titles: list[str] = []
    existing_keys = _existing_nxdo_dedupe_keys(project)
    for task in tasks:
        if len(created_titles) >= limit:
            break
        scaffold = _ticket_scaffold(task, repo=repo, project=project)
        title = str(scaffold["title"])
        key = str(scaffold["source_context"]["dedupe_key"])
        if key in existing_keys:
            skipped_titles.append(title)
            continue
        priority = _PRIORITY_MAP.get(str(task.get("priority") or "").lower(), "normal")
        try:
            created = create_nl_task(
                project,
                _ticket_text(task, repo=repo, project=project),
                sprint="current",
                priority=priority,
                scaffold=scaffold,
            )
        except (OSError, ValueError) as exc:
            skipped_titles.append(f"{title}: {exc}")
            continue
        if getattr(created, "reused", False):
            skipped_titles.append(title)
        else:
            created_titles.append(title)
            existing_keys.add(key)
    return created_titles, skipped_titles


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

    if not nxdo_enabled(project):
        outcome.skipped_reason = "disabled via KORU_NXDO_ENABLE"
        return outcome

    binary = _nxdo_executable(project)
    if binary is None:
        outcome.skipped_reason = "nxdo not on PATH (set KORU_NXDO_BIN)"
        return outcome
    outcome.nxdo_path = binary

    if not _api_key_available(project):
        outcome.skipped_reason = "no OPENROUTER_API_KEY/OPENAI_API_KEY (env or project .env)"
        return outcome

    started = now()
    repo, cooldown_remaining = _select_target_repo(project, now=started)
    if repo is None:
        outcome.skipped_reason = f"cooldown active for all repos (~{cooldown_remaining:.0f}s remaining)"
        return outcome
    outcome.target_repo = str(repo)

    cmd = [binary, "plan", str(repo), "--json"]
    model = _config_value("KORU_NXDO_MODEL", project)
    if model:
        cmd.extend(["--model", model])
    extra_context = _config_value("KORU_NXDO_EXTRA_CONTEXT", project)
    if extra_context:
        cmd.extend(["--extra-context", extra_context])

    start = time.monotonic()
    try:
        result = runner(cmd, project)
    except subprocess.TimeoutExpired as exc:
        outcome.error = f"nxdo timed out after {exc.timeout}s"
        outcome.nxdo_duration_s = time.monotonic() - start
        return outcome
    except (OSError, ValueError) as exc:
        outcome.error = f"nxdo exec failed: {exc}"
        outcome.nxdo_duration_s = time.monotonic() - start
        return outcome
    outcome.nxdo_duration_s = time.monotonic() - start
    outcome.nxdo_returncode = result.returncode
    outcome.ran = True

    # Stamp the attempt even on failure: a failing repo must not burn an
    # LLM call every idle cycle.
    stamps = _load_stamps(project)
    stamps[str(repo)] = started
    _save_stamps(project, stamps)

    if result.returncode != 0:
        lines = (result.stderr or result.stdout or "").strip().splitlines()
        outcome.error = (lines[-1:] or [f"nxdo rc={result.returncode}"])[0]
        return outcome

    plan = _plan_from_output(result.stdout)
    if plan is None:
        outcome.error = "nxdo produced no parseable TaskPlan JSON"
        return outcome

    limit = max(1, _env_int("KORU_NXDO_MAX_TICKETS", DEFAULT_MAX_TICKETS, project))
    applied, skipped = _apply_plan_tickets(project, repo, plan, limit=limit)
    outcome.applied_titles = applied
    outcome.skipped_titles = skipped
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
