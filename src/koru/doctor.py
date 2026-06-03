"""``koru --doctor`` — diagnose a koru-managed project.

When something goes wrong (LLM agent stuck, queue runner refusing to
start, policy not taking effect), the operator should run ``koru
--doctor`` first. The output is a flat list of named checks with
``pass`` / ``warn`` / ``fail`` status and a one-line detail. Both
human (text) and machine (JSON) renderings are produced from the same
report, so the LLM can also self-diagnose by parsing JSON.

Inventory of checks (stable names — ``run_diagnostics`` returns them
in this order so reports diff cleanly across runs):

    git_repo          — `.git/` resolvable from the project tree
    planfile_binary   — KORU_PLANFILE_CMD or `planfile` on PATH
    planfile_config   — `.planfile/config.yaml` exists and parses
    planfile_sprints  — at least one `.planfile/sprints/*.yaml` parses
                        and contains a `sprint.tickets` mapping
    runtime_dir       — `.planfile/.koru/` is writable (or its parent
                        is, since koru creates it lazily)
    policy_yaml       — `.planfile/.koru/policy.yaml` parses (if present)
    gitignore         — `.gitignore` ignores `.planfile/.koru/` (only
                        emitted when `.git/` is present)
    ci_command        — `policy.ci_command` first token resolves on PATH
    pytest_collect    — `python3 -m pytest --collect-only` exits 0 within
                        15 s (override via ``KORU_DOCTOR_PYTEST_TIMEOUT``).
                        Only emitted when ``pyproject.toml`` or ``tests/``
                        exists; pairs with ``koru scan``'s timeout fix to
                        catch hung collection (see PLF-093 post-mortem).
    koru_project_pipeline — root ``koru.yaml`` exists and parses when the
                        project is planfile-initialised (``SKIP`` before
                        ``.planfile/config.yaml``).
    autonomous_environ — ``TICKET_SOURCES`` / idle-diag / WUP-related env vars
                        for ``koru autonomous up`` (``FAIL`` on invalid
                        ``TICKET_SOURCES``).
    koru_runtime_identity — active Python/package/PATH/repo-local executable
                        identity for Koru itself.
    python_venv_alignment — active `VIRTUAL_ENV`, Python executable, and
                        project `.venv` alignment.
    autopilot_plugin_bundle — expected plugin version, package metadata, lockfile,
                        and bundled VSIX asset alignment.
    autonomous_service_stream — active ``koru auto``/WUP/autopilot socket streams
                        that may race when multiple services target one project.
    autopilot_env     — selected autopilot lane/IDE/socket environment.
    ide_runtime_presence — requested IDE is visible as a running process.
    autopilot_socket  — selected autopilot socket exists and accepts connects.
    autopilot_manage  — package/plugin/daemon state from ``koru autopilot manage``.
    autopilot_debug_log — recent plugin debug log activity for selected IDE/socket.
    autopilot_chat_control — recent IDE chat focus/paste/submit symptoms from
                        plugin debug logs.
    windsurf_chat_column_control — Windsurf right-chat column toggle symptoms
                        after native chat send.
    agent_backends_registry — static profile ids from ``koru.agent_backends``
                        (``PASS`` when the registry loads; see
                        ``koru agent-backends``).
    koru_package_version — installed ``koru`` distribution version (``WARN`` if
                        metadata missing, e.g. bare source tree).
    planfile_cli_version — ``planfile --version`` / ``KORU_PLANFILE_CMD … --version``
                        (``SKIP`` when no planfile executable).

Exit-code contract for the CLI wrapper: ``has_failures`` ⇒ ``1``;
warnings alone ⇒ ``0`` (warnings are advisory, not blocking).

The module is intentionally side-effect-free (no writes, no network).
"""


import json
import os
import subprocess  # noqa: F401 - compatibility: tests patch koru.doctor.subprocess.run
from dataclasses import dataclass, field
from pathlib import Path

