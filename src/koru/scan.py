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
- **Optional semcod / quality exports** — when ``--semcod-artifacts`` or
  ``KORU_SCAN_SEMCOD_ARTIFACTS=1``: read **jscpd** JSON, **code2llm**
  ``analysis.toon*``, **TestQL** text export, optional **redup** JSON to
  open backlog tickets for duplication / refactors / API regressions.

The output is dry-run by default (a list of :class:`Suggestion`
dataclasses); pass ``apply=True`` to ``run_scan`` to persist them as
planfile tickets through ``planfile ticket create``.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import shutil
import subprocess
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from .semcod_tools import detect_semcod_tools
from .tasks import create_nl_task
from .utils.subprocess_runner import default_subprocess_runner, get_python_cmd

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

    def _default_runner(cmd: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(cmd),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )

    use_runner = runner or _default_runner
    cmd = get_python_cmd(project) + ["-m", "pytest", "--collect-only", "-q", "--no-header"]
    try:
        result = use_runner(cmd, project)
    except subprocess.TimeoutExpired:
        # A timeout is a *real signal*, not a quiet success. Hiding it
        # behind ``return []`` produced false-positive "repo looks clean"
        # reports (see PLF-093 post-mortem). Surface it as its own ticket
        # so the next agent investigates the hang instead of trusting a
        # silent green light.
        return [
            Suggestion(
                signal="pytest_collect_timeout",
                title="pytest collection timed out — investigate hangs",
                description=(
                    f"`pytest --collect-only` did not finish within "
                    f"{timeout_seconds:g}s when invoked from the project "
                    "root. koru scan cannot tell whether the suite is "
                    "healthy or broken — it just hung.\n\n"
                    "Common root causes:\n"
                    "- heavy module-level imports in `conftest.py` "
                    "(database connect, network, model loading) running "
                    "during *collection* instead of inside fixtures;\n"
                    "- a pytest plugin (e.g. pytest-asyncio, pytest-django) "
                    "blocking on a fixture that never resolves;\n"
                    "- unbounded test discovery walking generated/build "
                    "directories — fix with `norecursedirs` or `testpaths`;\n"
                    "- circular imports between sub-packages that pytest "
                    "tries to load as a single rootdir.\n\n"
                    "Reproduce locally:\n"
                    "    timeout 60 python3 -m pytest --collect-only -q\n\n"
                    "If it still hangs, narrow scope:\n"
                    "    pytest --collect-only -q --rootdir=. tests/\n"
                    "    pytest --collect-only -q -p no:asyncio\n\n"
                    "Until this is fixed, `koru scan`'s pytest probe is "
                    "non-actionable: it cannot distinguish a clean repo "
                    "from a broken one."
                ),
                priority="high",
                labels=("ci", "bug", "scan", "timeout"),
            )
        ]
    except (FileNotFoundError, OSError):
        # pytest not installed / not invokable in this environment — that's
        # an environmental gap, not a project bug. Stay silent (the user
        # would not be able to act on it from inside the repo).
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
                    "This blocks the CI gate; resolve before any other ticket.\n\n"
                    f"Raw error context:\n```\n{output[-1000:].strip()}\n```"
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
                        'pythonpath = ["src"]` (or equivalent) in '
                        "`pyproject.toml`, or an editable install missing.\n\n"
                        f"Full traceback snippet:\n```\n{output[-1500:].strip()}\n```"
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


def _load_koruignore_patterns(project: Path) -> tuple[str, ...]:
    """Load optional scan ignore patterns from ``.koruignore``.

    The format is intentionally minimal: one glob pattern per line,
    blank lines and ``#`` comments are ignored.
    """
    ignore_file = project / ".koruignore"
    if not ignore_file.is_file():
        return ()
    try:
        lines = ignore_file.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return ()

    patterns: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("./"):
            line = line[2:]
        elif line.startswith("/"):
            line = line[1:]
        patterns.append(line)
    return tuple(patterns)


