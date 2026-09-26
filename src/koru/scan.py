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
  **redsl**, **metrun**, and **pfix** diagnose exports to open backlog tickets for
  duplication / refactors / validation failures / API regressions / performance
  hotspots / environment blockers.

The output is dry-run by default (a list of :class:`Suggestion`
dataclasses); pass ``apply=True`` to ``run_scan`` to persist them as
planfile tickets through ``planfile ticket create``.
"""

import os
import re
import shutil
import subprocess
from collections.abc import Callable, Sequence
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from koru.fleet_admission import scan_admission
from koru.scan_artifacts import (
    _ANALYSIS_ARTIFACT_PATHS as _ANALYSIS_ARTIFACT_PATHS,  # noqa: F401
)
from koru.scan_artifacts import (
    _CALLS_ARTIFACT_PATHS as _CALLS_ARTIFACT_PATHS,  # noqa: F401
)
from koru.scan_artifacts import (
    _PLANFILE_TICKETS_ARTIFACT_PATHS as _PLANFILE_TICKETS_ARTIFACT_PATHS,  # noqa: F401
)
from koru.scan_artifacts import (
    _code2llm_cc_locations as _code2llm_cc_locations,  # noqa: F401
)
from koru.scan_artifacts import (
    _code2llm_module_paths as _code2llm_module_paths,  # noqa: F401
)
from koru.scan_artifacts import (
    _find_analysis_file as _find_analysis_file,  # noqa: F401
)
from koru.scan_artifacts import (
    _first_existing_artifact as _first_existing_artifact,  # noqa: F401
)
from koru.scan_artifacts import (
    _load_yaml_mapping as _load_yaml_mapping,  # noqa: F401
)
from koru.scan_artifacts import (
    _scan_code2llm_analysis as _scan_code2llm_analysis,  # noqa: F401
)
from koru.scan_artifacts import (
    _scan_jscpd_report as _scan_jscpd_report,  # noqa: F401
)
from koru.scan_artifacts import (
    _scan_metrun_report as _scan_metrun_report,  # noqa: F401
)
from koru.scan_artifacts import (
    _scan_pfix_report as _scan_pfix_report,  # noqa: F401
)
from koru.scan_artifacts import (
    _scan_prefact_report as _scan_prefact_report,  # noqa: F401
)
from koru.scan_artifacts import (
    _scan_pyqual_report as _scan_pyqual_report,  # noqa: F401
)
from koru.scan_artifacts import (
    _scan_redsl_report as _scan_redsl_report,  # noqa: F401
)
from koru.scan_artifacts import (
    _scan_redup_changed as _scan_redup_changed,  # noqa: F401
)
from koru.scan_artifacts import (
    _scan_redup_filtered as _scan_redup_filtered,  # noqa: F401
)
from koru.scan_artifacts import (
    _scan_regix_report as _scan_regix_report,  # noqa: F401
)
from koru.scan_artifacts import (
    _scan_structured_semcod_report as _scan_structured_semcod_report,  # noqa: F401
)
from koru.scan_artifacts import (
    _scan_testql_export as _scan_testql_export,  # noqa: F401
)
from koru.scan_artifacts import (
    _scan_todo2code_plans as _scan_todo2code_plans,  # noqa: F401
)
from koru.scan_artifacts import (
    _scan_vallm_validation as _scan_vallm_validation,  # noqa: F401
)
from koru.scan_artifacts import (
    _should_skip_code2llm_dup_ticket as _should_skip_code2llm_dup_ticket,  # noqa: F401
)
from koru.scan_artifacts import (
    scan_semcod_quality_artifacts,
)
from koru.scan_collection import collect_suggestions as _collect_suggestions_impl
from koru.scan_dedupe_policy import (
    SCAN_DEDUP_SKIP_STATUSES as _SCAN_DEDUP_SKIP_STATUSES_IMPL,
)
from koru.scan_dedupe_policy import (
    add_active_scan_title_keys as _add_active_scan_title_keys_impl,
)
from koru.scan_dedupe_policy import (
    add_existing_scan_title_keys as _add_existing_scan_title_keys_impl,
)
from koru.scan_dedupe_policy import (
    existing_scan_titles as _existing_scan_titles_impl,
)
from koru.scan_dedupe_policy import (
    existing_scan_titles_from_payload as _existing_scan_titles_from_payload_impl,
)
from koru.scan_dedupe_policy import (
    existing_scan_titles_from_sprint as _existing_scan_titles_from_sprint_impl,
)
from koru.scan_dedupe_policy import (
    load_existing_scan_titles as _load_existing_scan_titles_impl,
)
from koru.scan_dedupe_policy import (
    scan_duplicate_skip as _scan_duplicate_skip_impl,
)
from koru.scan_dedupe_policy import (
    scan_ticket_list_payload as _scan_ticket_list_payload_impl,
)
from koru.scan_ticket_emission import (
    apply_create_result as _apply_create_result_impl,
)
from koru.scan_ticket_emission import (
    apply_scan_suggestions as _apply_scan_suggestions_impl,
)
from koru.scan_ticket_emission import create_ticket as _create_ticket_impl
from koru.scan_ticket_emission import (
    is_reused_create_detail as _is_reused_create_detail_impl,
)
from koru.scan_ticket_emission import (
    log_scan_decision as _log_scan_decision_impl,
)
from koru.scan_ticket_emission import (
    normalize_create_detail as _normalize_create_detail_impl,
)
from koru.scan_todo import (
    DEFAULT_SCAN_EXCLUDES as _DEFAULT_SCAN_EXCLUDES,
)
from koru.scan_todo import (
    scan_todo_markers as scan_todo_markers,
)
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
    timeout_seconds: float = 60.0,
) -> list[Suggestion]:
    """Probe pytest collection; surface every collection failure as a ticket.

    The default budget covers a cold collection of this repository's
    ~4400-test suite (~40s with no bytecode cache); the governance bridge
    is disabled for the probe, so the budget measures collection only.
    """
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
    # ``--collect-only`` is a read-only inventory probe. The managed
    # ``wellmanifest_governance`` bridge runs the full governance-check
    # subprocess at session start (~25s on this host) and aborts collection
    # with an INTERNALERROR when the checkout is dirty — neither helps a
    # collection probe inside a 30s budget, so the plugin stays off here.
    # ``-p no:`` is a no-op for projects that never loaded the plugin.
    cmd = get_python_cmd(project) + [
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        "--no-header",
        "-p",
        "no:wellmanifest_governance",
    ]
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


_GATE_MARKERS: tuple[tuple[str, str, str], ...] = (
    ("wup", "wup.yaml", "intelligent file watcher (3-layer: detect → quick → full)"),
    ("regix", "regix.yaml", "regression metrics gate (CC / MI / coverage delta)"),
    (
        "testql",
        "testql-scenarios",
        "behavioural HTTP probes (TOON YAML scenarios)",
    ),
)


def _is_workspace_root(project: Path) -> bool:
    """True when *project* is a multi-project workspace, not a single package.

    A workspace root has no packaging file of its own (``pyproject.toml`` /
    ``setup.py`` / ``setup.cfg``) yet contains several sub-projects that each
    carry one. On-change gates belong in those sub-projects — each self-gates —
    so a single root ``regix.yaml`` / ``wup.yaml`` would gate all of them at
    once, which is never what a monorepo wants. Skipping keeps koru from
    re-suggesting root gate bootstraps every scan (semcod: 66 sub-projects,
    STARTER-005/006/007).
    """
    if any((project / f).exists() for f in ("pyproject.toml", "setup.py", "setup.cfg")):
        return False
    child_pkgs = 0
    for child in project.iterdir():
        if not child.is_dir() or child.name in _DEFAULT_SCAN_EXCLUDES:
            continue
        if (child / "pyproject.toml").exists() or (child / "setup.py").exists():
            child_pkgs += 1
            if child_pkgs >= 2:
                return True
    return False


def scan_missing_gates(project: Path) -> list[Suggestion]:
    """Suggest bootstrap tickets for unconfigured on-change gates."""
    if _is_workspace_root(project):
        return []
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
    wanted_paths = tuple(path for path in (_normalize_scan_filter_path(item) for item in paths) if path)
    if not wanted_paths:
        return True
    haystack = [*suggestion.files, suggestion.title, suggestion.description]
    return any(_matches_scan_filter(str(value), wanted) for value in haystack for wanted in wanted_paths)


def _filter_suggestions_by_paths(
    suggestions: list[Suggestion],
    paths: Sequence[str | Path] | None,
) -> list[Suggestion]:
    if not paths:
        return suggestions
    return [item for item in suggestions if _suggestion_matches_paths(item, paths)]


def resolve_scan_paths(
    project: Path,
    *,
    explicit_paths: Sequence[str | Path] | None = None,
    from_env: bool = True,
) -> tuple[str, ...] | None:
    """Merge CLI/env path filters for scoped semcod intake and discovery."""
    merged: list[str] = []
    if from_env:
        raw = os.environ.get("KORU_SCAN_PATHS", "").strip()
        if raw:
            for part in re.split(r"[:,]+", raw):
                normalized = _normalize_scan_filter_path(part)
                if normalized:
                    merged.append(normalized)
    if explicit_paths:
        for item in explicit_paths:
            normalized = _normalize_scan_filter_path(item)
            if normalized:
                merged.append(normalized)
    deduped = tuple(dict.fromkeys(merged))
    return deduped or None


def resolve_code2llm_source(project: Path, scope_paths: Sequence[str] | None) -> Path:
    """Pick a code2llm source root when a single scoped path is requested."""
    project = project.resolve()
    if scope_paths and len(scope_paths) == 1:
        candidate = project / _normalize_scan_filter_path(scope_paths[0])
        if candidate.exists():
            return candidate.resolve()
    return project


def apply_scan_path_environ(paths: Sequence[str | Path] | None) -> None:
    """Publish scoped scan paths for autonomous cycles via ``KORU_SCAN_PATHS``."""
    if not paths:
        return
    normalized = [item for item in (_normalize_scan_filter_path(part) for part in paths) if item]
    if normalized:
        os.environ["KORU_SCAN_PATHS"] = ":".join(normalized)


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
    return _collect_suggestions_impl(
        project,
        skip_pytest=skip_pytest,
        include_semcod_artifacts=include_semcod_artifacts,
        paths=paths,
        scan_pytest_collect=scan_pytest_collect,
        scan_todo_markers=scan_todo_markers,
        scan_missing_gates=scan_missing_gates,
        scan_missing_tools=scan_missing_tools,
        scan_gitignore_drift=scan_gitignore_drift,
        scan_semcod_quality_artifacts=scan_semcod_quality_artifacts,
        filter_suggestions_by_paths=_filter_suggestions_by_paths,
    )


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


# Terminal Planfile entries suppress only identical evidence-bound findings.
_SCAN_DEDUP_SKIP_STATUSES: frozenset[str] = frozenset(
    _SCAN_DEDUP_SKIP_STATUSES_IMPL,
)


def _add_existing_scan_title_keys(titles: set[str], entry: object, *, source: str) -> None:
    _add_existing_scan_title_keys_impl(titles, entry, source=source)


def _add_active_scan_title_keys(titles: set[str], entry: object) -> None:
    _add_active_scan_title_keys_impl(titles, entry)


def _existing_scan_titles_from_sprint(project: Path, *, source: str) -> set[str]:
    return _existing_scan_titles_from_sprint_impl(project, source=source)


def _scan_ticket_list_payload(
    project: Path,
    cmd: list[str],
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]],
) -> list[Any]:
    return _scan_ticket_list_payload_impl(project, cmd, runner)


def _existing_scan_titles_from_payload(
    payload: list[Any],
    *,
    source: str,
    filter_source: bool = False,
) -> set[str]:
    return _existing_scan_titles_from_payload_impl(
        payload,
        source=source,
        filter_source=filter_source,
    )


def _load_existing_scan_titles(
    project: Path,
    cmd: list[str],
    *,
    source: str,
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]],
    filter_source: bool = False,
) -> set[str]:
    return _load_existing_scan_titles_impl(
        project,
        cmd,
        source=source,
        runner=runner,
        filter_source=filter_source,
    )


def _existing_scan_titles(
    project: Path,
    *,
    source: str,
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]] | None = None,
) -> set[str]:
    """Return active legacy keys and evidence-bound historical scan keys.

    Used to deduplicate ``--apply`` runs: re-running ``koru scan --apply``
    should not pile up identical open tickets or recreate an unchanged finding
    after archival. A terminal ticket is authoritative only when producer,
    dedupe key and evidence fingerprint all match; changed evidence remains a
    fresh regression.
    """
    return _existing_scan_titles_impl(
        project,
        source=source,
        runner=runner,
        default_runner=default_subprocess_runner,
        sprint_loader=lambda project_path, src: _existing_scan_titles_from_sprint(
            project_path,
            source=src,
        ),
    )


def _create_ticket(
    project: Path,
    suggestion: Suggestion,
    *,
    source: str,
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]] | None = None,
) -> CreateTicketResult:
    """Create one ticket via ``planfile ticket create``."""
    return _create_ticket_impl(
        project,
        suggestion,
        source=source,
        runner=runner,
        create_nl_task=create_nl_task,
        format_create_exception=_format_create_exception,
        suggestion_dedupe_key=_suggestion_dedupe_key,
        default_runner=default_subprocess_runner,
    )


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
    return _is_reused_create_detail_impl(detail)


def _log_scan_decision(
    suggestion: Suggestion,
    *,
    decision: str,
    reason: str | None,
    message: str,
) -> None:
    _log_scan_decision_impl(
        suggestion,
        decision=decision,
        reason=reason,
        message=message,
        record_scan_activity=_record_scan_activity,
    )


def _scan_duplicate_skip(
    suggestion: Suggestion,
    existing: set[str],
    *,
    source: str | None = None,
) -> tuple[str, str] | None:
    return _scan_duplicate_skip_impl(
        suggestion,
        existing,
        source=source,
        suggestion_dedupe_key=_suggestion_dedupe_key if source is not None else None,
    )


def _normalize_create_detail(detail: str) -> str:
    return _normalize_create_detail_impl(detail)


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
    _apply_create_result_impl(
        suggestion,
        create_result,
        applied=applied,
        skipped=skipped,
        skipped_as_duplicate=skipped_as_duplicate,
        skipped_create_failed=skipped_create_failed,
        skipped_create_failed_details=skipped_create_failed_details,
        log_scan_decision=_log_scan_decision,
        is_reused_create_detail=_is_reused_create_detail,
        normalize_create_detail=_normalize_create_detail,
    )


def _apply_scan_suggestions(
    project: Path,
    suggestions: list[Suggestion],
    *,
    source: str,
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]] | None,
) -> ScanResult:
    return _apply_scan_suggestions_impl(
        project,
        suggestions,
        source=source,
        runner=runner,
        existing_scan_titles=_existing_scan_titles,
        scan_duplicate_skip=lambda suggestion, existing: _scan_duplicate_skip(
            suggestion,
            existing,
            source=source,
        ),
        create_ticket=_create_ticket,
        apply_create_result=_apply_create_result,
        log_scan_decision=_log_scan_decision,
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

    admission = scan_admission(project)
    if admission is not None and not admission["admit_new"]:
        return ScanResult(suggestions=suggestions, skipped=[s.title for s in suggestions], fleet_admission=admission)
    # A single observation cannot authorize a batch of newly queued tickets.
    selected = suggestions[:1] if admission is not None else suggestions
    result = _apply_scan_suggestions(project, selected, source=source, runner=runner)
    if admission is None:
        return result
    from dataclasses import replace

    return replace(
        result,
        suggestions=suggestions,
        skipped=[*result.skipped, *(s.title for s in suggestions[1:])],
        fleet_admission=admission,
    )
