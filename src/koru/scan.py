"""Auto-generate planfile tickets from real repo signals.

``koru scan`` looks at concrete, observable signals in the project and
proposes tickets the agent (or human) can act on immediately, instead
of the placeholder ``STARTER-001 / 002`` that ``koru --init`` creates.

Signals (each implemented as a small probe so they can be unit-tested
in isolation):

- **pytest collection** — runs ``pytest --collect-only -q`` and turns
  collection errors (``ModuleNotFoundError``, ``ImportError`` …) into
  high-priority tickets.
- **TODO / FIXME / XXX / HACK markers** — grouped by file; one ticket
  per file when the count is non-trivial.
- **missing on-change gates** — wup / regix / testql configs absent
  while their markers (pyproject etc.) are present → bootstrap tickets.
- **missing semcod tools listed in pyproject** — when a tool appears
  as a dependency but is not installed / not invokable.
- **gitignore drift** — ``.planfile/.koru/`` should be gitignored.

The output is dry-run by default (a list of :class:`Suggestion`
dataclasses); pass ``apply=True`` to ``run_scan`` to persist them as
planfile tickets through ``planfile ticket create``.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from importlib.util import find_spec
from pathlib import Path
from typing import Any, Callable, Sequence

from .semcod_tools import detect_semcod_tools


# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Suggestion:
    """One proposed planfile ticket derived from a repo signal."""

    signal: str  # e.g. "pytest_collect" / "todo_markers" / "missing_gate"
    title: str
    description: str
    priority: str = "normal"  # critical | high | normal | low
    labels: tuple[str, ...] = ()
    files: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal": self.signal,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "labels": list(self.labels),
            "files": list(self.files),
        }


@dataclass(frozen=True)
class ScanResult:
    """Aggregate output of ``run_scan``."""

    suggestions: list[Suggestion]
    applied: list[str] = field(default_factory=list)  # ticket IDs / names actually created
    skipped: list[str] = field(default_factory=list)  # duplicates already in planfile

    def to_dict(self) -> dict[str, Any]:
        return {
            "suggestions": [s.to_dict() for s in self.suggestions],
            "applied": list(self.applied),
            "skipped": list(self.skipped),
        }


# ---------------------------------------------------------------------------
# Signal probes — each returns a list[Suggestion]; never raises
# ---------------------------------------------------------------------------


_COLLECT_ERROR_RE = re.compile(
    r"^(?:ERROR|FAILED)\s+(?P<path>\S+\.py)(?:::\S+)?\s*-\s*(?P<msg>.+)$",
    re.MULTILINE,
)
_IMPORT_ERROR_RE = re.compile(
    r"^E\s+(?P<exc>ModuleNotFoundError|ImportError):\s*(?P<msg>.+)$",
    re.MULTILINE,
)


def scan_pytest_collect(
    project: Path,
    *,
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]] | None = None,
    timeout_seconds: float = 30.0,
) -> list[Suggestion]:
    """Probe pytest collection; surface every collection failure as a ticket."""
    if not (project / "tests").exists() and not (project / "pyproject.toml").exists():
        return []

    def _default_runner(
        cmd: Sequence[str], cwd: Path
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(cmd),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )

    use_runner = runner or _default_runner
    try:
        result = use_runner(
            ["python3", "-m", "pytest", "--collect-only", "-q", "--no-header"],
            project,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []

    if result.returncode == 0:
        return []

    output = (result.stdout or "") + "\n" + (result.stderr or "")

    suggestions: list[Suggestion] = []
    seen_paths: set[str] = set()
    for match in _COLLECT_ERROR_RE.finditer(output):
        path = match.group("path").strip()
        msg = match.group("msg").strip()
        if path in seen_paths:
            continue
        seen_paths.add(path)
        suggestions.append(
            Suggestion(
                signal="pytest_collect",
                title=f"Fix pytest collection error in {path}",
                description=(
                    f"`pytest --collect-only` cannot import `{path}`.\n\n"
                    f"Reason: {msg}\n\n"
                    "This blocks the CI gate; resolve before any other ticket."
                ),
                priority="high",
                labels=("ci", "bug", "scan"),
                files=(path,),
            )
        )

    # No per-file match but stderr mentions an import error → one umbrella ticket.
    if not suggestions:
        imp = _IMPORT_ERROR_RE.search(output)
        if imp:
            suggestions.append(
                Suggestion(
                    signal="pytest_collect",
                    title="Fix package import path for pytest collection",
                    description=(
                        "`pytest --collect-only` fails before collecting any "
                        f"test:\n\n    {imp.group('exc')}: {imp.group('msg').strip()}\n\n"
                        "Likely cause: missing `[tool.pytest.ini_options] "
                        "pythonpath = [\"src\"]` (or equivalent) in "
                        "`pyproject.toml`, or an editable install missing."
                    ),
                    priority="high",
                    labels=("ci", "bug", "scan"),
                )
            )
    return suggestions


_MARKER_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b[: ]")
_DEFAULT_SCAN_EXCLUDES: frozenset[str] = frozenset(
    {".git", "__pycache__", ".venv", "venv", "node_modules", "build", "dist"}
)


def scan_todo_markers(
    project: Path,
    *,
    min_per_file: int = 3,
    max_files_walked: int = 2_000,
) -> list[Suggestion]:
    """Count TODO/FIXME/XXX/HACK per Python file; suggest cleanup tickets.

    ``min_per_file`` filters out trivial cases — most repos accumulate a
    handful of historical TODOs that are not worth surfacing.
    """
    counts: Counter[str] = Counter()
    walked = 0
    for path in project.rglob("*.py"):
        walked += 1
        if walked > max_files_walked:
            break
        if any(part in _DEFAULT_SCAN_EXCLUDES for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        n = len(_MARKER_RE.findall(text))
        if n >= min_per_file:
            counts[str(path.relative_to(project))] = n
    return [
        Suggestion(
            signal="todo_markers",
            title=f"Resolve {n} TODO/FIXME markers in {rel_path}",
            description=(
                f"Static scan found **{n}** TODO/FIXME/XXX/HACK markers "
                f"in `{rel_path}`. Either address them or convert each into "
                "an explicit planfile ticket so backlog stays honest."
            ),
            priority="low",
            labels=("cleanup", "scan"),
            files=(rel_path,),
        )
        for rel_path, n in counts.most_common(10)
    ]


_GATE_MARKERS: tuple[tuple[str, str, str], ...] = (
    ("wup", "wup.yaml", "intelligent file watcher (3-layer: detect → quick → full)"),
    ("regix", "regix.yaml", "regression metrics gate (CC / MI / coverage delta)"),
    (
        "testql",
        "testql-scenarios",
        "behavioural HTTP probes (TOON YAML scenarios)",
    ),
)


def scan_missing_gates(project: Path) -> list[Suggestion]:
    """Suggest bootstrap tickets for unconfigured on-change gates."""
    suggestions: list[Suggestion] = []
    for tool_id, marker, role in _GATE_MARKERS:
        configured = (project / marker).exists()
        installed = bool(shutil.which(tool_id)) or find_spec(tool_id) is not None
        if configured or not installed:
            continue
        suggestions.append(
            Suggestion(
                signal="missing_gate",
                title=f"Bootstrap {tool_id} on-change gate",
                description=(
                    f"`{tool_id}` is installed but no `{marker}` config "
                    "exists in the project root. Bootstrap with "
                    f"`task template:install:{tool_id}` (in koru) or "
                    "follow `workflows/on-change-gates.md`.\n\n"
                    f"Role: {role}."
                ),
                priority="normal",
                labels=("bootstrap", "gates", "scan"),
            )
        )
    return suggestions


def scan_missing_tools(project: Path) -> list[Suggestion]:
    """Suggest install tickets for tools declared in pyproject but missing."""
    pyproject = project / "pyproject.toml"
    if not pyproject.is_file():
        return []
    try:
        import tomllib

        with pyproject.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, Exception):  # noqa: BLE001 — tomllib raises a private type
        return []

    deps: list[str] = []
    project_section = data.get("project") or {}
    deps.extend(project_section.get("dependencies") or [])
    opt = project_section.get("optional-dependencies") or {}
    for extras in opt.values():
        deps.extend(extras or [])

    detected = {t.id: t for t in detect_semcod_tools(project)}
    suggestions: list[Suggestion] = []
    for dep in deps:
        name = re.split(r"[<>=!\[ ;]", dep, maxsplit=1)[0].strip().lower()
        if not name or name not in detected:
            continue
        tool = detected[name]
        if tool.available:
            continue
        suggestions.append(
            Suggestion(
                signal="missing_tool",
                title=f"Install semcod tool `{name}` (declared in pyproject)",
                description=(
                    f"`{name}` is listed in `pyproject.toml` dependencies "
                    "but is neither in PATH nor importable. Install it so "
                    "shell / api / llm tickets that depend on it can run.\n\n"
                    f"Role: {tool.role}."
                ),
                priority="normal",
                labels=("bootstrap", "deps", "scan"),
            )
        )
    return suggestions


def scan_gitignore_drift(project: Path) -> list[Suggestion]:
    """Ensure koru's runtime dir is gitignored."""
    gitignore = project / ".gitignore"
    needle = ".planfile/.koru"
    if not gitignore.is_file():
        return []
    try:
        text = gitignore.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    if needle in text:
        return []
    return [
        Suggestion(
            signal="gitignore_drift",
            title="Gitignore `.planfile/.koru/` runtime directory",
            description=(
                "koru writes ephemeral run logs to `.planfile/.koru/` "
                "but the project's `.gitignore` does not exclude it. "
                "Add the entry so run history isn't accidentally committed."
            ),
            priority="low",
            labels=("hygiene", "scan"),
            files=(".gitignore",),
        )
    ]


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def collect_suggestions(
    project: Path,
    *,
    skip_pytest: bool = False,
) -> list[Suggestion]:
    """Run every probe and concatenate the results."""
    project = project.resolve()
    out: list[Suggestion] = []
    if not skip_pytest:
        out.extend(scan_pytest_collect(project))
    out.extend(scan_todo_markers(project))
    out.extend(scan_missing_gates(project))
    out.extend(scan_missing_tools(project))
    out.extend(scan_gitignore_drift(project))
    return out