from koru import doctor_autonomous_streams as _autonomous_streams
from koru import doctor_chat_control as _chat_control
from koru import doctor_plugin_console as _plugin_console
from koru import doctor_project_health as _project_health
from koru import doctor_reporting_checks as _reporting_checks
from koru.autonomous_env import autonomous_environ_doctor_probe
from koru.doctor_autopilot_checks import (
    _autopilot_env_detail_bits as _autopilot_env_detail_bits,
)
from koru.doctor_autopilot_checks import (
    _autopilot_env_snapshot as _autopilot_env_snapshot,
)
from koru.doctor_autopilot_checks import (
    _autopilot_env_status as _autopilot_env_status,
)
from koru.doctor_autopilot_checks import (
    _check_autopilot_env,
    _check_autopilot_manage,
    _check_autopilot_runtime_status,
    _check_autopilot_socket,
    _check_ide_runtime_presence,
    _resolve_autopilot_socket_for_doctor,
    _selected_autopilot_ide,
)
from koru.doctor_autopilot_checks import (
    _has_autopilot_selection as _has_autopilot_selection,
)
from koru.doctor_constants import (
    _PROBLEM_CATALOG,
    FAIL,
    PASS,
    SKIP,
    WARN,
)
from koru.doctor_constants import (
    ProblemCatalogEntry as ProblemCatalogEntry,
)
from koru.doctor_plugin_bundle import (
    _autopilot_plugin_bundle_detail_bits as _autopilot_plugin_bundle_detail_bits,
)
from koru.doctor_plugin_bundle import (
    _autopilot_plugin_bundle_issues as _autopilot_plugin_bundle_issues,
)
from koru.doctor_plugin_bundle import (
    _autopilot_plugin_bundle_paths as _autopilot_plugin_bundle_paths,
)
from koru.doctor_plugin_bundle import (
    _check_autopilot_plugin_bundle,
)
from koru.doctor_plugin_bundle import (
    _package_lock_root_version as _package_lock_root_version,
)
from koru.doctor_plugin_bundle import (
    _read_json_file as _read_json_file,
)
from koru.doctor_project_checks import (
    _check_detected_configuration,
    _check_detected_environment,
)
from koru.doctor_project_checks import (
    _detected_configuration_json_bits as _detected_configuration_json_bits,
)
from koru.doctor_project_checks import (
    _detected_configuration_presence_bits as _detected_configuration_presence_bits,
)
from koru.doctor_render import (
    detected_problems as detected_problems,
)
from koru.doctor_render import (
    render_problem_catalog_text as render_problem_catalog_text,
)
from koru.doctor_render import (
    render_text as render_text,
)
from koru.doctor_reporting_checks import (
    _classify_ide_console_lines as _classify_ide_console_lines_impl,
)
from koru.doctor_reporting_checks import (
    _compact_console_excerpt as _compact_console_excerpt_impl,
)
from koru.doctor_reporting_checks import (
    _ide_console_build_detail as _ide_console_build_detail_impl,
)
from koru.doctor_reporting_checks import (
    _ide_console_category_counts as _ide_console_category_counts_impl,
)
from koru.doctor_reporting_checks import (
    _ide_console_error_count as _ide_console_error_count_impl,
)
from koru.doctor_reporting_checks import (
    _ide_console_line_is_diagnostic_headline as _ide_console_line_is_diagnostic_headline_impl,
)
from koru.doctor_reporting_checks import (
    _ide_console_line_is_interesting as _ide_console_line_is_interesting_impl,
)
from koru.doctor_reporting_checks import (
    _ide_console_log_roots as _ide_console_log_roots_impl,
)
from koru.doctor_reporting_checks import (
    _ide_console_warn_count as _ide_console_warn_count_impl,
)
from koru.doctor_reporting_checks import (
    _read_recent_ide_console_lines as _read_recent_ide_console_lines_impl,
)
from koru.doctor_reporting_checks import (
    _recent_ide_console_log_files as _recent_ide_console_log_files_impl,
)
from koru.doctor_reporting_checks import (
    check_ide_console_log as _check_ide_console_log_impl,
)
from koru.doctor_runtime_checks import (
    _check_koru_runtime_identity,
    _check_python_venv_alignment,
)
from koru.doctor_runtime_checks import (
    _installed_koru_version as _installed_koru_version,
)
from koru.doctor_runtime_checks import (
    _is_relative_to as _is_relative_to,
)
from koru.doctor_runtime_checks import (
    _koru_path_version_issues as _koru_path_version_issues,
)
from koru.doctor_runtime_checks import (
    _path_koru_supports_auto_subcommand as _path_koru_supports_auto_subcommand,
)
from koru.doctor_runtime_checks import (
    _read_project_version as _read_project_version,
)
from koru.runtime import runtime_dir

