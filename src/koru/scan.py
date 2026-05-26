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
  ``analysis.toon*``, **TestQL** text export, optional **redup** JSON, and
  semcod-style reports from **vallm**, **pyqual**, **prefact**, **regix**,
  and **redsl** to open backlog tickets for duplication / refactors /
  validation failures / API regressions.

The output is dry-run by default (a list of :class:`Suggestion`
dataclasses); pass ``apply=True`` to ``run_scan`` to persist them as
planfile tickets through ``planfile ticket create``.
"""


import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
from collections import Counter
from collections.abc import Callable, Sequence
from importlib.util import find_spec
from pathlib import Path
from typing import Any

import yaml

from koru.scan_types import (
    CreateTicketResult,
    ScanResult,
    Suggestion,
)
from koru.scan_types import (
    format_create_exception as _format_create_exception,
)
from koru.semcod_tools import detect_semcod_tools
from koru.tasks import create_nl_task
from koru.utils.subprocess_runner import default_subprocess_runner, get_python_cmd

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
            ),
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
            ),
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
                ),
            )
    return suggestions


_MARKER_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b[: ]")
_DEFAULT_SCAN_EXCLUDES: frozenset[str] = frozenset(
    {
        ".git",
        "__pycache__",
        ".venv",
        ".venv-test",
        "venv",
        "node_modules",
        "build",
        "dist",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".code2llm_cache",
        ".playwright-browsers",
    },
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
            ),
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
            ),
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
        ),
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
        ),
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
_TOON_LAYER_HOTSPOT_RE = re.compile(
    r"^\s*│\s*!!\s+(?P<module>\S+)\s+(?P<loc>\d+)L\s+"
    r"(?P<classes>\d+)C\s+(?P<methods>\d+)m\s+CC=(?P<cc>[0-9.]+)",
    re.MULTILINE,
)


def _find_analysis_file(project: Path) -> tuple[Path | None, str]:
    """Find the code2llm analysis file and return (path, relative_path)."""
    candidates = (
        project / "project" / "analysis.toon.yaml",
        project / "project" / "analysis.toon",
        project / "analysis.toon.yaml",
    )
    path = next((p for p in candidates if p.is_file()), None)
    if path is None:
        return None, ""
    return path, str(path.relative_to(project))


def _file_evidence(project: Path, path: Path, rel: str | None = None) -> dict[str, object]:
    try:
        stat = path.stat()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return {}
    return {
        "path": rel or str(path.relative_to(project)),
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": digest,
    }


def _code2llm_regenerate_command(project: Path) -> str:
    return (
        f"code2llm {project} -f all -o {project / 'project'} --no-chunk "
        "--exclude '*.md' --planfile-apply --planfile-source koru-project-discovery "
        f"--planfile-sprint current --planfile-project {project} --planfile-limit 20"
    )


def _code2llm_source_context(project: Path, analysis_path: Path, rel: str) -> dict[str, object]:
    return {
        "evidence": {
            "schema": "koru.ticket_evidence.v1",
            "kind": "code2llm_analysis",
            "artifact": _file_evidence(project, analysis_path, rel),
            "regenerate_command": _code2llm_regenerate_command(project),
            "staleness_check": (
                "Regenerate the artifact and compare artifact.sha256 before assuming "
                "this ticket still reflects the current code."
            ),
        }
    }


def _with_source_context(suggestion: Suggestion, context: dict[str, object] | None) -> Suggestion:
    if not context:
        return suggestion
    merged = dict(suggestion.source_context)
    merged.update(context)
    return Suggestion(
        signal=suggestion.signal,
        title=suggestion.title,
        description=suggestion.description,
        priority=suggestion.priority,
        labels=suggestion.labels,
        files=suggestion.files,
        source_context=merged,
    )


def _parse_dup_suggestions(
    text: str,
    rel: str,
    *,
    source_context: dict[str, object] | None = None,
) -> list[Suggestion]:
    """Parse duplication suggestions from analysis text."""
    suggestions: list[Suggestion] = []
    dup_match = _TOON_DUP_RE.search(text)
    if dup_match:
        count = int(dup_match.group("count"))
        suggestions.append(
            _with_source_context(
                Suggestion(
                signal="code2llm_dup",
                title=f"Remove {count} duplicated classes (code2llm analysis)",
                description=(
                    f"`{rel}` reports **{count}** duplicated classes. "
                    "Extract shared helpers/modules; re-run the source.context.evidence.regenerate_command to refresh."
                ),
                priority="high",
                labels=("code2llm", "duplication", "refactor", "scan"),
                files=(rel,),
                ),
                source_context,
            ),
        )
    return suggestions


def _parse_god_module_suggestions(
    text: str,
    rel: str,
    *,
    source_context: dict[str, object] | None = None,
) -> list[Suggestion]:
    """Parse god module suggestions from analysis text."""
    suggestions: list[Suggestion] = []
    for m in _TOON_GOD_RE.finditer(text):
        file_path = m.group("path").strip()
        loc = m.group("loc")
        classes = m.group("classes")
        methods = m.group("methods")
        suggestions.append(
            _with_source_context(
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
                ),
                source_context,
            ),
        )
    return suggestions


def _parse_high_cc_suggestions(
    text: str,
    rel: str,
    *,
    source_context: dict[str, object] | None = None,
) -> list[Suggestion]:
    """Parse high-CC method suggestions from analysis text."""
    suggestions: list[Suggestion] = []
    cc_seen: set[str] = set()
    for m in _TOON_CC_RE.finditer(text):
        func = m.group("func").strip()
        cc = int(m.group("cc"))
        limit = int(m.group("limit"))
        if func in cc_seen:
            continue
        cc_seen.add(func)
        suggestions.append(
            _with_source_context(
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
                ),
                source_context,
            ),
        )
    return suggestions


def _parse_refactor_suggestions(
    text: str,
    rel: str,
    *,
    source_context: dict[str, object] | None = None,
) -> list[Suggestion]:
    """Parse refactor item suggestions from analysis text."""
    suggestions: list[Suggestion] = []
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
            _with_source_context(
                Suggestion(
                signal="code2llm_refactor",
                title=f"code2llm refactor: {desc}",
                description=(
                    f"REFACTOR item from `{rel}`: **{desc}** ({note}). "
                    "Execute this refactor step; re-run the source.context.evidence.regenerate_command to verify."
                ),
                priority="normal",
                labels=("code2llm", "refactor", "scan"),
                files=(rel,),
                ),
                source_context,
            ),
        )
    return suggestions


def _parse_layer_hotspot_suggestions(
    text: str,
    rel: str,
    *,
    source_context: dict[str, object] | None = None,
) -> list[Suggestion]:
    """Parse large ``LAYERS`` module rows from newer code2llm output."""
    suggestions: list[Suggestion] = []
    seen: set[str] = set()
    for m in _TOON_LAYER_HOTSPOT_RE.finditer(text):
        module = m.group("module").strip()
        if module in seen:
            continue
        seen.add(module)
        loc = int(m.group("loc"))
        classes = int(m.group("classes"))
        methods = int(m.group("methods"))
        cc = float(m.group("cc"))
        if loc < 500 and cc < 12:
            continue
        priority = "high" if loc >= 800 or cc >= 14 else "normal"
        suggestions.append(
            _with_source_context(
                Suggestion(
                signal="code2llm_layer_hotspot",
                title=f"Split large module: {module}",
                description=(
                    f"`{rel}` flags `{module}` in LAYERS as a large/hot module "
                    f"({loc} lines, {classes} classes, {methods} methods, CC={cc:g}). "
                    "Extract cohesive submodules around stable responsibilities and add "
                    "focused regression tests before broad edits."
                ),
                priority=priority,
                labels=("code2llm", "architecture", "large-module", "refactor", "scan"),
                files=(rel,),
                ),
                source_context,
            ),
        )
        if len(suggestions) >= 5:
            break
    return suggestions


def _scan_code2llm_analysis(project: Path) -> list[Suggestion]:
    path, rel = _find_analysis_file(project)
    if path is None:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    source_context = _code2llm_source_context(project, path, rel)
    suggestions: list[Suggestion] = []
    suggestions.extend(_parse_dup_suggestions(text, rel, source_context=source_context))
    suggestions.extend(_parse_god_module_suggestions(text, rel, source_context=source_context))
    suggestions.extend(_parse_high_cc_suggestions(text, rel, source_context=source_context))
    suggestions.extend(_parse_refactor_suggestions(text, rel, source_context=source_context))
    suggestions.extend(_parse_layer_hotspot_suggestions(text, rel, source_context=source_context))
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
        ),
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
        ),
    ]


def _scan_redup_changed(project: Path) -> list[Suggestion]:
    path = project / ".redup" / "wup-changed.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    groups = data if isinstance(data, list) else data.get("groups") or data.get("clusters")
    if not isinstance(groups, list) or not groups:
        return []
    rel = str(path.relative_to(project))
    return [
        Suggestion(
            signal="redup_changed",
            title="Review duplicate groups touching recent changes",
            description=(
                f"`{rel}` lists {len(groups)} duplicate group(s) from the WUP/on-change "
                "redup scan. Triage these before running a full duplicate budget gate."
            ),
            priority="normal",
            labels=("redup", "duplication", "wup", "scan"),
            files=(rel,),
        ),
    ]


def _first_existing_artifact(project: Path, candidates: Sequence[str]) -> tuple[Path, str] | None:
    for candidate in candidates:
        path = project / candidate
        if path.is_file():
            return path, candidate
    return None


def _load_structured_artifact(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    if path.suffix.lower() == ".json":
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError:
        return None


def _intish(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"failed", "fail", "error", "errors", "red", "critical"}:
            return 1
        try:
            return int(float(text))
        except ValueError:
            return 0
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return len(value)
    return 0


def _sum_structured_counts(data: object, keys: frozenset[str]) -> int:
    """Best-effort issue counter for small semcod JSON/YAML reports."""
    if isinstance(data, dict):
        total = 0
        for key, value in data.items():
            key_text = str(key).lower().replace("-", "_")
            if key_text in keys:
                total += _intish(value)
            elif key_text == "status" and str(value).strip().lower() in {
                "failed",
                "failure",
                "error",
                "red",
            }:
                total += 1
            else:
                total += _sum_structured_counts(value, keys)
        return total
    if isinstance(data, list):
        return sum(_sum_structured_counts(item, keys) for item in data)
    return 0


def _scan_vallm_validation(project: Path) -> list[Suggestion]:
    found = _first_existing_artifact(
        project,
        (
            "validation.toon.yaml",
            "project/validation.toon.yaml",
            "vallm-validation.toon.yaml",
            "vallm-report.yaml",
            ".vallm/report.yaml",
        ),
    )
    if found is None:
        return []
    path, rel = found
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    errors = 0
    warnings = 0
    err_match = re.search(r"(?m)^\s*ERRORS\[(?P<count>\d+)\]", text)
    warn_match = re.search(r"(?m)^\s*WARNINGS\[(?P<count>\d+)\]", text)
    if err_match:
        errors = int(err_match.group("count"))
    if warn_match:
        warnings = int(warn_match.group("count"))
    if errors <= 0 and warnings < 10:
        return []
    priority = "high" if errors > 0 else "normal"
    return [
        Suggestion(
            signal="vallm_validation",
            title="Repair VALLM validation findings",
            description=(
                f"`{rel}` reports {errors} error(s) and {warnings} warning(s). "
                "Fix the highest-impact validation failures first, then re-run "
                "`vallm validate` / the project validation task and refresh the report."
            ),
            priority=priority,
            labels=("vallm", "validation", "scan"),
            files=(rel,),
        ),
    ]


def _scan_structured_semcod_report(
    project: Path,
    *,
    candidates: Sequence[str],
    signal: str,
    title: str,
    command_hint: str,
    labels: tuple[str, ...],
    keys: frozenset[str],
    high_threshold: int = 10,
) -> list[Suggestion]:
    found = _first_existing_artifact(project, candidates)
    if found is None:
        return []
    path, rel = found
    data = _load_structured_artifact(path)
    if data is None:
        return []
    count = _sum_structured_counts(data, keys)
    if count <= 0:
        return []
    priority = "high" if count >= high_threshold else "normal"
    return [
        Suggestion(
            signal=signal,
            title=title,
            description=(
                f"`{rel}` reports {count} actionable finding(s). "
                f"Triage and repair the report findings, then re-run `{command_hint}` "
                "and refresh the artifact before closing the ticket."
            ),
            priority=priority,
            labels=labels,
            files=(rel,),
        ),
    ]


def _scan_pyqual_report(project: Path) -> list[Suggestion]:
    return _scan_structured_semcod_report(
        project,
        candidates=(
            ".pyqual/report.json",
            ".pyqual/report.yaml",
            "pyqual-report.json",
            "pyqual-report.yaml",
            "quality-report.yaml",
        ),
        signal="pyqual_report",
        title="Repair PyQual quality findings",
        command_hint="pyqual check",
        labels=("pyqual", "quality", "scan"),
        keys=frozenset(
            {
                "failed",
                "failures",
                "failed_checks",
                "errors",
                "issues",
                "violations",
                "findings",
            },
        ),
    )


def _scan_prefact_report(project: Path) -> list[Suggestion]:
    return _scan_structured_semcod_report(
        project,
        candidates=(
            ".prefact/report.json",
            ".prefact/results.json",
            "prefact-report.json",
            "prefact-results.json",
        ),
        signal="prefact_report",
        title="Resolve Prefact pre-refactor findings",
        command_hint="prefact check",
        labels=("prefact", "refactor", "quality", "scan"),
        keys=frozenset(
            {
                "failed",
                "failures",
                "errors",
                "issues",
                "findings",
                "violations",
                "blocking",
            },
        ),
    )


def _scan_regix_report(project: Path) -> list[Suggestion]:
    return _scan_structured_semcod_report(
        project,
        candidates=(
            ".regix/report.json",
            ".regix/gates.json",
            "regix-report.json",
            "regix-gates.json",
        ),
        signal="regix_report",
        title="Repair Regix regression gate findings",
        command_hint="regix gates",
        labels=("regix", "regression", "scan"),
        keys=frozenset(
            {
                "failed",
                "failures",
                "failed_gates",
                "regressions",
                "errors",
                "violations",
            },
        ),
    )


def _scan_redsl_report(project: Path) -> list[Suggestion]:
    return _scan_structured_semcod_report(
        project,
        candidates=(
            ".redsl/report.json",
            ".redsl/gate.json",
            "redsl-report.json",
            "redsl-report.yaml",
            "redsl-gate.json",
        ),
        signal="redsl_report",
        title="Repair RedSL gate findings",
        command_hint="redsl gate check .",
        labels=("redsl", "gate", "scan"),
        keys=frozenset(
            {
                "failed",
                "failures",
                "errors",
                "issues",
                "findings",
                "violations",
                "regressions",
            },
        ),
    )


def scan_semcod_quality_artifacts(project: Path) -> list[Suggestion]:
    """Quality tickets from semcod-adjacent tool exports."""
    project = project.resolve()
    out: list[Suggestion] = []
    out.extend(_scan_jscpd_report(project))
    out.extend(_scan_code2llm_analysis(project))
    out.extend(_scan_testql_export(project))
    out.extend(_scan_redup_filtered(project))
    out.extend(_scan_redup_changed(project))
    out.extend(_scan_vallm_validation(project))
    out.extend(_scan_pyqual_report(project))
    out.extend(_scan_prefact_report(project))
    out.extend(_scan_regix_report(project))
    out.extend(_scan_redsl_report(project))
    return out


def _normalize_scan_filter_path(path: str | Path) -> str:
    text = str(path).strip().replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text.rstrip("/")


def _matches_scan_filter(value: str, wanted: str) -> bool:
    value = _normalize_scan_filter_path(value)
    if not value or not wanted:
        return False
    return value == wanted or value.startswith(f"{wanted}/") or wanted in value


def _suggestion_matches_paths(suggestion: Suggestion, paths: Sequence[str | Path]) -> bool:
    wanted_paths = tuple(
        path for path in (_normalize_scan_filter_path(item) for item in paths) if path
    )
    if not wanted_paths:
        return True
    haystack = [*suggestion.files, suggestion.title, suggestion.description]
    return any(
        _matches_scan_filter(str(value), wanted)
        for value in haystack
        for wanted in wanted_paths
    )


def _filter_suggestions_by_paths(
    suggestions: list[Suggestion],
    paths: Sequence[str | Path] | None,
) -> list[Suggestion]:
    if not paths:
        return suggestions
    return [item for item in suggestions if _suggestion_matches_paths(item, paths)]


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def collect_suggestions(
    project: Path,
    *,
    skip_pytest: bool = False,
    include_semcod_artifacts: bool = False,
    paths: Sequence[str | Path] | None = None,
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
    return _filter_suggestions_by_paths(out, paths)


def _record_scan_activity(
    message: str,
    *,
    preview: str | None = None,
    data: dict[str, Any] | None = None,
) -> None:
    """Best-effort activity event for scan decisions."""
    try:
        from koru.activity_log import activity

        activity("SCAN", message, preview=preview, data=data)
    except Exception:
        pass


# Terminal planfile statuses: scan may re-apply when the signal is still present.
_SCAN_DEDUP_SKIP_STATUSES: frozenset[str] = frozenset(
    {"done", "canceled", "cancelled", "closed"},
)


def _add_existing_scan_title_keys(titles: set[str], entry: object, *, source: str) -> None:
    if not isinstance(entry, dict):
        return
    entry_source = entry.get("source")
    if isinstance(entry_source, dict):
        if entry_source.get("tool") != source:
            return
    elif entry_source != source:
        return
    status = str(entry.get("status") or "").lower()
    if status in _SCAN_DEDUP_SKIP_STATUSES:
        return
    entry_context = entry_source.get("context") if isinstance(entry_source, dict) else None
    if isinstance(entry_context, dict):
        signal = entry_context.get("signal")
        if isinstance(signal, str) and signal:
            titles.add(f"signal:{signal}")
    name = entry.get("name") or entry.get("title")
    if isinstance(name, str):
        titles.add(name)


def _add_active_scan_title_keys(titles: set[str], entry: object) -> None:
    if not isinstance(entry, dict):
        return
    status = str(entry.get("status") or "").lower()
    if status in _SCAN_DEDUP_SKIP_STATUSES:
        return
    entry_context = entry.get("source", {}).get("context")
    if isinstance(entry_context, dict):
        signal = entry_context.get("signal")
        if isinstance(signal, str) and signal:
            titles.add(f"signal:{signal}")
    name = entry.get("name") or entry.get("title")
    if isinstance(name, str):
        titles.add(name)


def _existing_scan_titles_from_sprint(project: Path, *, source: str) -> set[str]:
    sprint_path = project / ".planfile" / "sprints" / "current.yaml"
    try:
        data = yaml.safe_load(sprint_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return set()
    sprint = data.get("sprint") if isinstance(data, dict) else None
    tickets = sprint.get("tickets") if isinstance(sprint, dict) else None
    if isinstance(tickets, dict):
        entries = tickets.values()
    elif isinstance(tickets, list):
        entries = tickets
    else:
        return set()
    titles: set[str] = set()
    for entry in entries:
        _add_existing_scan_title_keys(titles, entry, source=source)
    return titles


def _scan_ticket_list_payload(
    project: Path,
    cmd: list[str],
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]],
) -> list[Any]:
    try:
        result = runner(cmd, project)
    except (FileNotFoundError, OSError):
        return []
    if result.returncode != 0:
        return []
    try:
        payload = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return []
    return payload if isinstance(payload, list) else []


def _existing_scan_titles_from_payload(
    payload: list[Any],
    *,
    source: str,
    filter_source: bool = False,
) -> set[str]:
    titles: set[str] = set()
    for entry in payload:
        if filter_source:
            _add_existing_scan_title_keys(titles, entry, source=source)
            continue
        _add_active_scan_title_keys(titles, entry)
    return titles


def _load_existing_scan_titles(
    project: Path,
    cmd: list[str],
    *,
    source: str,
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]],
    filter_source: bool = False,
) -> set[str]:
    payload = _scan_ticket_list_payload(project, cmd, runner)
    return _existing_scan_titles_from_payload(
        payload,
        source=source,
        filter_source=filter_source,
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
    if runner is None:
        titles = _existing_scan_titles_from_sprint(project, source=source)
        if titles:
            return titles

    use_runner = runner or default_subprocess_runner
    titles = _load_existing_scan_titles(
        project,
        ["planfile", "ticket", "list", "--source", source, "--format", "json"],
        source=source,
        runner=use_runner,
    )
    if titles:
        return titles
    return _load_existing_scan_titles(
        project,
        ["planfile", "ticket", "list", "--format", "json"],
        source=source,
        runner=use_runner,
        filter_source=True,
    )


def _create_ticket(
    project: Path,
    suggestion: Suggestion,
    *,
    source: str,
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]] | None = None,
) -> CreateTicketResult:
    """Create one ticket via ``planfile ticket create``."""
    if runner is None:
        try:
            created = create_nl_task(
                project,
                suggestion.description,
                priority=suggestion.priority,
                scaffold={
                    "labels": suggestion.labels,
                    "files": suggestion.files,
                    "title": suggestion.title,
                    "source_tool": source,
                    "source_context": {
                        "signal": suggestion.signal,
                        "dedupe_key": _suggestion_dedupe_key(source, suggestion),
                        **suggestion.source_context,
                    },
                    "executor_kind": "human",
                    "executor_mode": "interactive",
                },
            )
            if getattr(created, "reused", False):
                return CreateTicketResult(ok=False, detail="task already exists (reused)")
            return CreateTicketResult(ok=True)
        except Exception as exc:
            return CreateTicketResult(ok=False, detail=_format_create_exception(exc))

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
    except (FileNotFoundError, OSError) as exc:
        return CreateTicketResult(ok=False, detail=_format_create_exception(exc))
    if result.returncode == 0:
        return CreateTicketResult(ok=True)
    detail = (result.stderr or result.stdout or "").strip()
    return CreateTicketResult(ok=False, detail=detail)


def _suggestion_dedupe_key(source: str, suggestion: Suggestion) -> str:
    """Return a stable producer-neutral key for repeated scan signals."""
    files = [str(path) for path in suggestion.files if str(path).strip()]
    if not files:
        files = re.findall(
            r"(?:src|tests|scripts|plugins|services)/[A-Za-z0-9_./-]+",
            suggestion.title,
        )
    if suggestion.signal in {"code2llm_god", "code2llm_refactor"} and files:
        return f"semcod:code2llm:refactor:{files[0]}"
    if files:
        return f"{source}:{suggestion.signal}:{':'.join(files[:3])}"
    return f"{source}:{suggestion.signal}:{suggestion.title.strip().lower()}"


def _is_reused_create_detail(detail: str) -> bool:
    normalized = detail.strip().lower()
    return "reused" in normalized or "already exists" in normalized


def _log_scan_decision(
    suggestion: Suggestion,
    *,
    decision: str,
    reason: str | None,
    message: str,
) -> None:
    payload: dict[str, Any] = {
        "decision": decision,
        "signal": suggestion.signal,
        "title": suggestion.title,
        "priority": suggestion.priority,
    }
    if reason is not None:
        payload["reason"] = reason
    _record_scan_activity(
        message,
        preview=suggestion.description,
        data=payload,
    )


def _scan_duplicate_skip(
    suggestion: Suggestion,
    existing: set[str],
) -> tuple[str, str] | None:
    if suggestion.title in existing:
        return (
            "duplicate_title",
            f"pomijam ze skanu (duplikat tytułu): {suggestion.title} "
            f"(signal={suggestion.signal})",
        )
    if f"signal:{suggestion.signal}" in existing:
        return (
            "duplicate_signal",
            f"pomijam ze skanu (duplikat sygnału): {suggestion.title} "
            f"(signal={suggestion.signal} — istnieje aktywny ticket dla tego sygnału)",
        )
    return None


def _normalize_create_detail(detail: str) -> str:
    detail = (detail or "").strip()
    return detail.replace("\n", " ") if detail else ""


def _apply_create_result(
    suggestion: Suggestion,
    create_result: CreateTicketResult,
    *,
    applied: list[str],
    skipped: list[str],
    skipped_as_duplicate: list[str],
    skipped_create_failed: list[str],
    skipped_create_failed_details: list[str],
) -> None:
    if create_result.ok:
        applied.append(suggestion.title)
        _log_scan_decision(
            suggestion,
            decision="applied",
            reason=None,
            message=f"ticket ze skanu: {suggestion.title} (priority={suggestion.priority})",
        )
        return

    skipped.append(suggestion.title)
    detail = _normalize_create_detail(create_result.detail or "")
    if detail and _is_reused_create_detail(detail):
        skipped_as_duplicate.append(suggestion.title)
        _log_scan_decision(
            suggestion,
            decision="skipped",
            reason="duplicate_reused",
            message=(
                f"pomijam ze skanu (ticket już istnieje / reused): {suggestion.title} "
                f"(signal={suggestion.signal} — {detail[:180]})"
            ),
        )
        return

    skipped_create_failed.append(suggestion.title)
    if detail:
        skipped_create_failed_details.append(f"{suggestion.title}: {detail[:240]}")
    fallback_hint = " — sprawdź `.planfile/` uprawnienia/lock"
    _log_scan_decision(
        suggestion,
        decision="skipped",
        reason="create_failed",
        message=(
            f"pomijam ze skanu (planfile odrzucił create): {suggestion.title} "
            f"(signal={suggestion.signal}"
            + (f" — {detail[:180]}" if detail else fallback_hint)
            + ")"
        ),
    )


def _apply_scan_suggestions(
    project: Path,
    suggestions: list[Suggestion],
    *,
    source: str,
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]] | None,
) -> ScanResult:
    existing = _existing_scan_titles(project, source=source, runner=runner)
    applied: list[str] = []
    skipped: list[str] = []
    skipped_as_duplicate: list[str] = []
    skipped_create_failed: list[str] = []
    skipped_create_failed_details: list[str] = []

    for suggestion in suggestions:
        duplicate = _scan_duplicate_skip(suggestion, existing)
        if duplicate is not None:
            reason, message = duplicate
            skipped.append(suggestion.title)
            skipped_as_duplicate.append(suggestion.title)
            _log_scan_decision(suggestion, decision="skipped", reason=reason, message=message)
            continue

        create_result = _create_ticket(project, suggestion, source=source, runner=runner)
        _apply_create_result(
            suggestion,
            create_result,
            applied=applied,
            skipped=skipped,
            skipped_as_duplicate=skipped_as_duplicate,
            skipped_create_failed=skipped_create_failed,
            skipped_create_failed_details=skipped_create_failed_details,
        )

    return ScanResult(
        suggestions=suggestions,
        applied=applied,
        skipped=skipped,
        skipped_as_duplicate=skipped_as_duplicate,
        skipped_create_failed=skipped_create_failed,
        skipped_create_failed_details=skipped_create_failed_details,
    )


def run_scan(
    project: Path,
    *,
    apply: bool = False,
    limit: int | None = None,
    skip_pytest: bool = False,
    include_semcod_artifacts: bool | None = None,
    paths: Sequence[str | Path] | None = None,
    source: str = "koru-scan",
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]] | None = None,
) -> ScanResult:
    """End-to-end scan: collect signals, optionally create planfile tickets."""
    project = project.resolve()
    if include_semcod_artifacts is None:
        include_semcod_artifacts = os.environ.get(
            "KORU_SCAN_SEMCOD_ARTIFACTS",
            "",
        ).strip().lower() in ("1", "true", "yes", "on")
    suggestions = collect_suggestions(
        project,
        skip_pytest=skip_pytest,
        include_semcod_artifacts=include_semcod_artifacts,
        paths=paths,
    )
    # Stable ordering: priority (critical > high > normal > low), then signal.
    priority_rank = {"critical": 0, "high": 1, "normal": 2, "low": 3}
    suggestions.sort(key=lambda s: (priority_rank.get(s.priority, 99), s.signal, s.title))
    if limit is not None and limit >= 0:
        suggestions = suggestions[:limit]

    if not apply:
        return ScanResult(suggestions=suggestions)

    return _apply_scan_suggestions(project, suggestions, source=source, runner=runner)
