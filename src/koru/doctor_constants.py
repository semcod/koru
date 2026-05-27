"""Constants and dataclasses for koru doctor diagnostics.

This module contains the core data structures used by the doctor system:
- Status constants (PASS, WARN, FAIL, SKIP)
- ProblemCatalogEntry dataclass
- Problem catalog definitions
"""

from dataclasses import dataclass

PASS = "pass"
WARN = "warn"
FAIL = "fail"
SKIP = "skip"


@dataclass(frozen=True)
class ProblemCatalogEntry:
    """Static description of a known diagnostic problem and its detector."""

    check: str
    severity: str
    problem: str
    detection: str


_PROBLEM_CATALOG: tuple[ProblemCatalogEntry, ...] = (
    ProblemCatalogEntry(
        check="git_repo",
        severity=WARN,
        problem="Project is not inside a Git repository.",
        detection="`.git` is missing or unresolved from the project root.",
    ),
    ProblemCatalogEntry(
        check="planfile_binary",
        severity=FAIL,
        problem="planfile CLI is unavailable or misconfigured.",
        detection="KORU_PLANFILE_CMD is not executable and `planfile` is not on PATH.",
    ),
    ProblemCatalogEntry(
        check="planfile_config",
        severity=FAIL,
        problem="planfile project configuration is missing or invalid.",
        detection="`.planfile/config.yaml` missing or YAML cannot be parsed as a mapping.",
    ),
    ProblemCatalogEntry(
        check="planfile_sprints",
        severity=FAIL,
        problem="Sprint queue data is missing, malformed, or empty.",
        detection="No valid `.planfile/sprints/*.yaml` ticket mapping is found.",
    ),
    ProblemCatalogEntry(
        check="runtime_dir",
        severity=FAIL,
        problem="Koru runtime directory is not writable.",
        detection="`.planfile/.koru/` (or its parent) lacks write permission.",
    ),
    ProblemCatalogEntry(
        check="policy_yaml",
        severity=FAIL,
        problem="Policy file is malformed or has invalid gate value types.",
        detection="`.planfile/.koru/policy.yaml` parse/type validation fails.",
    ),
    ProblemCatalogEntry(
        check="ci_command",
        severity=FAIL,
        problem="Configured CI command cannot be executed.",
        detection="First token in `policy.ci.command` cannot be resolved on PATH.",
    ),
    ProblemCatalogEntry(
        check="pytest_collect",
        severity=FAIL,
        problem="Pytest discovery hangs or cannot collect tests.",
        detection="`pytest --collect-only` times out or exits with collection errors.",
    ),
    ProblemCatalogEntry(
        check="autonomous_environ",
        severity=FAIL,
        problem="Autonomous mode environment variables are inconsistent.",
        detection="Doctor probe validates `TICKET_SOURCES` and related env overrides.",
    ),
    ProblemCatalogEntry(
        check="koru_runtime_identity",
        severity=WARN,
        problem="The active `koru` executable, imported package, and source tree differ.",
        detection=(
            "Doctor compares PATH `koru`, repo-local `.venv/bin/koru`, "
            "Python executable, and pyproject/package versions."
        ),
    ),
    ProblemCatalogEntry(
        check="python_venv_alignment",
        severity=WARN,
        problem="The shell venv, Python executable, and project `.venv` do not agree.",
        detection=(
            "Doctor compares `VIRTUAL_ENV`, `sys.executable`, and `<project>/.venv` "
            "to catch mixed `venv`/`.venv` runs."
        ),
    ),
    ProblemCatalogEntry(
        check="autopilot_plugin_bundle",
        severity=FAIL,
        problem="The expected autopilot plugin version is not bundled consistently.",
        detection=(
            "Doctor compares Python expected plugin version, plugin package.json, "
            "package-lock.json, and the bundled VSIX asset."
        ),
    ),
    ProblemCatalogEntry(
        check="autopilot_env",
        severity=FAIL,
        problem="Autopilot environment (lane/IDE/socket) is misconfigured.",
        detection=(
            "Doctor validates KORU_AUTOPILOT_LANE, KORU_AUTOPILOT_IDE, and "
            "KORU_AUTOPILOT_INSTANCE env vars."
        ),
    ),
    ProblemCatalogEntry(
        check="autonomous_service_stream",
        severity=WARN,
        problem=(
            "Multiple active koru auto/WUP/autopilot socket streams may race "
            "and generate conflicting queue or chat events."
        ),
        detection=(
            "Doctor inspects running koru autonomous processes, WUP watchers, "
            "and autopilot socket listeners/files for duplicate or orphaned streams."
        ),
    ),
    ProblemCatalogEntry(
        check="ide_runtime_presence",
        severity=WARN,
        problem="Requested IDE is not running.",
        detection="Doctor checks running processes for the selected IDE.",
    ),
    ProblemCatalogEntry(
        check="autopilot_socket",
        severity=FAIL,
        problem="Autopilot socket is missing or not accepting connections.",
        detection=(
            "Doctor checks socket existence and can connect to the daemon "
            "(SO_PEERCRED validated)."
        ),
    ),
    ProblemCatalogEntry(
        check="autopilot_manage",
        severity=WARN,
        problem="Autopilot package/plugin/daemon state is inconsistent.",
        detection=(
            "Doctor compares `koru autopilot manage` output against "
            "expected installation state."
        ),
    ),
    ProblemCatalogEntry(
        check="autopilot_runtime_status",
        severity=WARN,
        problem="Live autopilot daemon/plugin runtime state is incomplete or inconsistent.",
        detection=(
            "Doctor reads the active daemon status payload and validates daemon "
            "liveness, connected plugins, versions, builds, and selected IDE routing."
        ),
    ),
    ProblemCatalogEntry(
        check="autopilot_debug_log",
        severity=WARN,
        problem="No recent autopilot debug log activity for selected IDE/socket.",
        detection=(
            "Doctor scans plugin debug logs for recent timestamp entries "
            "(within last 5 minutes)."
        ),
    ),
    ProblemCatalogEntry(
        check="autopilot_chat_control",
        severity=WARN,
        problem="No recent IDE chat focus/paste/submit symptoms from plugin logs.",
        detection=(
            "Doctor scans plugin debug logs for chat focus, paste, and submit "
            "events, including submit_unverified/manual_send_required failures "
            "(within last 5 minutes)."
        ),
    ),
    ProblemCatalogEntry(
        check="windsurf_chat_column_control",
        severity=WARN,
        problem="Windsurf right-chat column may not be toggled after native chat send.",
        detection=(
            "Doctor scans Windsurf logs for chat column toggle symptoms "
            "(within last 5 minutes)."
        ),
    ),
    ProblemCatalogEntry(
        check="agent_backends_registry",
        severity=WARN,
        problem="Agent backends registry failed to load.",
        detection=(
            "Doctor checks that `koru.agent_backends` returns a non-empty "
            "registry of static agent profiles."
        ),
    ),
    ProblemCatalogEntry(
        check="interface_registry",
        severity=WARN,
        problem="Autonomy interface registry failed to load.",
        detection=(
            "Doctor checks that `docs/interfaces/koru-interface-registry.yaml` "
            "loads and exposes a non-empty set of control/observation interfaces."
        ),
    ),
    ProblemCatalogEntry(
        check="koru_package_version",
        severity=WARN,
        problem="Installed `koru` distribution metadata is missing.",
        detection=(
            "Doctor checks `importlib.metadata.version('koru')`; "
            "WARN if missing (e.g. bare source tree)."
        ),
    ),
    ProblemCatalogEntry(
        check="planfile_cli_version",
        severity=WARN,
        problem="planfile CLI version is unavailable.",
        detection=(
            "Doctor runs `planfile --version` when planfile binary is present; "
            "WARN if version cannot be parsed."
        ),
    ),
)


__all__ = [
    "PASS",
    "WARN",
    "FAIL",
    "SKIP",
    "ProblemCatalogEntry",
    "_PROBLEM_CATALOG",
]