# Default timeout for the pytest-collect probe. Doctor is meant to be
# *interactive and fast*; we deliberately keep this tighter than
# ``scan_pytest_collect``'s 30 s so the operator does not stare at a
# black terminal for half a minute. Override via ``KORU_DOCTOR_PYTEST_TIMEOUT``.
DEFAULT_PYTEST_COLLECT_TIMEOUT_SECONDS: float = (
    _project_health.DEFAULT_PYTEST_COLLECT_TIMEOUT_SECONDS
)


@dataclass
class Check:
    """A single diagnostic outcome."""

    name: str
    status: str
    detail: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


@dataclass
class DoctorReport:
    """Aggregate result of ``run_diagnostics``."""

    project: Path
    checks: list[Check] = field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return any(c.status == FAIL for c in self.checks)

    @property
    def has_warnings(self) -> bool:
        return any(c.status == WARN for c in self.checks)

    def summary(self) -> dict[str, int]:
        counts = {PASS: 0, WARN: 0, FAIL: 0, SKIP: 0}
        for check in self.checks:
            counts[check.status] = counts.get(check.status, 0) + 1
        return counts

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1",
            "project": str(self.project),
            "summary": self.summary(),
            "has_failures": self.has_failures,
            "checks": [c.to_dict() for c in self.checks],
        }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_diagnostics(project: Path) -> DoctorReport:
    """Run every check against ``project`` and return a frozen report.

    Each check is wrapped so a single buggy probe cannot crash the
    whole diagnostic run — an unexpected exception is converted into
    a ``fail`` entry with the exception's repr in ``detail``.
    """
    project = project.resolve()
    report = DoctorReport(project=project)
    has_git = (project / ".git").exists()

    probes = [
        ("detected_environment", _check_detected_environment),
        ("detected_configuration", _check_detected_configuration),
        ("git_repo", _check_git_repo),
        ("planfile_binary", _check_planfile_binary),
        ("koru_package_version", _check_koru_package_version),
        ("planfile_cli_version", _check_planfile_cli_version),
        ("planfile_config", _check_planfile_config),
        ("planfile_sprints", _check_planfile_sprints),
        ("planfile_sprints_yaml", _check_planfile_sprints_yaml),
        ("runtime_dir", _check_runtime_dir),
        ("policy_yaml", _check_policy_yaml),
        ("koru_project_pipeline", _check_koru_project_pipeline),
        ("autonomous_environ", autonomous_environ_doctor_probe),
        ("autonomous_service_stream", _check_autonomous_service_stream),
        ("koru_runtime_identity", _check_koru_runtime_identity),
        ("python_venv_alignment", _check_python_venv_alignment),
        ("autopilot_plugin_bundle", _check_autopilot_plugin_bundle),
        ("autopilot_env", _check_autopilot_env),
        ("ide_runtime_presence", _check_ide_runtime_presence),
        ("autopilot_socket", _check_autopilot_socket),
        ("autopilot_manage", _check_autopilot_manage),
        ("autopilot_runtime_status", _check_autopilot_runtime_status),
        ("autopilot_debug_log", _check_autopilot_debug_log),
        ("autopilot_chat_control", _check_autopilot_chat_control),
        ("windsurf_chat_column_control", _check_windsurf_chat_column_control),
        ("plugin_console_logs", _check_plugin_console_logs),
        ("ide_console_log", _check_ide_console_log),
        ("agent_backends_registry", _check_agent_backends_registry),
        ("interface_registry", _check_interface_registry),
        ("inotify_watches", _check_inotify_watches),
        ("wup_binary", _check_wup_binary),
    ]
    if has_git:
        probes.append(("gitignore", _check_gitignore))
    probes.append(("ci_command", _check_ci_command))
    # pytest_collect runs last because it's the slowest probe (subprocess
    # + 15 s timeout). Putting it at the end means the cheaper checks
    # complete first — the operator can already start reading their
    # results while pytest is still warming up.
    if (project / "tests").exists() or (project / "pyproject.toml").exists():
        probes.append(("pytest_collect", _check_pytest_collect))

    for name, fn in probes:
        try:
            status, detail = fn(project)
        except Exception as exc:  # pragma: no cover — defensive guard
            status, detail = FAIL, f"probe crashed: {exc!r}"
        report.checks.append(Check(name=name, status=status, detail=detail))

    return report


