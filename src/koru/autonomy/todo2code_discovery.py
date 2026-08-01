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

Environment knobs (``os.environ`` first, then project ``.env``):

- ``KORU_TODO2CODE_ENABLE``: ``0``/``false`` disables the generator (default on).
- ``KORU_TODO2CODE_BIN``: explicit path to the ``t2c`` executable.
- ``KORU_TODO2CODE_MAX_TICKETS``: cap of tickets created per run (default 10).
- ``KORU_TODO2CODE_STALE_MINUTES``: reuse fresh plans without re-running
  pipeline (default 60).
- ``KORU_TODO2CODE_TIMEOUT_SECONDS``: subprocess timeout (default 900).
- ``KORU_TODO2CODE_OUT``: pipeline output directory under the project
  (default ``.intent``).
- ``KORU_TODO2CODE_LLM_MODEL``: first-attempt code model (default Claude Opus
  5); retries use ``KORU_TODO2CODE_LLM_FALLBACK_MODEL``.
- ``KORU_TODO2CODE_LLM_MAX_TOKENS``: response ceiling restored by Koru when an
  older Planfile schema drops queue-only inputs (default 4000).
- ``KORU_TODO2CODE_LLM_EXECUTOR``: request autonomous LLM execution (default
  off). It is honored only together with ``KORU_TODO2CODE_CONTRACT``.
- ``KORU_TODO2CODE_CONTRACT``: capability contract defined by the target
  project's ``koru.yaml`` and named by autonomous todo2code tickets.