def _existing_scan_titles(
    project: Path,
    *,
    source: str,
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]] | None = None,
) -> set[str]:
    """Return titles of tickets already created by previous `koru scan` runs.

    Used to deduplicate ``--apply`` runs: re-running ``koru scan --apply``
    should not pile up identical tickets.
    """
    def _default(
        cmd: Sequence[str], cwd: Path
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(cmd), cwd=cwd, capture_output=True, text=True, check=False,
        )

    use_runner = runner or _default
    try:
        result = use_runner(
            ["planfile", "ticket", "list", "--source", source, "--format", "json"],
            project,
        )
    except (FileNotFoundError, OSError):
        return set()
    if result.returncode != 0:
        return set()
    try:
        payload = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return set()
    if not isinstance(payload, list):
        return set()
    titles: set[str] = set()
    for entry in payload:
        if isinstance(entry, dict):
            name = entry.get("name") or entry.get("title")
            if isinstance(name, str):
                titles.add(name)
    return titles


def _create_ticket(
    project: Path,
    suggestion: Suggestion,
    *,
    source: str,
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]] | None = None,
) -> bool:
    """Create one ticket via ``planfile ticket create``. Returns success."""
    def _default(
        cmd: Sequence[str], cwd: Path
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(cmd), cwd=cwd, capture_output=True, text=True, check=False,
        )

    use_runner = runner or _default
    cmd: list[str] = [
        "planfile", "ticket", "create",
        suggestion.title,
        "--priority", suggestion.priority,
        "--source", source,
        "--description", suggestion.description,
    ]
    for label in suggestion.labels:
        cmd.extend(["--label", label])
    for f in suggestion.files:
        cmd.extend(["--files", f])
    try:
        result = use_runner(cmd, project)
    except (FileNotFoundError, OSError):
        return False
    return result.returncode == 0


def run_scan(
    project: Path,
    *,
    apply: bool = False,
    limit: int | None = None,
    skip_pytest: bool = False,
    source: str = "koru-scan",
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]] | None = None,
) -> ScanResult:
    """End-to-end scan: collect signals, optionally create planfile tickets."""
    project = project.resolve()
    suggestions = collect_suggestions(project, skip_pytest=skip_pytest)
    # Stable ordering: priority (critical > high > normal > low), then signal.
    priority_rank = {"critical": 0, "high": 1, "normal": 2, "low": 3}
    suggestions.sort(
        key=lambda s: (priority_rank.get(s.priority, 99), s.signal, s.title)
    )
    if limit is not None and limit >= 0:
        suggestions = suggestions[:limit]

    if not apply:
        return ScanResult(suggestions=suggestions)

    existing = _existing_scan_titles(project, source=source, runner=runner)
    applied: list[str] = []
    skipped: list[str] = []
    for s in suggestions:
        if s.title in existing:
            skipped.append(s.title)
            continue
        ok = _create_ticket(project, s, source=source, runner=runner)
        if ok:
            applied.append(s.title)
        else:
            skipped.append(s.title)
    return ScanResult(suggestions=suggestions, applied=applied, skipped=skipped)