def problem_catalog() -> list[dict[str, str]]:
    """Return known problem classes and their detection rules."""
    return [
        {
            "check": item.check,
            "severity": item.severity,
            "problem": item.problem,
            "detection": item.detection,
        }
        for item in _PROBLEM_CATALOG
    ]

# ---------------------------------------------------------------------------
# Individual probes
# ---------------------------------------------------------------------------


def _check_agent_backends_registry(_project: Path) -> tuple[str, str]:
    del _project
    from koru.agent_backends import list_agent_backend_ids

    ids = list_agent_backend_ids()
    return PASS, f"{len(ids)} profiles: {', '.join(ids)}"


def _check_interface_registry(_project: Path) -> tuple[str, str]:
    del _project
    from koru.interface_registry import list_interface_ids, summarize_interfaces_by_family

    ids = list_interface_ids()
    if not ids:
        return WARN, "0 interfaces loaded"
    families = summarize_interfaces_by_family()
    family_summary = ", ".join(f"{name}={count}" for name, count in sorted(families.items()))
    preview = f"{', '.join(ids[:5])}{' ...' if len(ids) > 5 else ''}"
    return PASS, f"{len(ids)} interfaces: {preview}; families: {family_summary}"


_short_command = _autonomous_streams.short_command


def _autopilot_stream_socket_paths() -> list[Path]:
    selected = _resolve_autopilot_socket_for_doctor()
    return _autonomous_streams.autopilot_stream_socket_paths(selected)


def _autopilot_stream_socket_summary() -> tuple[list[str], int, int]:
    return _autonomous_streams.autopilot_stream_socket_summary(
        _autopilot_stream_socket_paths()
    )


_process_stream_summary = _autonomous_streams.process_stream_summary
_drop_non_service_autonomous_matches = (
    _autonomous_streams.drop_non_service_autonomous_matches
)
_autonomous_stream_issue_codes = _autonomous_streams.autonomous_stream_issue_codes


def _check_autonomous_service_stream(project: Path) -> tuple[str, str]:
    return _autonomous_streams.check_autonomous_service_stream(
        project,
        socket_summary=_autopilot_stream_socket_summary,
    )


def _autopilot_debug_log_path() -> Path:
    return Path(os.environ.get("KORU_PLUGIN_DEBUG_LOG", "/tmp/koru-plugin-debug.log"))


def _read_recent_autopilot_debug_lines(path: Path, *, limit: int = 400) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]


def _autopilot_line_mentions_selected(line: str, *, selected: str, socket_text: str) -> bool:
    if f'"ide":"{selected}"' in line or socket_text in line or f"ide={selected}" in line:
        return True
    if selected == "windsurf" and "WINDSURF_" in line:
        return True
    if selected == "antigravity" and "ANTIGRAVITY_" in line:
        return True
    return False


def _autopilot_debug_event_name(line: str) -> str:
    return _chat_control.autopilot_debug_event_name(line)


def _autopilot_debug_event_has(line: str, token: str) -> bool:
    return _chat_control.autopilot_debug_event_has(line, token)


