"""Bootstrap a new project from a flat-format pipeline YAML.

This module bridges the two koru pipeline formats:

- **Authoring (flat)** — the format from
  ``docs/planfile-execution-gateway.md`` and ``examples/bootstrap.planfile.yaml``.
  Tasks are a top-level list, easy to write and review.

- **Runtime (nested)** — the planfile-native layout:
  ``.planfile/sprints/<sprint>.yaml`` with tickets keyed by id under
  ``sprint.tickets``. Used by ``planfile`` CLI and ``koru --queue``.

The converter validates the flat schema and materialises it into the
runtime layout without touching planfile internals — koru stays a thin
orchestrator and planfile remains the source of truth at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

VALID_EXECUTOR_KINDS: frozenset[str] = frozenset({"shell", "human", "llm", "api", "mcp"})
VALID_EXECUTOR_MODES: frozenset[str] = frozenset({"automatic", "interactive"})
VALID_STATUSES: frozenset[str] = frozenset({"open", "in_progress", "review", "done", "blocked"})
VALID_PRIORITIES: frozenset[str] = frozenset({"critical", "high", "medium", "normal", "low"})
VALID_EXECUTION_STATES: frozenset[str] = frozenset(
    {"pending", "ready", "running", "waiting_input", "done", "failed", "skipped"},
)


@dataclass
class ValidationError:
    task_id: str
    field: str
    message: str

    def __str__(self) -> str:
        return f"{self.task_id}: {self.field}: {self.message}"


@dataclass
class ImportReport:
    project_dir: Path
    sprint: str
    tickets_imported: list[str] = field(default_factory=list)
    config_created: bool = False
    sprint_file_created: bool = False
    sprint_file_overwritten: bool = False

    def summary(self) -> str:
        lines = [
            f"project: {self.project_dir}",
            f"sprint:  {self.sprint}",
            f"tickets: {len(self.tickets_imported)} imported",
        ]
        if self.config_created:
            lines.append("config:  .planfile/config.yaml created")
        if self.sprint_file_created:
            lines.append(f"sprint:  .planfile/sprints/{self.sprint}.yaml created")
        elif self.sprint_file_overwritten:
            lines.append(f"sprint:  .planfile/sprints/{self.sprint}.yaml overwritten")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Loader + validator
# ---------------------------------------------------------------------------


def load_flat_pipeline(path: str | Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Read a flat-format pipeline YAML and return ``(header, tasks)``.

    The file must have a ``tasks`` top-level list. The header is everything
    else (project, version, generated, description, etc.) and is preserved
    for round-tripping.
    """
    file = Path(path)
    if not file.exists():
        raise FileNotFoundError(f"pipeline file not found: {file}")
    data = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{file}: expected a YAML mapping at top level")
    raw_tasks = data.get("tasks")
    if not isinstance(raw_tasks, list):
        raise ValueError(f"{file}: missing top-level 'tasks' list")
    tasks = [t for t in raw_tasks if isinstance(t, dict)]
    header = {k: v for k, v in data.items() if k != "tasks"}
    return header, tasks


def _validate_id(task: dict[str, Any], seen_ids: set[str]) -> list[ValidationError]:
    """Validate task id field."""
    errors: list[ValidationError] = []
    tid = str(task.get("id") or "<missing-id>")

    if "id" not in task:
        errors.append(ValidationError(tid, "id", "missing"))
        return errors
    if tid in seen_ids:
        errors.append(ValidationError(tid, "id", "duplicate"))
        return errors

    return errors


def _validate_name(task: dict[str, Any]) -> list[ValidationError]:
    """Validate task name/title field."""
    tid = str(task.get("id") or "<missing-id>")
    if not (task.get("name") or task.get("title")):
        return [ValidationError(tid, "name", "missing (or 'title')")]
    return []


def _validate_status(task: dict[str, Any]) -> list[ValidationError]:
    """Validate task status field."""
    tid = str(task.get("id") or "<missing-id>")
    status = task.get("status", "open")
    if status not in VALID_STATUSES:
        return [ValidationError(tid, "status", f"{status!r} not in {sorted(VALID_STATUSES)}")]
    return []


def _validate_priority(task: dict[str, Any]) -> list[ValidationError]:
    """Validate task priority field."""
    tid = str(task.get("id") or "<missing-id>")
    priority = task.get("priority", "normal")
    if isinstance(priority, str) and priority not in VALID_PRIORITIES:
        return [ValidationError(tid, "priority", f"{priority!r} not in {sorted(VALID_PRIORITIES)}")]
    return []


def _validate_executor(task: dict[str, Any]) -> list[ValidationError]:
    """Validate task executor field."""
    tid = str(task.get("id") or "<missing-id>")
    errors: list[ValidationError] = []
    executor = task.get("executor")

    if not isinstance(executor, dict):
        return [ValidationError(tid, "executor", "missing or not a mapping")]

    kind = executor.get("kind")
    if kind not in VALID_EXECUTOR_KINDS:
        errors.append(
            ValidationError(
                tid, "executor.kind", f"{kind!r} not in {sorted(VALID_EXECUTOR_KINDS)}"
            ),
        )

    mode = executor.get("mode", "automatic")
    if mode not in VALID_EXECUTOR_MODES:
        errors.append(
            ValidationError(
                tid, "executor.mode", f"{mode!r} not in {sorted(VALID_EXECUTOR_MODES)}"
            ),
        )

    return errors