"""

from __future__ import annotations

import hashlib
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

from koru.autonomy.code_change_usefulness import (
    is_useful_plan,
    plan_useful_paths,
    plan_usefulness_score,
)

Runner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]

DEFAULT_SOURCE = "koru-todo2code-discovery"
DEFAULT_OUT_SUBDIR = ".intent"
DEFAULT_MAX_TICKETS = 10
DEFAULT_STALE_MINUTES = 60.0
DEFAULT_TIMEOUT_SECONDS = 900.0
DEFAULT_MIN_USEFULNESS = 8.0
PLANS_FILENAME = "code-change-plans.json"

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


def _dotenv_value(project: Path | None, name: str) -> str:
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


def todo2code_enabled(project: Path | None = None) -> bool:
    return _env_flag("KORU_TODO2CODE_ENABLE", True, project)


def _t2c_executable(project: Path | None = None) -> str | None:
    override = _config_value("KORU_TODO2CODE_BIN", project)
    if override:
        path = Path(override).expanduser()
        return str(path) if path.is_file() else None
    found = shutil.which("t2c")
    if found:
        return found
    # Common local install from the monorepo checkout.
    sibling = Path.home() / "github" / "semcod" / "todo2code" / "dist" / "src" / "cli.js"
    if sibling.is_file():
        return str(sibling)
    return None


def _resolve_t2c_cli_js(binary: str) -> str | None:
    """Resolve ``t2c`` / symlink / path to the real ``cli.js`` entrypoint.

    ``todo2code`` only calls ``main()`` when ``process.argv[1]`` equals
    ``import.meta.url``. Invoking a PATH symlink such as
    ``~/.nvm/.../bin/t2c`` therefore exits 0 without running the pipeline.
    Always prefer ``node <resolved-cli.js>`` when we can resolve to a ``.js``
    file.
    """
    path = Path(binary)
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path
    if resolved.is_file() and resolved.suffix == ".js":
        return str(resolved)
    if path.is_file() and path.suffix == ".js":
        return str(path)
    return None


def _out_dir(project: Path) -> Path:
    sub = _config_value("KORU_TODO2CODE_OUT", project) or DEFAULT_OUT_SUBDIR
    candidate = (project / sub).resolve()
    try:
        candidate.relative_to(project.resolve())
    except ValueError as exc:
        raise ValueError(
            "KORU_TODO2CODE_OUT must resolve inside the target project"
        ) from exc
    return candidate


def _optional_input(project: Path, *candidates: str) -> Path | None:
    for name in candidates:
        path = project / name
        if path.is_file():
            return path
    return None


def _build_pipeline_cmd(
    binary: str,
    project: Path,
    *,
    out_dir: Path,
) -> list[str]:
    # Prefer node + resolved cli.js so PATH symlinks actually run main().
    cli_js = _resolve_t2c_cli_js(binary)
    if cli_js is not None:
        cmd = ["node", cli_js, "pipeline", str(project)]
    else:
        cmd = [binary, "pipeline", str(project)]

    cmd.extend(
        [
            "--nl-mode",
            "deterministic",
            "--markdown-mode",
            "deterministic",
            "--communication-mode",
            "deterministic",
            "--project-dir",
            "project",
            "--no-docs-llm",
            "--no-summary-llm",
            "--out",
            str(out_dir),
        ]
    )

    todo = _optional_input(project, "TODO.md", "todo.md", "TODO.txt", "todo.txt")
    if todo is not None:
        cmd.extend(["--todo", str(todo)])

    changelog = _optional_input(project, "CHANGELOG.md", "changelog.md")
    if changelog is not None:
        cmd.extend(["--changelog", str(changelog)])

    task = _optional_input(project, "TASK.md", "task.md", "TASKS.md")
    if task is not None:
        cmd.extend(["--task", str(task)])

    return cmd


def find_latest_plans_path(out_dir: Path) -> Path | None:
    """Return the newest ``code-change-plans.json`` under ``out_dir/runs``."""
    runs = out_dir / "runs"
    if not runs.is_dir():
        # Also accept a flat dump for tests / manual runs.
        flat = out_dir / PLANS_FILENAME
        return flat if flat.is_file() else None
    candidates = sorted(
        runs.glob(f"*/{PLANS_FILENAME}"),
        key=lambda p: p.stat().st_mtime if p.is_file() else 0.0,
        reverse=True,
    )
    for path in candidates:
        if path.is_file():
            return path
    return None


def _plans_fresh(plans_path: Path, *, stale_minutes: float) -> bool:
    try:
        age_s = max(0.0, time.time() - plans_path.stat().st_mtime)
    except OSError:
        return False
    return age_s < stale_minutes * 60.0


def _load_plan_set(plans_path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(plans_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _string_list(value: Any) -> list[str]:
    return [str(v) for v in (value or []) if str(v).strip()]


def _truncate(text: str, limit: int = 140) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _plan_paths(plan: dict[str, Any]) -> list[str]:
    """Useful target paths only (venv/binary/analysis dumps filtered out)."""
    return plan_useful_paths(plan)


def _plan_dedupe_key(plan: dict[str, Any]) -> str:
    plan_id = str(plan.get("id") or "").strip()
    if plan_id:
        return f"todo2code:plan:{plan_id}"
    plan_hash = str(plan.get("planHash") or "").strip()
    if plan_hash:
        return f"todo2code:hash:{plan_hash}"
    title = _slug(str(plan.get("title") or "plan"))
    paths = ",".join(_plan_paths(plan)[:5])
    digest = hashlib.sha256(f"{title}|{paths}".encode()).hexdigest()[:16]
    return f"todo2code:fallback:{digest}"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:80]


def _existing_todo2code_keys(
    project: Path,
    *,
    sprint: str = "current",
) -> tuple[set[str], set[tuple[str, tuple[str, ...]]]]:
    """Return plan dedupe keys and (title, files) pairs already in the sprint.

    Plan ids are content-bound and change when the intent graph fingerprint
    shifts, so title+files guards against re-filing the same work from a
    fresh pipeline run.
    """
    try:
        import yaml

        sprint_path = project / ".planfile" / "sprints" / f"{sprint}.yaml"
        data = yaml.safe_load(sprint_path.read_text(encoding="utf-8")) or {}
    except (OSError, Exception):  # noqa: BLE001 - best-effort duplicate guard
        return set(), set()
    sprint_data = data.get("sprint") if isinstance(data, dict) else None
    tickets = sprint_data.get("tickets") if isinstance(sprint_data, dict) else None
    if not isinstance(tickets, dict):
        return set(), set()
    keys: set[str] = set()
    title_files: set[tuple[str, tuple[str, ...]]] = set()
    for ticket in tickets.values():
        if not isinstance(ticket, dict):
            continue
        name = str(ticket.get("name") or "").strip()
        files = tuple(str(v) for v in (ticket.get("files") or []) if str(v).strip())
        if name.startswith("[todo2code]"):
            title_files.add((name, files))
        source = ticket.get("source")
        context = source.get("context") if isinstance(source, dict) else None
        if not isinstance(context, dict):
            continue
        key = str(context.get("dedupe_key") or "").strip()
        if key.startswith("todo2code:"):
            keys.add(key)
        # Also remember title/files from source-tagged tickets without prefix.
        tool = str(source.get("tool") or "") if isinstance(source, dict) else ""
        if tool == DEFAULT_SOURCE and name:
            title_files.add((name, files))
    return keys, title_files


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


def _ticket_text(plan: dict[str, Any], *, plans_rel: str) -> str:
    lines: list[str] = []
    description = str(plan.get("description") or "").strip()
    title = str(plan.get("title") or "").strip()
    lines.append(description or title or "Implement grounded todo2code code-change plan.")

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

    criteria = _string_list(plan.get("acceptanceCriteria"))
    if criteria:
        lines.append("")
        lines.append("Acceptance criteria:")
        lines.extend(f"- {item}" for item in criteria)

    risk = plan.get("risk") if isinstance(plan.get("risk"), dict) else {}
    risk_level = str(risk.get("level") or "").strip()
    risk_reasons = _string_list(risk.get("reasons"))
    if risk_level or risk_reasons:
        lines.append("")
        lines.append(f"Risk: {risk_level or 'unknown'}")
        lines.extend(f"- {reason}" for reason in risk_reasons)

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

    lines.append("")
    lines.append(
        "Implement only the declared target paths, then re-run "
        "`t2c evaluate-code-change` / pipeline before marking the ticket done."
    )
    return "\n".join(lines)


def _default_llm_model(project: Path | None = None) -> str:
    for key in ("KORU_TODO2CODE_LLM_MODEL", "LLM_MODEL", "KORU_LLM_MODEL"):
        value = _config_value(key, project)
        if value:
            return value
    return "openrouter/anthropic/claude-opus-5"


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
        "llm_model": _default_llm_model(project),
        "llm_max_tokens": _env_int("KORU_TODO2CODE_LLM_MAX_TOKENS", 4000, project),
        "llm_timeout_seconds": 300,
        "include_project_context": True,
        "context_files": paths[:12],
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
    from koru.tasks import create_nl_task

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

    created_titles: list[str] = []
    skipped_titles: list[str] = []
    existing_keys, existing_title_files = _existing_todo2code_keys(project, sprint=sprint)
    try:
        plans_rel = str(plans_path.relative_to(project))
    except ValueError:
        plans_rel = str(plans_path)

    for plan in useful:
        if len(created_titles) >= limit:
            break
        scaffold = _ticket_scaffold(plan, project=project, plans_path=plans_path, source=source)
        title = str(scaffold["title"])
        key = str(scaffold["source_context"]["dedupe_key"])
        files = tuple(str(v) for v in (scaffold.get("files") or []) if str(v).strip())
        title_key = (title, files)
        if key in existing_keys or title_key in existing_title_files:
            skipped_titles.append(title)
            continue
        priority = _PRIORITY_MAP.get(str(plan.get("priority") or "").upper(), "normal")
        if priority not in {"high", "normal", "low"}:
            priority = _PRIORITY_MAP.get(str(plan.get("priority") or "").lower(), "normal")
        score = plan_usefulness_score(plan, project=project)
        scaffold["source_context"]["usefulness_score"] = round(score, 2)
        scaffold["labels"] = list(
            dict.fromkeys([*scaffold.get("labels", []), "useful-code-change"])
        )
        try:
            created = create_nl_task(
                project,
                _ticket_text(plan, plans_rel=plans_rel),
                sprint=sprint,
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
            existing_title_files.add(title_key)
    return created_titles, skipped_titles, len(useful), filtered_out


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
    stale = (
        stale_minutes
        if stale_minutes is not None
        else _env_float("KORU_TODO2CODE_STALE_MINUTES", DEFAULT_STALE_MINUTES, project)
    )
    limit = (
        planfile_limit
        if planfile_limit is not None
        else max(1, _env_int("KORU_TODO2CODE_MAX_TICKETS", DEFAULT_MAX_TICKETS, project))
    )
    min_usefulness = _env_float(
        "KORU_TODO2CODE_MIN_USEFULNESS",
        DEFAULT_MIN_USEFULNESS,
        project,
    )

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
        raw_count = len([p for p in (plan_set.get("plans") or []) if isinstance(p, dict)])
        outcome.plans_count = raw_count
        if apply_planfile:
            applied, skipped, useful, filtered = _apply_plan_tickets(
                project,
                plan_set,
                plans_path=existing_plans,
                source=planfile_source,
                limit=limit,
                sprint=planfile_sprint,
                min_usefulness=min_usefulness,
            )
            outcome.applied_titles = applied
            outcome.skipped_titles = skipped
            outcome.useful_plans_count = useful
            outcome.filtered_out_count = filtered
        else:
            useful = [
                p
                for p in (plan_set.get("plans") or [])
                if isinstance(p, dict) and is_useful_plan(p, project=project, min_score=min_usefulness)
            ]
            outcome.useful_plans_count = len(useful)
            outcome.filtered_out_count = raw_count - len(useful)
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

    raw_count = len([p for p in (plan_set.get("plans") or []) if isinstance(p, dict)])
    outcome.plans_count = raw_count

    if not apply_planfile:
        useful = [
            p
            for p in (plan_set.get("plans") or [])
            if isinstance(p, dict) and is_useful_plan(p, project=project, min_score=min_usefulness)
        ]
        outcome.useful_plans_count = len(useful)
        outcome.filtered_out_count = raw_count - len(useful)
        return outcome

    applied, skipped, useful, filtered = _apply_plan_tickets(
        project,
        plan_set,
        plans_path=plans_path,
        source=planfile_source,
        limit=limit,
        sprint=planfile_sprint,
        min_usefulness=min_usefulness,
    )
    outcome.applied_titles = applied
    outcome.skipped_titles = skipped
    outcome.useful_plans_count = useful
    outcome.filtered_out_count = filtered
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