def _read_recent_autopilot_activity_lines(project: Path, *, limit: int = 600) -> list[str]:
    path = runtime_dir(project) / "nfo-events.jsonl"
    if not path.is_file():
        return []
    try:
        rows = path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    except OSError:
        return []
    activity: list[str] = []
    for row in rows:
        try:
            payload = json.loads(row)
        except json.JSONDecodeError:
            continue
        extra = payload.get("extra")
        if isinstance(extra, dict):
            message = str(extra.get("activity_message") or "")
        else:
            message = ""
        if not message:
            message = str(payload.get("kwargs") or "")
        if message:
            activity.append(message)
    return activity


@dataclass(frozen=True)
class _AutopilotDebugContext:
    selected: str | None
    path: Path
    socket_text: str
    relevant: list[str]
    skip_reason: str | None


def _recent_autopilot_debug_context() -> _AutopilotDebugContext:
    selected = _selected_autopilot_ide()
    path = _autopilot_debug_log_path()
    if not selected:
        return _AutopilotDebugContext(selected, path, "", [], "autopilot env unset")
    if not path.is_file():
        return _AutopilotDebugContext(selected, path, "", [], f"{path} missing")
    socket_text = str(_resolve_autopilot_socket_for_doctor())
    lines = _read_recent_autopilot_debug_lines(path)
    relevant = [
        line
        for line in lines
        if _autopilot_line_mentions_selected(line, selected=selected, socket_text=socket_text)
    ]
    return _AutopilotDebugContext(selected, path, socket_text, relevant, None)


def _check_autopilot_debug_log(_project: Path) -> tuple[str, str]:
    try:
        context = _recent_autopilot_debug_context()
    except OSError as exc:
        path = _autopilot_debug_log_path()
        return WARN, f"cannot read {path}: {exc}"
    if context.skip_reason:
        return SKIP, context.skip_reason
    if not context.relevant:
        return WARN, (
            f"{context.path}: no recent entries for ide={context.selected} "
            f"or socket={context.socket_text}"
        )
    if any("CONNECT_OK" in line or "HELLO" in line for line in context.relevant):
        return PASS, f"{context.path}: {len(context.relevant)} recent matching entrie(s)"
    if any("CONNECT_ERROR" in line for line in context.relevant):
        return (
            WARN,
            f"{context.path}: {len(context.relevant)} matching entrie(s), "
            "latest connection errors present",
        )
    return PASS, f"{context.path}: {len(context.relevant)} recent matching entrie(s)"


_activity_line_mentions_selected = _chat_control.activity_line_mentions_selected
_count_daemon_metrics = _chat_control.count_daemon_metrics
_count_chat_control_metrics = _chat_control.count_chat_control_metrics
_calculate_command_indices = _chat_control.calculate_command_indices
_calculate_success_failure_indices = _chat_control.calculate_success_failure_indices
_ChatControlAnalysis = _chat_control.ChatControlAnalysis
_build_chat_control_detail_bits = _chat_control.build_chat_control_detail_bits


def _chat_control_context(
    project: Path,
) -> tuple[str, Path, list[str], list[str], str | None, str | None]:
    """Return normalized context for chat-control checks.

    Returns:
        selected, debug_log_path, relevant_debug_lines, selected_activity_lines,
        early_status, early_detail
    """
    try:
        context = _recent_autopilot_debug_context()
    except OSError as exc:
        path = _autopilot_debug_log_path()
        return "", path, [], [], WARN, f"cannot read {path}: {exc}"

    if context.skip_reason:
        return context.selected or "", context.path, context.relevant, [], SKIP, context.skip_reason
    if not context.relevant:
        return (
            context.selected or "",
            context.path,
            context.relevant,
            [],
            WARN,
            f"{context.path}: no recent chat-control entries for ide={context.selected}",
        )

    activity = [
        line
        for line in _read_recent_autopilot_activity_lines(project)
        if context.selected and _activity_line_mentions_selected(line, context.selected)
    ]
    return context.selected or "", context.path, context.relevant, activity, None, None