def _validate_execution_state(task: dict[str, Any]) -> list[ValidationError]:
    """Validate task execution.state field."""
    tid = str(task.get("id") or "<missing-id>")
    execution = task.get("execution") or {}
    state = execution.get("state", "pending")
    if state not in VALID_EXECUTION_STATES:
        return [
            ValidationError(
                tid,
                "execution.state",
                f"{state!r} not in {sorted(VALID_EXECUTION_STATES)}",
            ),
        ]
    return []


def _validate_blocked_by(task: dict[str, Any]) -> list[ValidationError]:
    """Validate task blocked_by field."""
    tid = str(task.get("id") or "<missing-id>")
    errors: list[ValidationError] = []
    blocked_by = task.get("blocked_by", []) or []

    if not isinstance(blocked_by, list):
        return [ValidationError(tid, "blocked_by", "must be a list")]

    for dep in blocked_by:
        if not isinstance(dep, str):
            errors.append(ValidationError(tid, "blocked_by", f"non-string entry: {dep!r}"))

    return errors


def _validate_task(task: dict[str, Any], seen_ids: set[str]) -> list[ValidationError]:
    """Validate a single task. Returns a list of errors."""
    errors: list[ValidationError] = []

    errors.extend(_validate_id(task, seen_ids))

    # Early return if id is missing or duplicate
    if any(e.field == "id" for e in errors):
        return errors

    errors.extend(_validate_name(task))
    errors.extend(_validate_status(task))
    errors.extend(_validate_priority(task))
    errors.extend(_validate_executor(task))
    errors.extend(_validate_execution_state(task))
    errors.extend(_validate_blocked_by(task))

    return errors


def _validate_cross_task_dependencies(tasks: list[dict[str, Any]]) -> list[ValidationError]:
    """Validate cross-task dependencies (blocked_by references and cycles)."""
    errors: list[ValidationError] = []
    ids = {str(t.get("id")) for t in tasks if t.get("id")}
    for task in tasks:
        tid = str(task.get("id") or "")
        for dep in task.get("blocked_by") or []:
            if isinstance(dep, str) and dep not in ids:
                errors.append(ValidationError(tid, "blocked_by", f"unknown task id {dep!r}"))
    cycle = _detect_cycle(tasks)
    if cycle:
        errors.append(
            ValidationError(cycle[0], "blocked_by", f"cycle detected: {' → '.join(cycle)}"),
        )
    return errors


def validate_flat_pipeline(tasks: list[dict[str, Any]]) -> list[ValidationError]:
    """Validate a flat pipeline. Returns a list of errors (empty == valid)."""
    errors: list[ValidationError] = []
    seen_ids: set[str] = set()

    for task in tasks:
        task_errors = _validate_task(task, seen_ids)
        errors.extend(task_errors)
        if task.get("id"):
            seen_ids.add(str(task.get("id")))

    # Cross-task validation: all blocked_by references resolve, no cycles
    errors.extend(_validate_cross_task_dependencies(tasks))
    return errors


def _dependency_graph(tasks: list[dict[str, Any]]) -> dict[str, list[str]]:
    graph: dict[str, list[str]] = {}
    for task in tasks:
        task_id = str(task.get("id") or "")
        if not task_id:
            continue
        graph[task_id] = [dep for dep in (task.get("blocked_by") or []) if isinstance(dep, str)]
    return graph


def _reconstruct_cycle(parent: dict[str, str], *, node: str, neighbor: str) -> list[str]:
    cycle = [node]
    cursor = node
    while cursor != neighbor and cursor in parent:
        cursor = parent[cursor]
        cycle.append(cursor)
    cycle.append(node)
    cycle.reverse()
    return cycle


def _detect_cycle(tasks: list[dict[str, Any]]) -> list[str]:
    """Return the first detected dependency cycle, or empty list."""
    graph = _dependency_graph(tasks)
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = dict.fromkeys(graph, WHITE)
    parent: dict[str, str] = {}

    def dfs(node: str) -> list[str]:
        color[node] = GRAY
        for nb in graph.get(node, []):
            if color.get(nb, WHITE) == GRAY:
                return _reconstruct_cycle(parent, node=node, neighbor=nb)
            if color.get(nb, WHITE) == WHITE:
                parent[nb] = node
                found = dfs(nb)
                if found:
                    return found
        color[node] = BLACK
        return []

    for node in graph:
        if color[node] == WHITE:
            cycle = dfs(node)
            if cycle:
                return cycle
    return []


# ---------------------------------------------------------------------------
# Materialiser (flat → nested .planfile/)
# ---------------------------------------------------------------------------


