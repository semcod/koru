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
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from koru.autonomous_env import autonomous_environ_doctor_probe
from koru.autonomy.environment import probe_socket_health
from koru.autopilot.ide import (
    detect_running_ides,
    detect_terminal_host_ide_id,
    normalize_ide_id,
)
from koru.autopilot.install_manager import collect_install_manager_report
from koru.doctor_constants import (
    FAIL,
    PASS,
    ProblemCatalogEntry,
    SKIP,
    WARN,
    _PROBLEM_CATALOG,
)
from koru.policy import policy_path
from koru.project_pipeline import KORU_PROJECT_PIPELINE_FILENAME, project_pipeline_path
from koru.runtime import planfile_dir, runtime_dir
from koru.utils.subprocess_runner import get_python_cmd
from koruide.plugin_version import EXPECTED_VSCODE_PLUGIN_VERSION
from koruide.socket import default_socket_path

# Default timeout for the pytest-collect probe. Doctor is meant to be
# *interactive and fast*; we deliberately keep this tighter than
# ``scan_pytest_collect``'s 30 s so the operator does not stare at a
# black terminal for half a minute. Override via ``KORU_DOCTOR_PYTEST_TIMEOUT``.
DEFAULT_PYTEST_COLLECT_TIMEOUT_SECONDS: float = 15.0


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
        ("koru_runtime_identity", _check_koru_runtime_identity),
        ("python_venv_alignment", _check_python_venv_alignment),
        ("autopilot_plugin_bundle", _check_autopilot_plugin_bundle),
        ("autopilot_env", _check_autopilot_env),
        ("ide_runtime_presence", _check_ide_runtime_presence),
        ("autopilot_socket", _check_autopilot_socket),
        ("autopilot_manage", _check_autopilot_manage),
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


def detected_problems(report: DoctorReport) -> list[dict[str, str]]:
    """Return warnings/failures as an explicit problem list for UX and JSON output."""
    return [
        c.to_dict()
        for c in report.checks
        if c.status in (WARN, FAIL)
    ]


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


def render_problem_catalog_text() -> str:
    """Render known problem classes in a compact text table."""
    lines = ["Known problems and detection rules:"]
    for item in _PROBLEM_CATALOG:
        sev = item.severity.upper()
        lines.append(f"  - [{sev}] {item.check}: {item.problem}")
        lines.append(f"      detection: {item.detection}")
    return "\n".join(lines)


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
    return PASS, f"{len(ids)} interfaces: {', '.join(ids[:5])}{' ...' if len(ids) > 5 else ''}; families: {family_summary}"


def _check_detected_environment(project: Path) -> tuple[str, str]:
    del project
    py = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    bits = [
        f"os={platform.system().lower()} {platform.release()} ({platform.machine()})",
        f"python={py}",
        f"executable={sys.executable}",
    ]
    virtual_env = os.environ.get("VIRTUAL_ENV", "").strip()
    if not virtual_env and getattr(sys, "base_prefix", sys.prefix) != sys.prefix:
        virtual_env = sys.prefix
    bits.append(f"virtual_env={virtual_env or 'none'}")
    lane = os.environ.get("KORU_AGENT_LANE", "").strip()
    if lane:
        bits.append(f"agent_lane={lane}")
    return PASS, "; ".join(bits)