def _is_koruignored(rel_path: Path, patterns: Sequence[str]) -> bool:
    """Return ``True`` when ``rel_path`` matches a ``.koruignore`` pattern."""
    if not patterns:
        return False

    rel = rel_path.as_posix()
    basename = rel_path.name
    for pattern in patterns:
        if not pattern:
            continue

        if pattern.endswith("/"):
            prefix = pattern.rstrip("/")
            if rel == prefix or rel.startswith(f"{prefix}/"):
                return True
            continue

        if fnmatch.fnmatch(rel, pattern):
            return True
        # Bare filename patterns should match in any directory.
        if "/" not in pattern and fnmatch.fnmatch(basename, pattern):
            return True

    return False


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
    koruignore_patterns = _load_koruignore_patterns(project)
    walked = 0
    for path in project.rglob("*.py"):
        walked += 1
        if walked > max_files_walked:
            break
        if any(part in _DEFAULT_SCAN_EXCLUDES for part in path.parts):
            continue
        rel_path = path.relative_to(project)
        if _is_koruignored(rel_path, koruignore_patterns):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        n = len(_MARKER_RE.findall(text))
        if n >= min_per_file:
            counts[str(rel_path)] = n
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


def _scan_jscpd_report(project: Path) -> list[Suggestion]:
    path = project / ".jscpd" / "jscpd-report.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    total = (data.get("statistics") or {}).get("total") or {}
    dup_lines = int(total.get("duplicatedLines") or 0)
    if dup_lines <= 0:
        return []
    pct = float(total.get("percentage") or 0)
    clones = int(total.get("clones") or 0)
    rel = str(path.relative_to(project))
    pr = "high" if pct >= 15.0 or dup_lines >= 50_000 else "normal"
    return [
        Suggestion(
            signal="jscpd_report",
            title="Reduce jscpd duplicate-code hotspots (semcod scan)",
            description=(
                f"`{rel}`: {dup_lines} duplicated lines ({pct:.1f}% of scanned LOC), "
                f"{clones} clone groups. Triage largest clones first; re-run jscpd after refactors."
            ),
            priority=pr,
            labels=("quality", "duplication", "jscpd", "scan"),
            files=(rel,),
        )
    ]


_TOON_GOD_RE = re.compile(
    r"^\s*🔴\s+GOD\s+(?P<path>\S+)\s*=\s*(?P<loc>\d+)L,\s*(?P<classes>\d+)\s+classes?,\s*(?P<methods>\d+)m",
    re.MULTILINE,
)
_TOON_CC_RE = re.compile(
    r"^\s*🟡\s+CC\s+(?P<func>\S+)\s+CC=(?P<cc>\d+)\s+\(limit:\s*(?P<limit>\d+)\)",
    re.MULTILINE,
)
_TOON_DUP_RE = re.compile(
    r"^\s*🔴\s+DUP\s+(?P<count>\d+)\s+classes?\s+duplicated",
    re.MULTILINE,
)
_TOON_REFACTOR_ITEM_RE = re.compile(r"^\s*(?P<num>\d+)\.\s+(?P<desc>.+?)\s*\((?P<note>[^)]+)\)\s*$")