_chat_control_has_failures = _chat_control.chat_control_has_failures
_chat_control_command_hints = _chat_control.chat_control_command_hints
_chat_control_recovered_after_retry = _chat_control.chat_control_recovered_after_retry
_chat_control_result = _chat_control.chat_control_result
_analyze_chat_control = _chat_control.analyze_chat_control


def _check_autopilot_chat_control(project: Path) -> tuple[str, str]:
    selected, _path, relevant, activity, early_status, early_detail = _chat_control_context(project)
    if early_status is not None and early_detail is not None:
        return early_status, early_detail

    analysis = _analyze_chat_control(selected, relevant, activity)
    status, detail = _chat_control_result(
        detail_bits=analysis.detail_bits,
        command_missing_latest=analysis.command_missing_latest,
        chat_metrics=analysis.chat_metrics,
        daemon_successes=analysis.daemon_successes,
        last_success_index=analysis.last_success_index,
        last_failure_index=analysis.last_failure_index,
        last_activity_success_index=analysis.last_activity_success_index,
        last_activity_failure_index=analysis.last_activity_failure_index,
    )
    if status == WARN:
        detail = "; ".join([detail, *_chat_control_command_hints(project, selected)])
    return status, detail


_windsurf_chat_column_indexes = _chat_control.windsurf_chat_column_indexes
_windsurf_line_mentions_chat_open_command = (
    _chat_control.windsurf_line_mentions_chat_open_command
)
_windsurf_chat_column_detail_bits = _chat_control.windsurf_chat_column_detail_bits
_windsurf_chat_column_result = _chat_control.windsurf_chat_column_result


def _check_windsurf_chat_column_control(_project: Path) -> tuple[str, str]:
    try:
        context = _recent_autopilot_debug_context()
    except OSError as exc:
        path = _autopilot_debug_log_path()
        return WARN, f"cannot read {path}: {exc}"
    if context.skip_reason:
        return SKIP, context.skip_reason
    if context.selected != "windsurf":
        return SKIP, f"ide={context.selected or '-'}; only applicable to windsurf"
    if not context.relevant:
        return WARN, f"{context.path}: no recent Windsurf chat-column entries"

    indexes = _windsurf_chat_column_indexes(context.relevant)
    detail_bits = _windsurf_chat_column_detail_bits(context.relevant, indexes)
    return _windsurf_chat_column_result(indexes, detail_bits)


_doctor_console_log_tail_limit = _plugin_console.doctor_console_log_tail_limit
_compact_plugin_console_entry = _plugin_console.compact_plugin_console_entry
_plugin_console_entry_matches_selected = (
    _plugin_console.plugin_console_entry_matches_selected
)
_daemon_console_logs_for_doctor = _plugin_console.daemon_console_logs_for_doctor


def _plugin_debug_log_tail_for_doctor(limit: int) -> tuple[Path, list[str], str | None]:
    return _plugin_console.plugin_debug_log_tail_for_doctor(
        limit,
        recent_context=_recent_autopilot_debug_context,
        debug_log_path=_autopilot_debug_log_path,
    )


_plugin_console_logs_daemon_result = _plugin_console.plugin_console_logs_daemon_result


def _plugin_console_logs_debug_tail_result(
    *,
    selected: str,
    socket_path: Path,
    debug_path: Path,
    debug_tail: list[str],
    daemon_error: str | None,
) -> tuple[str, str] | None:
    return _plugin_console.plugin_console_logs_debug_tail_result(
        selected=selected,
        socket_path=socket_path,
        debug_path=debug_path,
        debug_tail=debug_tail,
        daemon_error=daemon_error,
        offline_noise_checker=_plugin_debug_tail_is_daemon_offline_noise,
    )


_plugin_console_logs_empty_result = _plugin_console.plugin_console_logs_empty_result


