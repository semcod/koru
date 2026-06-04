"""Diagnostic probe ordering and execution for ``koru doctor``."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from koru.doctor_constants import FAIL
from koru.doctor_models import Check, DoctorReport

CheckFn = Callable[[Path], tuple[str, str]]
CheckResolver = Callable[[str], CheckFn]

_BASE_PROBES: tuple[tuple[str, str], ...] = (
    ("detected_environment", "_check_detected_environment"),
    ("detected_configuration", "_check_detected_configuration"),
    ("git_repo", "_check_git_repo"),
    ("planfile_binary", "_check_planfile_binary"),
    ("koru_package_version", "_check_koru_package_version"),
    ("planfile_cli_version", "_check_planfile_cli_version"),
    ("planfile_config", "_check_planfile_config"),
    ("planfile_sprints", "_check_planfile_sprints"),
    ("planfile_sprints_yaml", "_check_planfile_sprints_yaml"),
    ("runtime_dir", "_check_runtime_dir"),
    ("policy_yaml", "_check_policy_yaml"),
    ("koru_project_pipeline", "_check_koru_project_pipeline"),
    ("autonomous_environ", "autonomous_environ_doctor_probe"),
    ("autonomous_service_stream", "_check_autonomous_service_stream"),
    ("koru_runtime_identity", "_check_koru_runtime_identity"),
    ("python_venv_alignment", "_check_python_venv_alignment"),
    ("autopilot_plugin_bundle", "_check_autopilot_plugin_bundle"),
    ("autopilot_env", "_check_autopilot_env"),
    ("ide_runtime_presence", "_check_ide_runtime_presence"),
    ("autopilot_socket", "_check_autopilot_socket"),
    ("autopilot_manage", "_check_autopilot_manage"),
    ("autopilot_runtime_status", "_check_autopilot_runtime_status"),
    ("autopilot_debug_log", "_check_autopilot_debug_log"),
    ("autopilot_chat_control", "_check_autopilot_chat_control"),
    ("windsurf_chat_column_control", "_check_windsurf_chat_column_control"),
    ("plugin_console_logs", "_check_plugin_console_logs"),
    ("ide_console_log", "_check_ide_console_log"),
    ("agent_backends_registry", "_check_agent_backends_registry"),
    ("interface_registry", "_check_interface_registry"),
    ("inotify_watches", "_check_inotify_watches"),
    ("wup_binary", "_check_wup_binary"),
)


def probe_specs(project: Path) -> list[tuple[str, str]]:
    probes = list(_BASE_PROBES)
    if (project / ".git").exists():
        probes.append(("gitignore", "_check_gitignore"))
    probes.append(("ci_command", "_check_ci_command"))
    if (project / "tests").exists() or (project / "pyproject.toml").exists():
        probes.append(("pytest_collect", "_check_pytest_collect"))
    return probes


def run_diagnostics(project: Path, *, check_resolver: CheckResolver) -> DoctorReport:
    """Run every check against ``project`` and return a diagnostic report."""
    project = project.resolve()
    report = DoctorReport(project=project)
    for name, attr in probe_specs(project):
        try:
            status, detail = check_resolver(attr)(project)
        except Exception as exc:  # pragma: no cover - defensive guard
            status, detail = FAIL, f"probe crashed: {exc!r}"
        report.checks.append(Check(name=name, status=status, detail=detail))
    return report


def problem_catalog(catalog: tuple[object, ...]) -> list[dict[str, str]]:
    """Return known problem classes and their detection rules."""
    return [
        {
            "check": item.check,
            "severity": item.severity,
            "problem": item.problem,
            "detection": item.detection,
        }
        for item in catalog
    ]