def _scan_code2llm_analysis(project: Path) -> list[Suggestion]:
    candidates = (
        project / "project" / "analysis.toon.yaml",
        project / "project" / "analysis.toon",
        project / "analysis.toon.yaml",
    )
    path = next((p for p in candidates if p.is_file()), None)
    if path is None:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    rel = str(path.relative_to(project))

    suggestions: list[Suggestion] = []

    # --- HEALTH: DUP ---
    dup_match = _TOON_DUP_RE.search(text)
    if dup_match:
        count = int(dup_match.group("count"))
        suggestions.append(
            Suggestion(
                signal="code2llm_dup",
                title=f"Remove {count} duplicated classes (code2llm analysis)",
                description=(
                    f"`{rel}` reports **{count}** duplicated classes. "
                    "Extract shared helpers/modules; re-run `code2llm ./ -f toon` to refresh."
                ),
                priority="high",
                labels=("code2llm", "duplication", "refactor", "scan"),
                files=(rel,),
            )
        )

    # --- HEALTH: GOD modules ---
    for m in _TOON_GOD_RE.finditer(text):
        file_path = m.group("path").strip()
        loc = m.group("loc")
        classes = m.group("classes")
        methods = m.group("methods")
        suggestions.append(
            Suggestion(
                signal="code2llm_god",
                title=f"Split god module: {file_path}",
                description=(
                    f"`{rel}` flags `{file_path}` as a god module "
                    f"({loc} lines, {classes} classes, {methods} methods). "
                    "Split into focused submodules by responsibility."
                ),
                priority="high",
                labels=("code2llm", "god-module", "refactor", "scan"),
                files=(file_path, rel),
            )
        )

    # --- HEALTH: high-CC methods ---
    cc_seen: set[str] = set()
    for m in _TOON_CC_RE.finditer(text):
        func = m.group("func").strip()
        cc = int(m.group("cc"))
        limit = int(m.group("limit"))
        if func in cc_seen:
            continue
        cc_seen.add(func)
        suggestions.append(
            Suggestion(
                signal="code2llm_cc",
                title=f"Reduce cyclomatic complexity: {func} (CC={cc}, limit={limit})",
                description=(
                    f"`{rel}` reports `{func}` with CC={cc} (limit={limit}). "
                    "Extract sub-functions, simplify conditionals, or split into strategy pattern."
                ),
                priority="normal",
                labels=("code2llm", "complexity", "refactor", "scan"),
                files=(rel,),
            )
        )

    # --- REFACTOR plan items ---
    in_refactor = False
    for line in text.splitlines():
        if line.startswith("REFACTOR"):
            in_refactor = True
            continue
        if in_refactor and line.startswith(("HEALTH", "PIPELINES", "LAYERS")):
            break
        if not in_refactor:
            continue
        rm = _TOON_REFACTOR_ITEM_RE.match(line)
        if not rm:
            continue
        desc = rm.group("desc").strip()
        note = rm.group("note").strip()
        suggestions.append(
            Suggestion(
                signal="code2llm_refactor",
                title=f"code2llm refactor: {desc}",
                description=(
                    f"REFACTOR item from `{rel}`: **{desc}** ({note}). "
                    "Execute this refactor step; re-run `code2llm ./ -f toon` to verify."
                ),
                priority="normal",
                labels=("code2llm", "refactor", "scan"),
                files=(rel,),
            )
        )

    return suggestions


def _scan_testql_export(project: Path) -> list[Suggestion]:
    path = project / "testql_api_results.json"
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    failed_scenarios = len(re.findall(r"(?m)^❌\s+\S+\.(?:yaml|yml)", text))
    if failed_scenarios < 3:
        return []
    rel = str(path.relative_to(project))
    pr = "high" if failed_scenarios >= 15 else "normal"
    return [
        Suggestion(
            signal="testql_export",
            title="Repair failing TestQL API scenarios (exported log)",
            description=(
                f"`{rel}` shows ~{failed_scenarios} failing scenario(s). "
                "Fix backend routes or refresh generated scenarios; re-export after green runs."
            ),
            priority=pr,
            labels=("testql", "regression", "api", "scan"),
            files=(rel,),
        )
    ]


def _scan_redup_filtered(project: Path) -> list[Suggestion]:
    path = project / ".redup" / "check.filtered.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    groups = data if isinstance(data, list) else data.get("groups") or data.get("clusters")
    if not isinstance(groups, list) or len(groups) < 20:
        return []
    rel = str(path.relative_to(project))
    return [
        Suggestion(
            signal="redup_filtered",
            title="Drive down redup duplicate groups (filtered JSON)",
            description=(
                f"`{rel}` lists {len(groups)} duplicate groups over the hygiene threshold. "
                "Extract shared helpers / modules; re-run `task quality:redup:report`."
            ),
            priority="normal",
            labels=("redup", "duplication", "python", "scan"),
            files=(rel,),
        )
    ]


