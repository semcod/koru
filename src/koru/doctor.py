"""Compatibility facade for ``koru --doctor`` project diagnostics.

The doctor report is a stable ordered list of named checks with
``pass`` / ``warn`` / ``fail`` / ``skip`` status and one-line details.
Implementation lives in responsibility-focused ``doctor_*`` modules; this
facade keeps legacy imports and test monkeypatch targets stable.

The module is intentionally side-effect-free: no writes and no network.
CLI exit-code behavior remains: failures exit non-zero, warnings are advisory.
"""


import subprocess  # noqa: F401 - compatibility: tests patch koru.doctor.subprocess.run
from pathlib import Path

from koru import doctor_autonomous_streams as _autonomous_streams
from koru import doctor_autopilot_debug as _autopilot_debug
from koru import doctor_project_health as _project_health
from koru import doctor_registry_checks as _registry_checks
from koru import doctor_reporting_checks as _reporting_checks
from koru import doctor_runner as _runner
from koru.autonomous_env import (
    autonomous_environ_doctor_probe as autonomous_environ_doctor_probe,
)
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
    _check_autopilot_env as _check_autopilot_env,
)
from koru.doctor_autopilot_checks import (
    _check_autopilot_manage as _check_autopilot_manage,
)
from koru.doctor_autopilot_checks import (
    _check_autopilot_runtime_status as _check_autopilot_runtime_status,
)
from koru.doctor_autopilot_checks import (
    _check_autopilot_socket as _check_autopilot_socket,
)
from koru.doctor_autopilot_checks import (
    _check_ide_runtime_presence as _check_ide_runtime_presence,
)
from koru.doctor_autopilot_checks import (
    _has_autopilot_selection as _has_autopilot_selection,
)
from koru.doctor_autopilot_checks import (
    _resolve_autopilot_socket_for_doctor,
    _selected_autopilot_ide,
)
from koru.doctor_constants import (
    _PROBLEM_CATALOG as _PROBLEM_CATALOG,
)
from koru.doctor_constants import (
    FAIL as FAIL,
)
from koru.doctor_constants import (
    PASS as PASS,
)
from koru.doctor_constants import (
    SKIP as SKIP,
)
from koru.doctor_constants import (
    WARN as WARN,
)
from koru.doctor_constants import (
    ProblemCatalogEntry as ProblemCatalogEntry,
)
from koru.doctor_models import Check as Check
from koru.doctor_models import DoctorReport as DoctorReport
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
    _check_autopilot_plugin_bundle as _check_autopilot_plugin_bundle,
)
from koru.doctor_plugin_bundle import (
    _package_lock_root_version as _package_lock_root_version,
)
from koru.doctor_plugin_bundle import (
    _read_json_file as _read_json_file,
)
from koru.doctor_project_checks import (
    _check_detected_configuration as _check_detected_configuration,
)
from koru.doctor_project_checks import (
    _check_detected_environment as _check_detected_environment,
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
    _check_koru_runtime_identity as _check_koru_runtime_identity,
)
from koru.doctor_runtime_checks import (
    _check_python_venv_alignment as _check_python_venv_alignment,
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

# Default timeout for the pytest-collect probe. Doctor is meant to be
# *interactive and fast*; we deliberately keep this tighter than
# ``scan_pytest_collect``'s 30 s so the operator does not stare at a
# black terminal for half a minute. Override via ``KORU_DOCTOR_PYTEST_TIMEOUT``.
DEFAULT_PYTEST_COLLECT_TIMEOUT_SECONDS: float = (
    _project_health.DEFAULT_PYTEST_COLLECT_TIMEOUT_SECONDS
)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_diagnostics(project: Path) -> DoctorReport:
    """Run every check against ``project`` and return a frozen report.

    Each check is wrapped so a single buggy probe cannot crash the
    whole diagnostic run — an unexpected exception is converted into
    a ``fail`` entry with the exception's repr in ``detail``.
    """
    return _runner.run_diagnostics(project, check_resolver=globals().__getitem__)


def problem_catalog() -> list[dict[str, str]]:
    """Return known problem classes and their detection rules."""
    return _runner.problem_catalog(_PROBLEM_CATALOG)

# ---------------------------------------------------------------------------
# Individual probes
# ---------------------------------------------------------------------------


_check_agent_backends_registry = _registry_checks.check_agent_backends_registry
_check_interface_registry = _registry_checks.check_interface_registry


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


_autopilot_debug_log_path = _autopilot_debug.autopilot_debug_log_path
_read_recent_autopilot_debug_lines = _autopilot_debug.read_recent_autopilot_debug_lines
_autopilot_line_mentions_selected = _autopilot_debug.autopilot_line_mentions_selected
_autopilot_debug_event_name = _autopilot_debug.autopilot_debug_event_name
_autopilot_debug_event_has = _autopilot_debug.autopilot_debug_event_has
_read_recent_autopilot_activity_lines = (
    _autopilot_debug.read_recent_autopilot_activity_lines
)
_AutopilotDebugContext = _autopilot_debug.AutopilotDebugContext


def _recent_autopilot_debug_context() -> _AutopilotDebugContext:
    return _autopilot_debug.recent_autopilot_debug_context(
        selected_ide=_selected_autopilot_ide,
        debug_log_path=_autopilot_debug_log_path,
        socket_resolver=_resolve_autopilot_socket_for_doctor,
        read_lines=_read_recent_autopilot_debug_lines,
        line_matches=_autopilot_line_mentions_selected,
    )


def _check_autopilot_debug_log(_project: Path) -> tuple[str, str]:
    return _autopilot_debug.check_autopilot_debug_log(
        recent_context=_recent_autopilot_debug_context,
        debug_log_path=_autopilot_debug_log_path,
    )


_activity_line_mentions_selected = _autopilot_debug.activity_line_mentions_selected
_count_daemon_metrics = _autopilot_debug.count_daemon_metrics
_count_chat_control_metrics = _autopilot_debug.count_chat_control_metrics
_calculate_command_indices = _autopilot_debug.calculate_command_indices
_calculate_success_failure_indices = _autopilot_debug.calculate_success_failure_indices
_ChatControlAnalysis = _autopilot_debug.ChatControlAnalysis
_build_chat_control_detail_bits = _autopilot_debug.build_chat_control_detail_bits


def _chat_control_context(
    project: Path,
) -> tuple[str, Path, list[str], list[str], str | None, str | None]:
    return _autopilot_debug.chat_control_context(
        project,
        recent_context=_recent_autopilot_debug_context,
        debug_log_path=_autopilot_debug_log_path,
        read_activity_lines=_read_recent_autopilot_activity_lines,
        activity_line_matches=_activity_line_mentions_selected,
    )


_chat_control_has_failures = _autopilot_debug.chat_control_has_failures
_chat_control_command_hints = _autopilot_debug.chat_control_command_hints
_chat_control_recovered_after_retry = _autopilot_debug.chat_control_recovered_after_retry
_chat_control_result = _autopilot_debug.chat_control_result
_analyze_chat_control = _autopilot_debug.analyze_chat_control


def _check_autopilot_chat_control(project: Path) -> tuple[str, str]:
    return _autopilot_debug.check_autopilot_chat_control(
        project,
        context_factory=_chat_control_context,
        command_hints=_chat_control_command_hints,
    )


_windsurf_chat_column_indexes = _autopilot_debug.windsurf_chat_column_indexes
_windsurf_line_mentions_chat_open_command = (
    _autopilot_debug.windsurf_line_mentions_chat_open_command
)
_windsurf_chat_column_detail_bits = _autopilot_debug.windsurf_chat_column_detail_bits
_windsurf_chat_column_result = _autopilot_debug.windsurf_chat_column_result


def _check_windsurf_chat_column_control(_project: Path) -> tuple[str, str]:
    return _autopilot_debug.check_windsurf_chat_column_control(
        recent_context=_recent_autopilot_debug_context,
        debug_log_path=_autopilot_debug_log_path,
    )


_doctor_console_log_tail_limit = _autopilot_debug.doctor_console_log_tail_limit
_compact_plugin_console_entry = _autopilot_debug.compact_plugin_console_entry
_plugin_console_entry_matches_selected = (
    _autopilot_debug.plugin_console_entry_matches_selected
)
_daemon_console_logs_for_doctor = _autopilot_debug.daemon_console_logs_for_doctor


def _plugin_debug_log_tail_for_doctor(limit: int) -> tuple[Path, list[str], str | None]:
    return _autopilot_debug.plugin_debug_log_tail_for_doctor(
        limit,
        recent_context=_recent_autopilot_debug_context,
        debug_log_path=_autopilot_debug_log_path,
    )


_plugin_console_logs_daemon_result = _autopilot_debug.plugin_console_logs_daemon_result


def _plugin_console_logs_debug_tail_result(
    *,
    selected: str,
    socket_path: Path,
    debug_path: Path,
    debug_tail: list[str],
    daemon_error: str | None,
) -> tuple[str, str] | None:
    return _autopilot_debug.plugin_console_logs_debug_tail_result(
        selected=selected,
        socket_path=socket_path,
        debug_path=debug_path,
        debug_tail=debug_tail,
        daemon_error=daemon_error,
        offline_noise_checker=_plugin_debug_tail_is_daemon_offline_noise,
    )


_plugin_console_logs_empty_result = _autopilot_debug.plugin_console_logs_empty_result


def _check_plugin_console_logs(_project: Path) -> tuple[str, str]:
    return _autopilot_debug.check_plugin_console_logs(
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
    return _autopilot_debug.plugin_debug_tail_is_daemon_offline_noise(
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