def _check_detected_configuration(project: Path) -> tuple[str, str]:
    koru_project = project / ".koru" / "project.json"
    planfile_cfg = planfile_dir(project) / "config.yaml"
    policy_cfg = policy_path(project)
    pipeline_cfg = project_pipeline_path(project)

    status = PASS
    detail_bits: list[str] = [
        f"planfile_config={'present' if planfile_cfg.is_file() else 'missing'}",
        f"policy_yaml={'present' if policy_cfg.is_file() else 'missing'}",
        f"koru_yaml={'present' if pipeline_cfg.is_file() else 'missing'}",
    ]

    if koru_project.is_file():
        try:
            payload = json.loads(koru_project.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return FAIL, f".koru/project.json malformed JSON: {exc}"

        schema = str(payload.get("schema", "")).strip()
        declared_project = str(payload.get("project", "")).strip()
        detail_bits.append(f"koru_project_json=present(schema={schema or 'unknown'})")

        if declared_project:
            try:
                if Path(declared_project).expanduser().resolve() != project.resolve():
                    status = WARN
                    detail_bits.append("project_path_mismatch=true")
            except OSError:
                status = WARN
                detail_bits.append("project_path_mismatch=unknown")
        if schema and schema != "koru.project/v1":
            status = WARN
            detail_bits.append("schema_mismatch=true")
    else:
        detail_bits.append("koru_project_json=missing")
        if planfile_cfg.is_file():
            status = WARN

    return status, "; ".join(detail_bits)


def _read_project_version(path: Path) -> str | None:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    project = data.get("project")
    if not isinstance(project, dict):
        return None
    version = project.get("version")
    return str(version) if version else None


def _installed_koru_version() -> str | None:
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version("koru")
    except (ImportError, PackageNotFoundError, ValueError):
        return None


def _selected_autopilot_ide(*, include_terminal_hint: bool = True) -> str | None:
    raw_ide = os.environ.get("KORU_AUTOPILOT_IDE")
    raw_instance = os.environ.get("KORU_AUTOPILOT_INSTANCE")
    selected = normalize_ide_id(raw_ide) or normalize_ide_id(raw_instance)
    if selected or not include_terminal_hint:
        return selected
    return normalize_ide_id(detect_terminal_host_ide_id())


def _has_autopilot_selection() -> bool:
    return bool(
        os.environ.get("KORU_AUTOPILOT_IDE")
        or os.environ.get("KORU_AUTOPILOT_INSTANCE")
        or os.environ.get("KORU_AUTOPILOT_SOCKET")
        or _selected_autopilot_ide(include_terminal_hint=True)
    )


def _resolve_autopilot_socket_for_doctor() -> Path:
    selected = _selected_autopilot_ide()
    if selected and not os.environ.get("KORU_AUTOPILOT_SOCKET"):
        previous = os.environ.get("KORU_AUTOPILOT_INSTANCE")
        try:
            os.environ["KORU_AUTOPILOT_INSTANCE"] = selected
            return default_socket_path()
        finally:
            if previous is None:
                os.environ.pop("KORU_AUTOPILOT_INSTANCE", None)
            else:
                os.environ["KORU_AUTOPILOT_INSTANCE"] = previous
    return default_socket_path()


def _path_koru_supports_auto_subcommand(path_koru: str | None) -> bool | None:
    """Probe whether ``koru auto`` works on the executable first on PATH."""
    if not path_koru:
        return None
    try:
        proc = subprocess.run(
            [path_koru, "auto", "--help"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    combined = f"{proc.stdout or ''}\n{proc.stderr or ''}"
    if "unrecognized arguments: auto" in combined:
        return False
    if proc.returncode == 0 and (
        "koru autonomous" in combined or "alias:" in combined.lower()
    ):
        return True
    return proc.returncode == 0 if proc.returncode == 0 else False


def _koru_path_version_issues(
    project_koru: Path,
    path_koru: str | None,
    package_version: str | None,
    source_version: str | None,
) -> tuple[str, list[str]]:
    """Return (status, extra_bits) for path-mismatch and version checks."""
    status = PASS
    bits: list[str] = []
    if project_koru.is_file() and path_koru:
        try:
            if Path(path_koru).resolve() != project_koru.resolve():
                status = WARN
                bits.append("path_mismatch=true")
        except OSError:
            status = WARN
            bits.append("path_mismatch=unknown")
    auto_ok = _path_koru_supports_auto_subcommand(path_koru)
    if auto_ok is False:
        status = WARN
        bits.append("koru_auto_unsupported=true")
        if project_koru.is_file():
            bits.append(
                f"fix=export PATH={project_koru.parent}:$PATH; hash -r; or {project_koru} auto"
            )
        else:
            bits.append("fix=pip install -e . && use koru autonomous")
    if package_version and source_version and package_version != source_version:
        status = WARN
        bits.append("version_mismatch=true")
    if package_version is None:
        status = WARN
        bits.append("package_metadata=missing")
    return status, bits


def _check_koru_runtime_identity(project: Path) -> tuple[str, str]:
    package_version = _installed_koru_version()
    source_version = _read_project_version(project / "pyproject.toml")
    path_koru = shutil.which("koru")
    project_koru = project / ".venv" / "bin" / "koru"
    detail_bits = [
        f"python={sys.executable}",
        f"package={package_version or '-'}",
        f"source_pyproject={source_version or '-'}",
        f"path_koru={path_koru or '-'}",
    ]
    if project_koru.is_file():
        detail_bits.append(f"project_venv_koru={project_koru}")
    status, extra_bits = _koru_path_version_issues(
        project_koru, path_koru, package_version, source_version
    )
    detail_bits.extend(extra_bits)
    return status, "; ".join(detail_bits)


def _is_relative_to(path: Path, parent: Path) -> bool:
    # Use lexical containment rather than ``resolve()`` for the child:
    # virtualenv Python binaries are often symlinks to /usr/bin/python,
    # but the operator still launched the interpreter from project .venv.
    try:
        child = path.expanduser()
        if not child.is_absolute():
            child = Path.cwd() / child
        child.absolute().relative_to(parent.expanduser().resolve())
    except (OSError, ValueError):
        return False
    return True


def _check_python_venv_alignment(project: Path) -> tuple[str, str]:
    project_venv = project / ".venv"
    virtual_env = os.environ.get("VIRTUAL_ENV", "").strip()
    executable = Path(sys.executable)
    python_from_project_venv = _is_relative_to(executable, project_venv)
    detail_bits = [
        f"virtual_env={virtual_env or '-'}",
        f"python={sys.executable}",
        f"project_venv={project_venv}",
    ]
    if not project_venv.exists():
        return WARN, "; ".join(detail_bits + ["project_venv_missing=true"])

    status = PASS
    if virtual_env:
        try:
            if Path(virtual_env).expanduser().resolve() != project_venv.resolve():
                status = WARN
                detail_bits.append("virtual_env_mismatch=true")
        except OSError:
            status = WARN
            detail_bits.append("virtual_env_mismatch=unknown")
    else:
        detail_bits.append("virtual_env_unset=true")

    if not python_from_project_venv:
        status = WARN
        detail_bits.append("python_not_from_project_venv=true")

    path_koru = shutil.which("koru")
    if path_koru and not _is_relative_to(Path(path_koru), project_venv):
        status = WARN
        detail_bits.append("path_koru_not_from_project_venv=true")
    return status, "; ".join(detail_bits)


def _read_json_file(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _package_lock_root_version(package_lock: dict[str, object] | None) -> str:
    if not package_lock:
        return ""
    packages = package_lock.get("packages")
    if not isinstance(packages, dict):
        return ""
    root = packages.get("")
    if not isinstance(root, dict):
        return ""
    return str(root.get("version") or "")


def _autopilot_plugin_bundle_paths(project: Path, plugin_dir: Path) -> tuple[Path, Path]:
    expected = EXPECTED_VSCODE_PLUGIN_VERSION
    return (
        project
        / "src"
        / "koru"
        / "assets"
        / "koru-autopilot-vscode"
        / f"koru-autopilot-{expected}.vsix",
        plugin_dir / f"koru-autopilot-{expected}.vsix",
    )


def _autopilot_plugin_bundle_detail_bits(
    *,
    package_version: str,
    lock_version: str,
    root_lock_version: str,
    local_vsix: Path,
    asset: Path,
) -> list[str]:
    expected = EXPECTED_VSCODE_PLUGIN_VERSION
    return [
        f"expected={expected}",
        f"package={package_version or '-'}",
        f"lock={lock_version or '-'}",
        f"lock_root={root_lock_version or '-'}",
        f"local_vsix={'present' if local_vsix.is_file() else 'missing'}",
        f"asset_vsix={'present' if asset.is_file() else 'missing'}",
    ]


def _autopilot_plugin_bundle_issues(
    *,
    package_json: dict[str, object] | None,
    package_lock: dict[str, object] | None,
    package_version: str,
    lock_version: str,
    root_lock_version: str,
    local_vsix: Path,
    asset: Path,
) -> list[str]:
    expected = EXPECTED_VSCODE_PLUGIN_VERSION
    issues: list[str] = []
    version_checks = (
        ("package_version_mismatch", package_version),
        ("lock_version_mismatch", lock_version),
        ("lock_root_version_mismatch", root_lock_version),
    )
    if not package_json:
        issues.append("package_json_unreadable")
    if not package_lock:
        issues.append("package_lock_unreadable")
    for label, version in version_checks:
        if version and version != expected:
            issues.append(label)
    if not local_vsix.is_file():
        issues.append("local_vsix_missing")
    if not asset.is_file():
        issues.append("asset_vsix_missing")
    return issues


def _check_autopilot_plugin_bundle(project: Path) -> tuple[str, str]:
    plugin_dir = project / "plugins" / "koru-autopilot-vscode"
    if not plugin_dir.is_dir():
        return SKIP, "plugin source tree not present"
    package_json = _read_json_file(plugin_dir / "package.json")
    package_lock = _read_json_file(plugin_dir / "package-lock.json")
    package_version = str(package_json.get("version") or "") if package_json else ""
    lock_version = str(package_lock.get("version") or "") if package_lock else ""
    root_lock_version = _package_lock_root_version(package_lock)
    asset, local_vsix = _autopilot_plugin_bundle_paths(project, plugin_dir)
    detail_bits = _autopilot_plugin_bundle_detail_bits(
        package_version=package_version,
        lock_version=lock_version,
        root_lock_version=root_lock_version,
        local_vsix=local_vsix,
        asset=asset,
    )
    issues = _autopilot_plugin_bundle_issues(
        package_json=package_json,
        package_lock=package_lock,
        package_version=package_version,
        lock_version=lock_version,
        root_lock_version=root_lock_version,
        local_vsix=local_vsix,
        asset=asset,
    )
    if issues:
        return WARN, "; ".join(detail_bits + [f"issues={','.join(issues)}"])
    return PASS, "; ".join(detail_bits + ["bundle=consistent"])


def _autopilot_env_snapshot() -> dict[str, str]:
    return {
        "instance": (os.environ.get("KORU_AUTOPILOT_INSTANCE") or "").strip(),
        "ide": (os.environ.get("KORU_AUTOPILOT_IDE") or "").strip(),
        "socket_env": (os.environ.get("KORU_AUTOPILOT_SOCKET") or "").strip(),
        "terminal": detect_terminal_host_ide_id() or "-",
        "session": os.environ.get("XDG_SESSION_TYPE") or "-",
        "runtime": os.environ.get("XDG_RUNTIME_DIR") or "-",
    }


def _autopilot_env_detail_bits(values: dict[str, str]) -> list[str]:
    return [
        f"instance={values['instance'] or '-'}",
        f"ide={values['ide'] or '-'}",
        f"socket_env={values['socket_env'] or '-'}",
        f"terminal_hint={values['terminal']}",
        f"session={values['session']}",
        f"runtime={values['runtime']}",
    ]


def _autopilot_env_status(values: dict[str, str]) -> tuple[str, list[str]]:
    normalized_instance = normalize_ide_id(values["instance"])
    normalized_ide = normalize_ide_id(values["ide"])
    if normalized_instance and normalized_ide and normalized_instance != normalized_ide:
        return WARN, ["instance_ide_mismatch=true"]
    if not _selected_autopilot_ide(include_terminal_hint=True):
        return SKIP, ["autopilot_env=unset"]
    if not (values["instance"] or values["ide"] or values["socket_env"]):
        return WARN, ["autopilot_env=unset", "using_terminal_hint=true"]
    return PASS, []


def _check_autopilot_env(_project: Path) -> tuple[str, str]:
    values = _autopilot_env_snapshot()
    status, extra_bits = _autopilot_env_status(values)
    return status, "; ".join(_autopilot_env_detail_bits(values) + extra_bits)


def _check_ide_runtime_presence(_project: Path) -> tuple[str, str]:
    selected = _selected_autopilot_ide()
    running = detect_running_ides()
    ids = [item.id for item in running]
    detail = f"selected={selected or '-'}; running={', '.join(ids) or '-'}"
    if not selected:
        return SKIP, detail
    if selected not in ids:
        return WARN, detail + "; selected_ide_not_running=true"
    return PASS, detail


def _check_autopilot_socket(_project: Path) -> tuple[str, str]:
    if not _has_autopilot_selection():
        return SKIP, "autopilot env unset"
    path = _resolve_autopilot_socket_for_doctor()
    health = probe_socket_health(path)
    detail = (
        f"path={health.path}; exists={health.exists}; "
        f"listening={health.listening}; stale={health.stale}"
    )
    if health.healthy:
        return PASS, detail
    if health.stale:
        return WARN, detail + "; restart daemon or remove stale socket"
    return WARN, detail + "; daemon not listening yet"


def _check_autopilot_manage(_project: Path) -> tuple[str, str]:
    if not _has_autopilot_selection():
        return SKIP, "autopilot env unset"
    selected = _selected_autopilot_ide() or "auto"
    report = collect_install_manager_report(
        ide=selected,
        socket_path=_resolve_autopilot_socket_for_doctor(),
    )
    issue_rows = [issue.to_dict() for issue in report.issues]
    severities = {str(row.get("severity")) for row in issue_rows}
    issue_codes = ", ".join(str(row.get("code")) for row in issue_rows) or "-"
    plugin = report.plugin
    daemon_running = bool(report.daemon.get("running"))
    detail = (
        f"ide={plugin.get('ide')}; daemon={'running' if daemon_running else 'stopped'}; "
        f"socket={report.socket}; connected={plugin.get('connected')}; "
        f"connected_version={plugin.get('connected_version') or '-'}; "
        f"installed={plugin.get('installed_version') or '-'}; "
        f"expected={plugin.get('expected_version') or '-'}; issues={issue_codes}"
    )
    if "error" in severities:
        return FAIL, detail
    if severities:
        return WARN, detail
    return PASS, detail


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
    parts = line.split(maxsplit=2)
    if len(parts) < 2 or not parts[0][:4].isdigit():
        return ""
    return parts[1]


def _autopilot_debug_event_has(line: str, token: str) -> bool:
    event_name = _autopilot_debug_event_name(line)
    if event_name == token:
        return True
    return event_name == "OUT" and token in line


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


def _recent_autopilot_debug_context() -> tuple[str | None, Path, str, list[str], str | None]:
    selected = _selected_autopilot_ide()
    path = _autopilot_debug_log_path()
    if not selected:
        return selected, path, "", [], "autopilot env unset"
    if not path.is_file():
        return selected, path, "", [], f"{path} missing"
    socket_text = str(_resolve_autopilot_socket_for_doctor())
    lines = _read_recent_autopilot_debug_lines(path)
    relevant = [
        line
        for line in lines
        if _autopilot_line_mentions_selected(line, selected=selected, socket_text=socket_text)
    ]
    return selected, path, socket_text, relevant, None


def _check_autopilot_debug_log(_project: Path) -> tuple[str, str]:
    try:
        selected, path, socket_text, relevant, skip_reason = _recent_autopilot_debug_context()
    except OSError as exc:
        path = _autopilot_debug_log_path()
        return WARN, f"cannot read {path}: {exc}"
    if skip_reason:
        return SKIP, skip_reason
    if not relevant:
        return WARN, f"{path}: no recent entries for ide={selected} or socket={socket_text}"
    if any("CONNECT_OK" in line or "HELLO" in line for line in relevant):
        return PASS, f"{path}: {len(relevant)} recent matching entrie(s)"
    if any("CONNECT_ERROR" in line for line in relevant):
        return WARN, f"{path}: {len(relevant)} matching entrie(s), latest connection errors present"
    return PASS, f"{path}: {len(relevant)} recent matching entrie(s)"


def _activity_line_mentions_selected(line: str, selected: str) -> bool:
    return (
        f"ide={selected}" in line
        or f"'ide': '{selected}'" in line
        or f'"ide": "{selected}"' in line
        or f'"ide":"{selected}"' in line
    )


def _count_daemon_metrics(activity: list[str]) -> tuple[int, int, int, int]:
    """Count daemon success/failure metrics from activity lines."""
    daemon_successes = sum(
        any(token in line for token in ("autopilot: ok", "drive wynik: ok=True", "message.sent"))
        for line in activity
    )
    daemon_failures = sum(
        any(token in line for token in ("verification=plugin_error", "autopilot skipped"))
        for line in activity
    )
    last_activity_success_index = max(
        (
            idx
            for idx, line in enumerate(activity)
            if any(
                token in line
                for token in ("autopilot: ok", "drive wynik: ok=True", "message.sent")
            )
        ),
        default=-1,
    )
    last_activity_failure_index = max(
        (
            idx
            for idx, line in enumerate(activity)
            if any(token in line for token in ("verification=plugin_error", "autopilot skipped"))
        ),
        default=-1,
    )
    return daemon_successes, daemon_failures, last_activity_success_index, last_activity_failure_index


def _count_chat_control_metrics(relevant: list[str]) -> dict[str, int | int]:
    """Count various chat control metrics from relevant lines."""
    fast_send_errors = sum(
        _autopilot_debug_event_has(line, "WINDSURF_FASTPATH_EXECUTE_SEND_ERROR")
        for line in relevant
    )
    paste_failures = sum(
        _autopilot_debug_event_has(line, "chat opened but paste command failed")
        for line in relevant
    )
    focus_rejections = sum(
        _autopilot_debug_event_has(line, "PROBE_FOCUS_REJECT")
        for line in relevant
    )
    paste_rejections = sum(
        _autopilot_debug_event_has(line, "PROBE_PASTE_REJECT")
        for line in relevant
    )
    input_refusals = sum(
        _autopilot_debug_event_has(line, token)
        for line in relevant
        for token in (
            "HOST_PASTE_NO_INPUT_FOCUS",
            "PROBE_PASTE_NO_INPUT_FOCUS",
            "TYPE_PASTE_NO_INPUT_FOCUS_REFUSED",
            "FOCUS_INPUT_ALL_FAILED",
        )
    )
    send_successes = sum(
        _autopilot_debug_event_has(line, token)
        for line in relevant
        for token in (
            "WINDSURF_FASTPATH_EXECUTE_SEND_OK",
            "winning_paste=windsurf.sendTextToChat",
            "winning_submit=windsurf.sendTextToChat",
            "message.sent",
        )
    )
    return {
        "fast_send_errors": fast_send_errors,
        "paste_failures": paste_failures,
        "focus_rejections": focus_rejections,
        "paste_rejections": paste_rejections,
        "input_refusals": input_refusals,
        "send_successes": send_successes,
    }


def _calculate_command_indices(relevant: list[str]) -> tuple[int, int]:
    """Calculate indices of command availability/missing events."""
    command_available_index = max(
        (
            idx
            for idx, line in enumerate(relevant)
            if _autopilot_debug_event_has(line, "WINDSURF_FASTPATH_CHECK_COMMAND")
            and '"hasSendCmd":true' in line
        ),
        default=-1,
    )
    command_missing_index = max(
        (
            idx
            for idx, line in enumerate(relevant)
            if _autopilot_debug_event_has(line, "WINDSURF_FASTPATH_ABORT_MISSING_COMMAND")
            or (
                _autopilot_debug_event_has(line, "WINDSURF_FASTPATH_CHECK_COMMAND")
                and '"hasSendCmd":false' in line
            )
        ),
        default=-1,
    )
    return command_available_index, command_missing_index


def _calculate_success_failure_indices(relevant: list[str]) -> tuple[int, int]:
    """Calculate indices of last success/failure events."""
    last_failure_index = max(
        (
            idx
            for idx, line in enumerate(relevant)
            if any(
                _autopilot_debug_event_has(line, token)
                for token in (
                    "WINDSURF_FASTPATH_EXECUTE_SEND_ERROR",
                    "chat opened but paste command failed",
                    "PROBE_FOCUS_REJECT",
                    "PROBE_PASTE_REJECT",
                    "HOST_PASTE_NO_INPUT_FOCUS",
                    "PROBE_PASTE_NO_INPUT_FOCUS",
                    "TYPE_PASTE_NO_INPUT_FOCUS_REFUSED",
                    "FOCUS_INPUT_ALL_FAILED",
                )
            )
        ),
        default=-1,
    )
    last_success_index = max(
        (
            idx
            for idx, line in enumerate(relevant)
            if any(
                _autopilot_debug_event_has(line, token)
                for token in (
                    "WINDSURF_FASTPATH_EXECUTE_SEND_OK",
                    "message.sent",
                    "winning_paste=windsurf.sendTextToChat",
                    "winning_submit=windsurf.sendTextToChat",
                )
            )
        ),
        default=-1,
    )
    return last_success_index, last_failure_index


def _build_chat_control_detail_bits(
    selected: str,
    relevant: list[str],
    chat_metrics: dict[str, int],
    daemon_successes: int,
    daemon_failures: int,
    activity: list[str],
    command_available: bool,
    command_missing_index: int,
) -> list[str]:
    """Build detail bits for chat control check."""
    detail_bits = [
        f"ide={selected}",
        f"entries={len(relevant)}",
        f"fast_send_errors={chat_metrics['fast_send_errors']}",
        f"paste_failures={chat_metrics['paste_failures']}",
        f"focus_rejections={chat_metrics['focus_rejections']}",
        f"paste_rejections={chat_metrics['paste_rejections']}",
        f"input_refusals={chat_metrics['input_refusals']}",
        f"send_successes={chat_metrics['send_successes']}",
    ]
    if activity:
        detail_bits.append(f"daemon_events={len(activity)}")
    if daemon_successes:
        detail_bits.append(f"daemon_successes={daemon_successes}")
    if daemon_failures:
        detail_bits.append(f"daemon_failures={daemon_failures}")
    if command_available:
        detail_bits.append("native_send_command=available")
    if command_missing_index >= 0:
        detail_bits.append("native_send_command_missing_seen=true")
    return detail_bits


def _check_autopilot_chat_control(project: Path) -> tuple[str, str]:
    try:
        selected, path, _socket_text, relevant, skip_reason = _recent_autopilot_debug_context()
    except OSError as exc:
        path = _autopilot_debug_log_path()
        return WARN, f"cannot read {path}: {exc}"
    if skip_reason:
        return SKIP, skip_reason
    if not relevant:
        return WARN, f"{path}: no recent chat-control entries for ide={selected}"

    activity = [
        line
        for line in _read_recent_autopilot_activity_lines(project)
        if selected and _activity_line_mentions_selected(line, selected)
    ]
    daemon_successes, daemon_failures, last_activity_success_index, last_activity_failure_index = _count_daemon_metrics(activity)
    chat_metrics = _count_chat_control_metrics(relevant)
    command_available_index, command_missing_index = _calculate_command_indices(relevant)
    last_success_index, last_failure_index = _calculate_success_failure_indices(relevant)

    command_available = command_available_index >= 0
    command_missing_latest = command_missing_index > max(
        command_available_index,
        last_success_index,
    )
    detail_bits = _build_chat_control_detail_bits(
        selected,
        relevant,
        chat_metrics,
        daemon_successes,
        daemon_failures,
        activity,
        command_available,
        command_missing_index,
    )

    if command_missing_latest:
        return WARN, "; ".join(detail_bits + ["native chat command unavailable"])
    if any(
        (
            chat_metrics["fast_send_errors"],
            chat_metrics["paste_failures"],
            chat_metrics["focus_rejections"],
            chat_metrics["paste_rejections"],
            chat_metrics["input_refusals"],
        )
    ):
        if (
            last_success_index > last_failure_index >= 0
            or last_activity_success_index > last_activity_failure_index
        ):
            detail_bits.append("recovered_after_retry=true")
        else:
            detail_bits.append("latest_chat_control_failure=true")
        return WARN, "; ".join(detail_bits)
    if chat_metrics["send_successes"] or daemon_successes:
        return PASS, "; ".join(detail_bits + ["chat_control=stable"])
    return WARN, "; ".join(detail_bits + ["no recent paste/submit success observed"])


def _windsurf_chat_column_indexes(relevant: list[str]) -> dict[str, list[int]]:
    return {
        "send": [
            idx
            for idx, line in enumerate(relevant)
            if _autopilot_debug_event_has(line, "WINDSURF_FASTPATH_EXECUTE_SEND_OK")
            or "winning_paste=windsurf.sendTextToChat" in line
        ],
        "disabled": [
            idx
            for idx, line in enumerate(relevant)
            if _autopilot_debug_event_has(line, "WINDSURF_KEEP_OPEN_DISABLED")
        ],
        "keep_open_ok": [
            idx
            for idx, line in enumerate(relevant)
            if _autopilot_debug_event_has(line, "WINDSURF_KEEP_OPEN_OK")
        ],
        "cascade_toggle": [
            idx
            for idx, line in enumerate(relevant)
            if _autopilot_debug_event_has(line, "WINDSURF_KEEP_OPEN_OK")
            and _windsurf_line_mentions_chat_open_command(line)
        ],
    }


def _windsurf_line_mentions_chat_open_command(line: str) -> bool:
    return any(
        marker in line
        for marker in ("cascadePanel.open", "showCascade", "openChat", "panel.chat")
    )


def _windsurf_chat_column_detail_bits(
    relevant: list[str],
    indexes: dict[str, list[int]],
) -> list[str]:
    return [
        "ide=windsurf",
        f"entries={len(relevant)}",
        f"native_sends={len(indexes['send'])}",
        f"keep_open_ok={len(indexes['keep_open_ok'])}",
        f"post_send_toggle_candidates={len(indexes['cascade_toggle'])}",
        f"keep_open_disabled={len(indexes['disabled'])}",
    ]


def _windsurf_chat_column_result(
    indexes: dict[str, list[int]],
    detail_bits: list[str],
) -> tuple[str, str]:
    last_send = max(indexes["send"], default=-1)
    last_disabled = max(indexes["disabled"], default=-1)
    last_toggle = max(indexes["cascade_toggle"], default=-1)
    if last_toggle > last_disabled and last_toggle > -1:
        return WARN, "; ".join(
            detail_bits
            + [
                "risk=post_send_cascade_open_may_toggle_right_chat_column",
                "upgrade_plugin_or_keep koruAutopilot.windsurfKeepOpenAfterSend=false",
            ]
        )
    if last_disabled > last_send >= 0:
        return PASS, "; ".join(detail_bits + ["post_send_keep_open_guard=disabled"])
    if last_send >= 0 and not indexes["disabled"] and not indexes["keep_open_ok"]:
        return WARN, "; ".join(
            detail_bits
            + ["post_send_keep_open_guard=unknown", "reload IDE if plugin was just upgraded"]
        )
    return PASS, "; ".join(detail_bits + ["no post-send toggle evidence"])


def _check_windsurf_chat_column_control(_project: Path) -> tuple[str, str]:
    try:
        selected, path, _socket_text, relevant, skip_reason = _recent_autopilot_debug_context()
    except OSError as exc:
        path = _autopilot_debug_log_path()
        return WARN, f"cannot read {path}: {exc}"
    if skip_reason:
        return SKIP, skip_reason
    if selected != "windsurf":
        return SKIP, f"ide={selected or '-'}; only applicable to windsurf"
    if not relevant:
        return WARN, f"{path}: no recent Windsurf chat-column entries"

    indexes = _windsurf_chat_column_indexes(relevant)
    detail_bits = _windsurf_chat_column_detail_bits(relevant, indexes)
    return _windsurf_chat_column_result(indexes, detail_bits)


def _doctor_console_log_tail_limit() -> int:
    raw = os.environ.get("KORU_DOCTOR_CONSOLE_LOG_LINES", "").strip()
    if not raw:
        return 8
    try:
        value = int(raw)
    except ValueError:
        return 8
    return min(max(value, 1), 40)


def _compact_plugin_console_entry(entry: dict[str, object], *, max_len: int = 220) -> str:
    timestamp = str(entry.get("timestamp") or "-").strip()
    ide = str(entry.get("ide") or "-").strip()
    message = str(entry.get("message") or "").strip()
    data = entry.get("data")
    if data is None:
        data_text = ""
    else:
        try:
            data_text = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError):
            data_text = str(data)
    text = " ".join(part for part in (timestamp, ide, message, data_text) if part)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        text = text[: max_len - 3].rstrip() + "..."
    return text


def _plugin_console_entry_matches_selected(entry: dict[str, object], selected: str) -> bool:
    ide = normalize_ide_id(str(entry.get("ide") or ""))
    if ide:
        return ide == selected
    data = entry.get("data")
    if isinstance(data, dict):
        data_ide = normalize_ide_id(str(data.get("ide") or ""))
        if data_ide:
            return data_ide == selected
    message = str(entry.get("message") or "")
    if selected == "windsurf" and "WINDSURF_" in message:
        return True
    if selected == "antigravity" and "ANTIGRAVITY_" in message:
        return True
    return not ide


def _daemon_console_logs_for_doctor(
    socket_path: Path,
) -> tuple[list[dict[str, object]], str | None]:
    try:
        from koru.autopilot.client import AutopilotClient

        status = AutopilotClient(socket_path=socket_path, timeout=1.5).status()
    except (OSError, RuntimeError) as exc:
        return [], str(exc)
    raw_logs = status.get("console_logs")
    if not isinstance(raw_logs, list):
        return [], None
    return [row for row in raw_logs if isinstance(row, dict)], None


def _plugin_debug_log_tail_for_doctor(limit: int) -> tuple[Path, list[str], str | None]:
    try:
        _selected, path, _socket_text, relevant, skip_reason = _recent_autopilot_debug_context()
    except OSError as exc:
        path = _autopilot_debug_log_path()
        return path, [], str(exc)
    if skip_reason:
        return path, [], skip_reason
    return path, relevant[-limit:], None


def _check_plugin_console_logs(_project: Path) -> tuple[str, str]:
    """Show recent extension-host console logs forwarded by the plugin."""
    selected = _selected_autopilot_ide()
    if not selected:
        return SKIP, "autopilot env unset"
    limit = _doctor_console_log_tail_limit()
    socket_path = _resolve_autopilot_socket_for_doctor()
    daemon_logs, daemon_error = _daemon_console_logs_for_doctor(socket_path)
    selected_logs = [
        entry
        for entry in daemon_logs
        if _plugin_console_entry_matches_selected(entry, selected)
    ]
    if selected_logs:
        tail = selected_logs[-limit:]
        latest = " | ".join(_compact_plugin_console_entry(entry) for entry in tail)
        return PASS, (
            f"ide={selected}; source=daemon; socket={socket_path}; "
            f"entries={len(selected_logs)}; latest={latest}"
        )

    debug_path, debug_tail, debug_error = _plugin_debug_log_tail_for_doctor(limit)
    if debug_tail:
        latest = " | ".join(re.sub(r"\s+", " ", line).strip() for line in debug_tail)
        offline_after_stop = _plugin_debug_tail_is_daemon_offline_noise(
            debug_tail,
            selected=selected,
            socket_path=socket_path,
            daemon_error=daemon_error,
        )
        status = PASS if offline_after_stop or not daemon_error else WARN
        reason = f"; daemon_status_error={daemon_error}" if daemon_error else ""
        if offline_after_stop:
            reason = f"; daemon_offline_expected_after_stop=true{reason}"
        return status, (
            f"ide={selected}; source=plugin_debug_log; path={debug_path}; "
            f"entries={len(debug_tail)}; latest={latest}{reason}"
        )
    if daemon_error:
        return WARN, f"ide={selected}; socket={socket_path}; daemon_status_error={daemon_error}"
    if debug_error:
        return WARN, (
            f"ide={selected}; source=daemon; entries=0; debug_log={debug_path}; "
            f"debug_error={debug_error}"
        )
    return WARN, (
        f"ide={selected}; source=daemon; socket={socket_path}; "
        "no console logs received yet"
    )


def _plugin_debug_tail_is_daemon_offline_noise(
    lines: list[str],
    *,
    selected: str,
    socket_path: Path,
    daemon_error: str | None,
) -> bool:
    if not daemon_error:
        return False
    error_text = daemon_error.lower()
    if "no such file" not in error_text and "enoent" not in error_text:
        return False

    allowed = {"CONNECT_CANDIDATES", "CONNECT_TRY", "CONNECT_ERROR", "CONNECT_CLOSE"}
    socket_text = str(socket_path)
    for line in lines:
        event = _autopilot_debug_event_name(line)
        if event not in allowed:
            return False
        if selected not in line and socket_text not in line:
            return False
    return any(_autopilot_debug_event_has(line, "CONNECT_ERROR") for line in lines)


def _ide_console_log_roots(selected: str) -> list[Path]:
    override = os.environ.get("KORU_IDE_CONSOLE_LOG_DIR")
    if override:
        return [Path(override).expanduser()]
    home = Path.home()
    roots: dict[str, list[Path]] = {
        "windsurf": [home / ".config" / "Windsurf" / "logs"],
        "antigravity": [home / ".config" / "Antigravity" / "logs"],
        "vscode": [home / ".config" / "Code" / "logs"],
        "vscodium": [home / ".config" / "VSCodium" / "logs"],
        "cursor": [home / ".config" / "Cursor" / "logs"],
    }
    return roots.get(selected, [])


def _recent_ide_console_log_files(selected: str, *, max_sessions: int = 5) -> list[Path]:
    files: list[Path] = []
    for root in _ide_console_log_roots(selected):
        if not root.is_dir():
            continue
        sessions = sorted(
            (path for path in root.iterdir() if path.is_dir()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )[:max_sessions]
        root_files = [path for path in root.iterdir() if path.is_file()]
        for session in sessions:
            files.extend(
                path
                for path in session.rglob("*")
                if path.is_file() and path.suffix.lower() in {".log", ".txt"}
            )
        files.extend(path for path in root_files if path.suffix.lower() in {".log", ".txt"})
    return sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)


def _read_recent_ide_console_lines(
    files: list[Path],
    *,
    per_file_limit: int = 120,
) -> list[tuple[Path, str]]:
    rows: list[tuple[Path, str]] = []
    for path in files[:30]:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        rows.extend((path, line) for line in lines[-per_file_limit:] if line.strip())
    return rows


def _ide_console_line_is_interesting(line: str) -> bool:
    lowered = line.lower()
    tokens = (
        "[error]",
        " error ",
        " err ",
        "[warn]",
        " warn ",
        "warning",
        "exception",
        "rejected promise",
        "trustedscript",
        "trustedtypepolicy",
        "trustedstring",
        "trusted types",
        "language server has not been started",
        "cannot register",
        "already registered",
        "overwriting grammar scope",
        "marketplace",
        "404",
        "500",
        "acknowledgecascadecodeedit",
        "file or directory",
        "does not exist",
        "unable to read file",
        "app icon customization is not supported",
        "failed to find pyright executable",
        "lifecyclephase.restored",
        "extension host",
        "koru",
        "windsurf",
        "cascade",
        "chat",
    )
    return any(token in lowered for token in tokens)


def _ide_console_line_is_diagnostic_headline(line: str) -> bool:
    stripped = line.strip()
    if stripped.startswith("at ") or stripped.startswith("at async "):
        return False
    lowered = stripped.lower()
    return any(
        token in lowered
        for token in (
            "[error]",
            "[warn]",
            "console.error",
            "console.warn",
            " error:",
            " warn ",
            " warning",
            "rejected promise",
            "trustedscript",
            "trustedtypepolicy",
            "trustedstring",
            "trusted types",
            "language server has not been started",
            "cannot register",
            "already registered",
            "overwriting grammar scope",
            "marketplace",
            "acknowledgecascadecodeedit",
            "file or directory",
            "does not exist",
            "unable to read file",
            "app icon customization is not supported",
            "failed to find pyright executable",
            "lifecyclephase.restored",
        )
    )


def _compact_console_excerpt(path: Path, line: str, *, max_len: int = 220) -> str:
    text = re.sub(r"\s+", " ", line).strip()
    if len(text) > max_len:
        text = text[: max_len - 3].rstrip() + "..."
    parent = path.parent.name
    label = f"{parent}/{path.name}" if parent else path.name
    return f"{label}: {text}"


_IDE_CONSOLE_WARN_TOKENS: tuple[str, ...] = (
    "warn",
    "trustedscript",
    "trustedtypepolicy",
    "trustedstring",
    "trusted types",
    "rejected promise",
    "cannot register",
    "already registered",
    "overwriting grammar scope",
    "language server has not been started",
    "lifecyclephase.restored",
)

_IDE_CONSOLE_CATEGORY_PATTERNS: dict[str, tuple[tuple[str, ...], ...]] = {
    "trusted_types": (
        ("trustedscript",),
        ("trustedtypepolicy",),
        ("trustedstring",),
        ("trusted types",),
    ),
    "language_server_not_started": (("language server has not been started",),),
    "extension_registration": (("cannot register",), ("already registered",)),
    "grammar_scope_overwrite": (("overwriting grammar scope",),),
    "missing_extension_file": (("unable to read file", "nonexistent file"),),
    "missing_workspace_path": (("file or directory", "does not exist"),),
    "marketplace_404": (("marketplace", "404"),),
    "cascade_rpc_500": (("acknowledgecascadecodeedit", "500"),),
    "cascade_panel_early_restore": (("windsurf.cascadepanel", "lifecyclephase.restored"),),
    "app_icon_unsupported": (("app icon customization is not supported",),),
    "pyright_fallback": (("failed to find pyright executable",),),
}


def _ide_console_error_count(headlines: list[tuple[Path, str]]) -> int:
    return sum("error" in line.lower() or "[err" in line.lower() for _path, line in headlines)


def _ide_console_warn_count(headlines: list[tuple[Path, str]]) -> int:
    return sum(
        any(token in line.lower() for token in _IDE_CONSOLE_WARN_TOKENS)
        for _path, line in headlines
    )


def _ide_console_category_counts(interesting: list[tuple[Path, str]]) -> list[str]:
    counts: list[str] = []
    for name, patterns in _IDE_CONSOLE_CATEGORY_PATTERNS.items():
        count = sum(
            any(all(token in line.lower() for token in pattern) for pattern in patterns)
            for _path, line in interesting
        )
        if count:
            counts.append(f"{name}={count}")
    return counts


def _classify_ide_console_lines(
    rows: list[tuple[Path, str]],
) -> tuple[list[tuple[Path, str]], list[tuple[Path, str]], list[tuple[Path, str]]]:
    """Return (interesting, headlines, sample_rows) from raw log rows."""
    interesting = [
        (path, line) for path, line in rows if _ide_console_line_is_interesting(line)
    ]
    headlines = [
        (path, line)
        for path, line in interesting
        if _ide_console_line_is_diagnostic_headline(line)
    ]
    sample_rows = headlines or interesting
    return interesting, headlines, sample_rows


def _ide_console_build_detail(
    selected: str,
    existing_roots: list[Path],
    files: list[Path],
    interesting: list[tuple[Path, str]],
    error_count: int,
    warn_count: int,
    category_counts: list[str],
    sample_rows: list[tuple[Path, str]],
) -> str:
    detail = (
        f"ide={selected}; roots={','.join(str(path) for path in existing_roots)}; "
        f"files={len(files)}; interesting={len(interesting)}; errors={error_count}; "
        f"warnings={warn_count}"
    )
    if category_counts:
        detail += "; categories=" + ",".join(category_counts)
    if sample_rows:
        samples = [_compact_console_excerpt(path, line) for path, line in sample_rows[-3:]]
        detail += "; latest=" + " | ".join(samples)
    return detail


def _check_ide_console_log(_project: Path) -> tuple[str, str]:
    selected = _selected_autopilot_ide()
    if not selected:
        return SKIP, "autopilot env unset"
    roots = _ide_console_log_roots(selected)
    if not roots:
        return SKIP, f"no known console log root for ide={selected}"
    existing_roots = [path for path in roots if path.is_dir()]
    if not existing_roots:
        roots_text = ", ".join(str(path) for path in roots)
        return WARN, f"ide={selected}; log root missing: {roots_text}"

    try:
        files = _recent_ide_console_log_files(selected)
        rows = _read_recent_ide_console_lines(files)
    except OSError as exc:
        return WARN, f"ide={selected}; cannot read console logs: {exc}"
    if not files:
        roots_text = ", ".join(str(path) for path in existing_roots)
        return WARN, f"ide={selected}; no log files found under {roots_text}"
    if not rows:
        return WARN, f"ide={selected}; files={len(files)}; no readable recent log lines"

    interesting, headlines, sample_rows = _classify_ide_console_lines(rows)
    error_count = _ide_console_error_count(headlines)
    warn_count = _ide_console_warn_count(headlines)
    category_counts = _ide_console_category_counts(interesting)
    detail = _ide_console_build_detail(
        selected, existing_roots, files, interesting, error_count, warn_count,
        category_counts, sample_rows,
    )
    if error_count or warn_count:
        return WARN, detail
    return PASS, detail + "; no recent warnings/errors"


def _check_git_repo(project: Path) -> tuple[str, str]:
    git = project / ".git"
    if git.is_dir():
        return PASS, "initialised"
    if git.is_file():  # worktree pointer
        return PASS, "git worktree"
    return WARN, "no .git/ — git history is required for CI/CD review"


def _check_planfile_binary(_project: Path) -> tuple[str, str]:
    explicit = os.environ.get("KORU_PLANFILE_CMD")
    if explicit:
        first = shlex.split(explicit)[0] if explicit.strip() else ""
        resolved = shutil.which(first) if first else None
        if resolved or (first and Path(first).is_file()):
            return PASS, f"KORU_PLANFILE_CMD={explicit}"
        return FAIL, f"KORU_PLANFILE_CMD set but not executable: {explicit}"
    on_path = shutil.which("planfile")
    if on_path:
        return PASS, on_path
    return FAIL, "`planfile` not on PATH and KORU_PLANFILE_CMD unset"


def _planfile_version_argv() -> list[str] | None:
    explicit = os.environ.get("KORU_PLANFILE_CMD", "").strip()
    if explicit:
        return shlex.split(explicit) + ["--version"]
    exe = shutil.which("planfile")
    if exe:
        return [exe, "--version"]
    return None


def _check_koru_package_version(_project: Path) -> tuple[str, str]:
    del _project
    try:
        from importlib.metadata import PackageNotFoundError, version

        ver = version("koru")
    except (ImportError, PackageNotFoundError, ValueError):
        return WARN, "koru version metadata unavailable (editable install / src only)"
    return PASS, f"koru {ver}"


def _check_planfile_cli_version(project: Path) -> tuple[str, str]:
    argv = _planfile_version_argv()
    if not argv:
        return SKIP, "no planfile executable"
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=8,
            cwd=str(project.resolve()),
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return WARN, f"planfile --version failed: {exc}"
    blob = f"{proc.stdout or ''}\n{proc.stderr or ''}"
    for line in blob.splitlines():
        if "version" in line.lower() and any(ch.isdigit() for ch in line):
            return PASS, line.strip()[:180]
    return WARN, "planfile --version produced no parseable version line"


def _check_planfile_config(project: Path) -> tuple[str, str]:
    cfg = planfile_dir(project) / "config.yaml"
    if not cfg.exists():
        return FAIL, f"missing {cfg.relative_to(project)} — run `koru --init`"
    try:
        data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return FAIL, f"YAML parse error in {cfg.relative_to(project)}: {exc}"
    if not isinstance(data, dict):
        return FAIL, "config.yaml is not a YAML mapping"
    return PASS, "valid"


def _check_planfile_sprints(project: Path) -> tuple[str, str]:
    sprints = planfile_dir(project) / "sprints"
    if not sprints.is_dir():
        return FAIL, "no .planfile/sprints/ directory"
    yamls = sorted(sprints.glob("*.yaml"))
    if not yamls:
        return FAIL, ".planfile/sprints/ is empty"
    total_tickets = 0
    bad: list[str] = []
    for path in yamls:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            bad.append(path.name)
            continue
        if not isinstance(data, dict):
            bad.append(path.name)
            continue
        sprint = data.get("sprint")
        tickets = sprint.get("tickets") if isinstance(sprint, dict) else None
        if isinstance(tickets, dict):
            total_tickets += len(tickets)
    if bad:
        return FAIL, f"unparseable sprints: {', '.join(bad)}"
    if total_tickets == 0:
        return WARN, f"{len(yamls)} sprint(s), 0 tickets — nothing to drain"
    return PASS, f"{len(yamls)} sprint(s), {total_tickets} ticket(s)"


def _check_planfile_sprints_yaml(project: Path) -> tuple[str, str]:
    sprints = planfile_dir(project) / "sprints"
    if not sprints.is_dir():
        return SKIP, "no .planfile/sprints/ directory"
    yamls = sorted(sprints.glob("*.yaml"))
    if not yamls:
        return SKIP, ".planfile/sprints/ is empty"
    errors = []
    for path in yamls:
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            errors.append(f"{path.name}: {exc}")
    if errors:
        return FAIL, f"YAML parse errors in: {', '.join(errors)}"
    return PASS, "all sprint files have valid YAML syntax"


def _check_runtime_dir(project: Path) -> tuple[str, str]:
    rt = runtime_dir(project)
    if rt.is_dir():
        if os.access(rt, os.W_OK):
            return PASS, ".planfile/.koru/ writable"
        return FAIL, ".planfile/.koru/ exists but is not writable"
    parent = rt.parent
    if parent.is_dir() and os.access(parent, os.W_OK):
        return PASS, ".planfile/.koru/ will be created on first write"
    if not parent.exists():
        return WARN, "no .planfile/ yet — run `koru --init`"
    return FAIL, ".planfile/ exists but is not writable"


def _check_koru_project_pipeline(project: Path) -> tuple[str, str]:
    cfg = planfile_dir(project) / "config.yaml"
    if not cfg.is_file():
        return SKIP, "no planfile config (project not initialised)"
    path = project_pipeline_path(project)
    if not path.is_file():
        return WARN, (
            f"missing {KORU_PROJECT_PIPELINE_FILENAME} — "
            "`koru --init` on a fresh repo creates one; copy from another project or add manually"
        )
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return FAIL, f"{KORU_PROJECT_PIPELINE_FILENAME}: {exc}"
    if not isinstance(data, dict):
        return FAIL, f"{KORU_PROJECT_PIPELINE_FILENAME}: expected YAML mapping at top level"
    schema = data.get("schema")
    if schema is not None and str(schema) not in ("1.0", "1"):
        return WARN, f"unknown schema {schema!r} (expected 1.0)"
    return PASS, f"{KORU_PROJECT_PIPELINE_FILENAME} present"


def _check_policy_yaml(project: Path) -> tuple[str, str]:
    path = policy_path(project)
    if not path.exists():
        return PASS, "absent — strict defaults apply"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return FAIL, (
            "policy.yaml YAML parse error — koru is silently using "
            f"strict defaults: {exc.__class__.__name__}"
        )
    if not isinstance(data, dict):
        return FAIL, "policy.yaml is not a YAML mapping — strict defaults in use"
    llm = data.get("llm")
    if llm is not None and not isinstance(llm, dict):
        return FAIL, "policy.llm must be a mapping"
    # Detect string-truthy values (e.g. allow_commit: "true") which
    # load_policy rejects silently — flag them so the operator sees it.
    if isinstance(llm, dict):
        for key, value in llm.items():
            if (key.startswith("allow_") or key.startswith("require_")) and not isinstance(
                value, bool
            ):
                return WARN, (
                    f"llm.{key} is {type(value).__name__} (must be bool); "
                    "koru is using the strict default for this gate"
                )
    return PASS, "parses; loaded values match schema"


def _check_gitignore(project: Path) -> tuple[str, str]:
    gi = project / ".gitignore"
    if not gi.exists():
        return WARN, ".gitignore missing — runtime artefacts may be committed"
    text = gi.read_text(encoding="utf-8")
    needle = ".planfile/.koru/"
    if any(line.strip() == needle for line in text.splitlines()):
        return PASS, f"ignores {needle}"
    return WARN, f".gitignore does not list {needle} — re-run `koru --init`"


_PYTEST_COLLECT_COUNT_RE = re.compile(r"(\d+)\s+tests?\s+collected", re.IGNORECASE)
_PYTEST_NO_TESTS_RE = re.compile(r"no tests ran|collected 0 items", re.IGNORECASE)


def _resolve_pytest_collect_timeout() -> float:
    """Return the timeout from env var with a safe fallback.

    Env override exists for two reasons: (1) operators on slow CI boxes
    can extend it; (2) tests can shrink it to keep the suite fast.
    Invalid values silently fall back to the default — the operator
    should not be punished for a typo in their shell rc.
    """
    raw = os.environ.get("KORU_DOCTOR_PYTEST_TIMEOUT", "").strip()
    if not raw:
        return DEFAULT_PYTEST_COLLECT_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_PYTEST_COLLECT_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_PYTEST_COLLECT_TIMEOUT_SECONDS


def _compact_pytest_collect_failure(stdout: str, stderr: str) -> str:
    """Return one operator-useful line from a failed pytest collection."""
    combined = f"{stdout or ''}\n{stderr or ''}"
    lines = [line.strip() for line in combined.splitlines() if line.strip()]
    if not lines:
        return ""

    diagnostic_tokens = (
        "error:",
        "error collecting",
        "importerror",
        "modulenotfounderror",
        "syntaxerror",
        "usage:",
        "failed:",
        "traceback",
        "no module named",
        "permission denied",
    )
    for line in lines:
        lowered = line.lower()
        if any(token in lowered for token in diagnostic_tokens):
            return line[:220] + ("..." if len(line) > 220 else "")

    return lines[0][:220] + ("..." if len(lines[0]) > 220 else "")


def _check_pytest_collect(project: Path) -> tuple[str, str]:
    """Run ``pytest --collect-only`` and report whether collection works.

    This is the fast diagnostic counterpart to ``koru scan``'s pytest
    probe. The two share the same root concern — *can pytest even load
    its tests?* — but with different roles:

    - ``koru scan`` creates a ticket when collection fails or times out.
    - ``koru doctor`` returns a status line so the operator can see the
      health of the test infrastructure at a glance, without committing
      anything to the queue.

    Status mapping:
      PASS — exit 0; report N tests collected if parseable.
      WARN — exit non-zero; collection broke. Suggest ``koru scan`` for
             per-file detail rather than dumping pytest's stderr here.
      FAIL — timeout. Strongest signal: pytest is hung, not just broken.
             The operator should treat this as a release blocker.
      SKIP — pytest binary missing; doctor cannot diagnose further.
    """
    timeout_seconds = _resolve_pytest_collect_timeout()
    cmd = get_python_cmd(project) + ["-m", "pytest", "--collect-only", "-q", "--no-header"]
    try:
        result = subprocess.run(
            cmd,
            cwd=project,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return FAIL, (
            f"pytest --collect-only hung > {timeout_seconds:g}s — investigate "
            "heavy conftest imports or runaway test discovery "
            "(see `koru scan` for a queueable ticket with checklist)"
        )
    except (FileNotFoundError, OSError):
        return SKIP, "pytest not invokable (python3/pytest missing on PATH)"

    output = f"{result.stdout or ''}\n{result.stderr or ''}"
    if result.returncode == 0:
        match = _PYTEST_COLLECT_COUNT_RE.search(output)
        if match:
            return PASS, f"{match.group(1)} test(s) collected"
        if _PYTEST_NO_TESTS_RE.search(output):
            return WARN, "0 tests collected — verify testpaths / discovery rules"
        return PASS, "collection clean (count not parseable)"

    # Non-zero exit: collection failed. Keep the detail short — `koru
    # scan` is the place to dig into per-file errors. We include one
    # headline so doctor is still useful when the operator needs the
    # first clue without opening another log.
    detail = "pytest --collect-only failed — run `koru scan` for actionable per-file tickets"
    headline = _compact_pytest_collect_failure(result.stdout or "", result.stderr or "")
    if headline:
        detail = f"{detail}; first_error={headline}"
    return WARN, detail


def _check_inotify_watches(project: Path) -> tuple[str, str]:
    """Check Linux inotify watches limit (for WUP/watchdog file watching stability)."""
    import sys
    del project
    if sys.platform != "linux":
        return SKIP, "only applicable on Linux"

    path = Path("/proc/sys/fs/inotify/max_user_watches")
    if not path.is_file():
        return SKIP, f"{path} not found"

    try:
        limit_str = path.read_text(encoding="utf-8").strip()
        limit = int(limit_str)
        if limit < 524288:
            return FAIL, (
                f"watches limit too low: {limit} (recommend >= 524288; "
                "use `sudo sysctl -w fs.inotify.max_user_watches=1048576` to fix)"
            )
        return PASS, f"limit is {limit} (sufficient)"
    except Exception as exc:
        return WARN, f"could not read limit: {exc}"


def _check_wup_binary(_project: Path) -> tuple[str, str]:
    """Check if the WUP regression testing watcher is available on PATH."""
    import shutil
    on_path = shutil.which("wup")
    if on_path:
        return PASS, on_path
    return WARN, "`wup` not on PATH — WUP-driven hot-reload checks will be skipped"


def _check_ci_command(project: Path) -> tuple[str, str]:
    from koru.policy import load_policy

    policy = load_policy(project)
    if not policy.ci_command.strip():
        return WARN, (
            "policy.ci.command is empty — agent must defer to a human "
            "for CI verification before completing tickets"
        )
    try:
        first = shlex.split(policy.ci_command)[0]
    except ValueError as exc:
        return FAIL, f"ci.command unparseable: {exc}"
    resolved = shutil.which(first)
    if resolved:
        return PASS, f"`{policy.ci_command}` (resolves to {resolved})"
    if Path(first).is_file():
        return PASS, f"`{policy.ci_command}` (file exists)"
    return FAIL, f"ci.command first token `{first}` not on PATH"


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


_STATUS_GLYPH = {PASS: "OK ", WARN: "WARN", FAIL: "FAIL", SKIP: "SKIP"}


def render_text(report: DoctorReport) -> str:
    """Human-readable rendering — fixed-width status column."""
    lines: list[str] = []
    lines.append(f"koru doctor — {report.project}")
    lines.append("")
    width = max((len(c.name) for c in report.checks), default=0)
    for c in report.checks:
        glyph = _STATUS_GLYPH.get(c.status, c.status.upper())
        lines.append(f"  [{glyph}] {c.name.ljust(width)}  {c.detail}")
    counts = report.summary()
    total = sum(counts.values())
    parts = [f"{total} checks"]
    if counts.get(PASS):
        parts.append(f"{counts[PASS]} passed")
    if counts.get(WARN):
        parts.append(f"{counts[WARN]} warning(s)")
    if counts.get(FAIL):
        parts.append(f"{counts[FAIL]} failed")
    lines.append("")
    lines.append(f"  {', '.join(parts)}")

    problems = detected_problems(report)
    if problems:
        lines.append("")
        lines.append("Detected problems:")
        for p in problems:
            glyph = _STATUS_GLYPH.get(p["status"], p["status"].upper())
            lines.append(f"  - [{glyph}] {p['name']}: {p['detail']}")
    return "\n".join(lines)