def scan_semcod_quality_artifacts(project: Path) -> list[Suggestion]:
    """Quality tickets from semcod-adjacent tool exports (jscpd, code2llm, testql, redup)."""
    project = project.resolve()
    out: list[Suggestion] = []
    out.extend(_scan_jscpd_report(project))
    out.extend(_scan_code2llm_analysis(project))
    out.extend(_scan_testql_export(project))
    out.extend(_scan_redup_filtered(project))
    return out


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def collect_suggestions(
    project: Path,
    *,
    skip_pytest: bool = False,
    include_semcod_artifacts: bool = False,
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
    if include_semcod_artifacts:
        out.extend(scan_semcod_quality_artifacts(project))
    return out


# Terminal planfile statuses: scan may re-apply when the signal is still present.
_SCAN_DEDUP_SKIP_STATUSES: frozenset[str] = frozenset(
    {"done", "canceled", "cancelled", "closed"}
)


def _existing_scan_titles(
    project: Path,
    *,
    source: str,
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]] | None = None,
) -> set[str]:
    """Return titles of *active* tickets from previous ``koru scan`` runs.

    Used to deduplicate ``--apply`` runs: re-running ``koru scan --apply``
    should not pile up identical open tickets. Closed tickets (``done``,
    ``canceled``) are ignored so a regressing signal can open a fresh ticket.
    """
    use_runner = runner or default_subprocess_runner

    def _load_titles(cmd: list[str], *, filter_source: bool = False) -> set[str]:
        try:
            result = use_runner(cmd, project)
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
            if not isinstance(entry, dict):
                continue
            if filter_source:
                entry_source = entry.get("source")
                if isinstance(entry_source, dict):
                    if entry_source.get("tool") != source:
                        continue
                elif entry_source != source:
                    continue
            status = str(entry.get("status") or "").lower()
            if status in _SCAN_DEDUP_SKIP_STATUSES:
                continue
            entry_context = entry.get("source", {}).get("context")
            if isinstance(entry_context, dict):
                signal = entry_context.get("signal")
                if isinstance(signal, str) and signal:
                    titles.add(f"signal:{signal}")
            name = entry.get("name") or entry.get("title")
            if isinstance(name, str):
                titles.add(name)
        return titles

    titles = _load_titles(
        ["planfile", "ticket", "list", "--source", source, "--format", "json"],
    )
    if titles:
        return titles
    return _load_titles(
        ["planfile", "ticket", "list", "--format", "json"],
        filter_source=True,
    )


def _create_ticket(
    project: Path,
    suggestion: Suggestion,
    *,
    source: str,
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]] | None = None,
) -> bool:
    """Create one ticket via ``planfile ticket create``. Returns success."""
    if runner is None:
        try:
            create_nl_task(
                project,
                suggestion.description,
                priority=suggestion.priority,
                scaffold={
                    "labels": suggestion.labels,
                    "files": suggestion.files,
                    "title": suggestion.title,
                    "source_tool": source,
                    "source_context": {"signal": suggestion.signal},
                    "executor_kind": "human",
                    "executor_mode": "interactive",
                },
            )
            return True
        except (OSError, ValueError):
            return False

    use_runner = runner or default_subprocess_runner
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
    include_semcod_artifacts: bool | None = None,
    source: str = "koru-scan",
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]] | None = None,
) -> ScanResult:
    """End-to-end scan: collect signals, optionally create planfile tickets."""
    project = project.resolve()
    if include_semcod_artifacts is None:
        include_semcod_artifacts = os.environ.get(
            "KORU_SCAN_SEMCOD_ARTIFACTS", ""
        ).strip().lower() in ("1", "true", "yes", "on")
    suggestions = collect_suggestions(
        project,
        skip_pytest=skip_pytest,
        include_semcod_artifacts=include_semcod_artifacts,
    )
    # Stable ordering: priority (critical > high > normal > low), then signal.
    priority_rank = {"critical": 0, "high": 1, "normal": 2, "low": 3}
    suggestions.sort(key=lambda s: (priority_rank.get(s.priority, 99), s.signal, s.title))
    if limit is not None and limit >= 0:
        suggestions = suggestions[:limit]

    if not apply:
        return ScanResult(suggestions=suggestions)

    existing = _existing_scan_titles(project, source=source, runner=runner)
    applied: list[str] = []
    skipped: list[str] = []
    for s in suggestions:
        if s.title in existing or f"signal:{s.signal}" in existing:
            skipped.append(s.title)
            continue
        ok = _create_ticket(project, s, source=source, runner=runner)
        if ok:
            applied.append(s.title)
            try:
                from .activity_log import activity

                activity(
                    "SCAN",
                    f"ticket ze skanu: {s.title} (priority={s.priority})",
                    preview=s.description,
                )
            except Exception:
                pass
        else:
            skipped.append(s.title)
    return ScanResult(suggestions=suggestions, applied=applied, skipped=skipped)