def materialize_to_planfile(
    flat_tasks: list[dict[str, Any]],
    project_dir: str | Path,
    *,
    sprint: str = "current",
    sprint_name: str = "Imported pipeline",
    prefix: str = "PLF",
    overwrite: bool = False,
) -> ImportReport:
    """Write ``flat_tasks`` into ``project_dir/.planfile/sprints/<sprint>.yaml``.

    Creates ``.planfile/config.yaml`` if missing. Existing sprint file is
    preserved unless ``overwrite=True``; otherwise raises ``FileExistsError``.
    """
    project = Path(project_dir).resolve()
    base_dir = project / ".planfile"
    sprints_dir = base_dir / "sprints"
    config_path = base_dir / "config.yaml"
    sprint_path = sprints_dir / f"{sprint}.yaml"

    sprints_dir.mkdir(parents=True, exist_ok=True)

    report = ImportReport(project_dir=project, sprint=sprint)

    if not config_path.exists():
        config_data = {
            "project": project.name,
            "prefix": prefix,
            "next_id": _next_id_after(flat_tasks, prefix),
        }
        config_path.write_text(yaml.safe_dump(config_data, sort_keys=False), encoding="utf-8")
        report.config_created = True

    if sprint_path.exists() and not overwrite:
        raise FileExistsError(
            f"{sprint_path} already exists. Use overwrite=True (or --force) to replace it.",
        )

    tickets: dict[str, dict[str, Any]] = {}
    for task in flat_tasks:
        tid = str(task["id"])
        tickets[tid] = _normalise_task(task, default_sprint=sprint)
        report.tickets_imported.append(tid)

    sprint_data = {
        "sprint": {
            "id": sprint,
            "name": sprint_name,
            "status": "active",
            "tickets": tickets,
        },
    }
    if sprint_path.exists():
        report.sprint_file_overwritten = True
    else:
        report.sprint_file_created = True
    sprint_path.write_text(
        yaml.safe_dump(sprint_data, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    return report


def _normalise_task(task: dict[str, Any], *, default_sprint: str) -> dict[str, Any]:
    """Return a planfile-Ticket-compatible mapping for a flat task."""
    out = dict(task)
    # Map title -> name if name absent
    if "name" not in out and "title" in out:
        out["name"] = out.pop("title")
    out.setdefault("sprint", default_sprint)
    out.setdefault("status", "open")
    out.setdefault("priority", "normal")

    # Default the executor mode for safety.
    if isinstance(out.get("executor"), dict):
        out["executor"].setdefault("mode", "automatic")

    # Default execution.state to "ready" for tasks with no blocked_by, else "pending"
    execution = out.get("execution")
    if not isinstance(execution, dict):
        execution = {}
    execution.setdefault("queue", "default")
    if "state" not in execution:
        execution["state"] = "ready" if not out.get("blocked_by") else "pending"
    execution.setdefault("attempt", 0)
    execution.setdefault("max_attempts", 1)
    out["execution"] = execution

    # Drop fields planfile doesn't model so it stays clean.
    for noisy in ("phase",):
        out.pop(noisy, None)

    return out


def _next_id_after(tasks: list[dict[str, Any]], prefix: str) -> int:
    """Compute a safe next_id higher than any numeric suffix already in use."""
    max_id = 0
    pref = f"{prefix}-"
    for task in tasks:
        tid = str(task.get("id") or "")
        if tid.startswith(pref):
            try:
                num = int(tid[len(pref) :].split("-")[-1])
                max_id = max(max_id, num)
            except ValueError:
                continue
    return max_id + 1


# ---------------------------------------------------------------------------
# Top-level entry: validate → materialize
# ---------------------------------------------------------------------------


def import_flat_pipeline(
    flat_path: str | Path,
    project_dir: str | Path,
    *,
    sprint: str = "current",
    overwrite: bool = False,
    prefix: str | None = None,
) -> ImportReport:
    """Validate and import a flat pipeline into ``project_dir/.planfile/``.

    Raises ``ValueError`` with a multi-line message if validation fails.
    """
    header, tasks = load_flat_pipeline(flat_path)
    if not tasks:
        raise ValueError(f"{flat_path}: no tasks found")

    errors = validate_flat_pipeline(tasks)
    if errors:
        joined = "\n".join(f"  - {e}" for e in errors)
        raise ValueError(f"{flat_path}: validation failed\n{joined}")

    sprint_name = str(header.get("description") or header.get("project") or "Imported pipeline")
    if "\n" in sprint_name:
        sprint_name = sprint_name.splitlines()[0].strip()

    return materialize_to_planfile(
        tasks,
        project_dir,
        sprint=sprint,
        sprint_name=sprint_name,
        prefix=(prefix or _infer_prefix(tasks) or "PLF"),
        overwrite=overwrite,
    )


def _infer_prefix(tasks: list[dict[str, Any]]) -> str | None:
    """Infer planfile prefix from the first task id (e.g. KORU-B-001 → KORU)."""
    for task in tasks:
        tid = str(task.get("id") or "")
        if "-" in tid:
            return tid.split("-", 1)[0]
    return None