def _check_plugin_console_logs(_project: Path) -> tuple[str, str]:
    return _plugin_console.check_plugin_console_logs(
        selected_autopilot_ide=_selected_autopilot_ide,
        tail_limit=_doctor_console_log_tail_limit,
        socket_resolver=_resolve_autopilot_socket_for_doctor,
        daemon_logs_reader=_daemon_console_logs_for_doctor,
        debug_tail_reader=_plugin_debug_log_tail_for_doctor,
        entry_matches_selected=_plugin_console_entry_matches_selected,
        daemon_result=_plugin_console_logs_daemon_result,
        debug_tail_result=_plugin_console_logs_debug_tail_result,
        empty_result=_plugin_console_logs_empty_result,
    )


def _plugin_debug_tail_is_daemon_offline_noise(
    lines: list[str],
    *,
    selected: str,
    socket_path: Path,
    daemon_error: str | None,
) -> bool:
    return _plugin_console.plugin_debug_tail_is_daemon_offline_noise(
        lines,
        selected=selected,
        socket_path=socket_path,
        daemon_error=daemon_error,
        event_name=_autopilot_debug_event_name,
        event_has=_autopilot_debug_event_has,
    )


_ide_console_log_roots = _ide_console_log_roots_impl
_recent_ide_console_log_files = _recent_ide_console_log_files_impl
_read_recent_ide_console_lines = _read_recent_ide_console_lines_impl
_ide_console_line_is_interesting = _ide_console_line_is_interesting_impl
_ide_console_line_is_diagnostic_headline = _ide_console_line_is_diagnostic_headline_impl
_compact_console_excerpt = _compact_console_excerpt_impl


_IDE_CONSOLE_WARN_TOKENS = _reporting_checks._IDE_CONSOLE_WARN_TOKENS
_IDE_CONSOLE_CATEGORY_PATTERNS = _reporting_checks._IDE_CONSOLE_CATEGORY_PATTERNS


_ide_console_error_count = _ide_console_error_count_impl
_ide_console_warn_count = _ide_console_warn_count_impl
_ide_console_category_counts = _ide_console_category_counts_impl
_classify_ide_console_lines = _classify_ide_console_lines_impl
_ide_console_build_detail = _ide_console_build_detail_impl


def _check_ide_console_log(_project: Path) -> tuple[str, str]:
    del _project
    return _check_ide_console_log_impl(
        selected_autopilot_ide=_selected_autopilot_ide,
    )


_check_git_repo = _project_health.check_git_repo
_check_planfile_binary = _project_health.check_planfile_binary
_planfile_version_argv = _project_health.planfile_version_argv
_check_koru_package_version = _project_health.check_koru_package_version


def _check_planfile_cli_version(project: Path) -> tuple[str, str]:
    return _project_health.check_planfile_cli_version(
        project,
        argv_resolver=_planfile_version_argv,
    )


_check_planfile_config = _project_health.check_planfile_config
_check_planfile_sprints = _project_health.check_planfile_sprints
_check_planfile_sprints_yaml = _project_health.check_planfile_sprints_yaml
_check_runtime_dir = _project_health.check_runtime_dir
_check_koru_project_pipeline = _project_health.check_koru_project_pipeline
_check_policy_yaml = _project_health.check_policy_yaml
_check_gitignore = _project_health.check_gitignore


_PYTEST_COLLECT_COUNT_RE = _project_health._PYTEST_COLLECT_COUNT_RE
_PYTEST_NO_TESTS_RE = _project_health._PYTEST_NO_TESTS_RE


_resolve_pytest_collect_timeout = _project_health.resolve_pytest_collect_timeout
_compact_pytest_collect_failure = _project_health.compact_pytest_collect_failure


def _check_pytest_collect(project: Path) -> tuple[str, str]:
    return _project_health.check_pytest_collect(
        project,
        timeout_resolver=_resolve_pytest_collect_timeout,
        failure_compactor=_compact_pytest_collect_failure,
    )


_check_inotify_watches = _project_health.check_inotify_watches
_check_wup_binary = _project_health.check_wup_binary
_check_ci_command = _project_health.check_ci_command
