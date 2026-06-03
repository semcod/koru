"""Self-control diagnostics and repairs for Koru itself."""

from __future__ import annotations

import importlib.metadata
import json
import shutil
import subprocess
import sys
import tomllib
import urllib.parse
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from koru.autopilot.install_manager import collect_install_manager_report, repair_installation

Runner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class SelfCheck:
    name: str
    status: str
    detail: str
    repair: str = ""

    def to_dict(self) -> dict[str, str]:
        out = {"name": self.name, "status": self.status, "detail": self.detail}
        if self.repair:
            out["repair"] = self.repair
        return out


@dataclass(frozen=True)
class EcosystemComponent:
    name: str
    kind: str
    status: str
    current: str = ""
    expected: str = ""
    repair: str = ""
    detail: str = ""

    @property
    def needs_update(self) -> bool:
        return self.status in {"warn", "fail"} and bool(self.repair)

    def to_dict(self) -> dict[str, str | bool]:
        out: dict[str, str | bool] = {
            "name": self.name,
            "kind": self.kind,
            "status": self.status,
            "needs_update": self.needs_update,
        }
        if self.current:
            out["current"] = self.current
        if self.expected:
            out["expected"] = self.expected
        if self.repair:
            out["repair"] = self.repair
        if self.detail:
            out["detail"] = self.detail
        return out


@dataclass
class SelfControlReport:
    project: Path
    checks: list[SelfCheck] = field(default_factory=list)
    ecosystem_components: list[EcosystemComponent] = field(default_factory=list)
    actions: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return any(check.status == "fail" for check in self.checks)

    @property
    def needs_repair(self) -> bool:
        return any(check.status in {"warn", "fail"} and check.repair for check in self.checks)

    @property
    def ok(self) -> bool:
        return not self.has_failures and not self.needs_repair

    def summary(self) -> dict[str, int]:
        counts = {"ok": 0, "warn": 0, "fail": 0, "skip": 0}
        for check in self.checks:
            counts[check.status] = counts.get(check.status, 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "koru.self-control/v1",
            "project": str(self.project),
            "ok": self.ok,
            "needs_repair": self.needs_repair,
            "summary": self.summary(),
            "checks": [check.to_dict() for check in self.checks],
            "ecosystem_components": [
                component.to_dict() for component in self.ecosystem_components
            ],
            "update_plan": [
                component.to_dict()
                for component in self.ecosystem_components
                if component.needs_update
            ],
            "actions": list(self.actions),
        }


def _run(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )


def _source_version(project: Path) -> str | None:
    try:
        data = tomllib.loads((project / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    version = data.get("project", {}).get("version")
    return str(version) if version else None


def _installed_version() -> str | None:
    try:
        return importlib.metadata.version("koru")
    except importlib.metadata.PackageNotFoundError:
        return None


def _installed_editable_source_root() -> Path | None:
    try:
        dist = importlib.metadata.distribution("koru")
        raw = dist.read_text("direct_url.json")
    except importlib.metadata.PackageNotFoundError:
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    dir_info = data.get("dir_info") if isinstance(data, dict) else None
    if not isinstance(dir_info, dict) or not dir_info.get("editable"):
        return None
    parsed = urllib.parse.urlparse(str(data.get("url") or ""))
    if parsed.scheme != "file":
        return None
    return Path(urllib.parse.unquote(parsed.path)).resolve()


def _check_package_identity(project: Path) -> SelfCheck:
    source = _source_version(project)
    installed = _installed_version()
    detail = f"source={source or '-'}; installed={installed or '-'}; python={sys.executable}"
    if source and installed and source != installed:
        return SelfCheck(
            "package_identity",
            "warn",
            detail + "; version_mismatch=true",
            repair=f"{sys.executable} -m pip install -e {project}",
        )
    if installed is None:
        return SelfCheck(
            "package_identity",
            "warn",
            detail + "; package_metadata_missing=true",
            repair=f"{sys.executable} -m pip install -e {project}",
        )
    return SelfCheck("package_identity", "ok", detail)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except (OSError, ValueError):
        return False
    return True


def _check_entrypoint_identity(project: Path) -> SelfCheck:
    path_koru = shutil.which("koru")
    local = project / ".venv" / "bin" / "koru"
    detail = f"path_koru={path_koru or '-'}; local_koru={local if local.is_file() else '-'}"
    if local.is_file() and path_koru and not _is_relative_to(Path(path_koru), project / ".venv"):
        editable_source = _installed_editable_source_root()
        if editable_source is not None and editable_source == project.resolve():
            return SelfCheck(
                "entrypoint_identity",
                "ok",
                detail + "; path_not_project_venv=true; editable_source_matches=true",
            )
        return SelfCheck(
            "entrypoint_identity",
            "warn",
            detail + "; path_not_project_venv=true",
            repair=f"export PATH={local.parent}:$PATH",
        )
    return SelfCheck("entrypoint_identity", "ok", detail)


def _install_manager_checks(
    project: Path,
    *,
    ide: str,
    socket_path: Path | None,
) -> list[SelfCheck]:
    try:
        report = collect_install_manager_report(ide=ide, socket_path=socket_path)
    except Exception as exc:
        return [
            SelfCheck(
                "autopilot_install_manager",
                "fail",
                f"collect failed: {type(exc).__name__}: {exc}",
                repair=f"koru autopilot manage --ide {ide} --fix",
            )
        ]
    repairable, advisory = _install_manager_issue_groups(report)
    detail = _install_manager_check_detail(report)
    if repairable:
        return [
            SelfCheck(
                "autopilot_install_manager",
                "warn",
                detail + f"; repairable={','.join(repairable)}",
                repair=f"koru autopilot manage --ide {report.plugin.get('ide') or ide} --fix",
            )
        ]
    return [
        SelfCheck(
            "autopilot_install_manager",
            "ok" if not advisory else "warn",
            detail + (f"; advisory={','.join(advisory)}" if advisory else ""),
        )
    ]


_INSTALL_MANAGER_REPAIRABLE_CODES = {
    "koru_version_mismatch",
    "koru_path_mismatch",
    "plugin_installed_version_mismatch",
    "plugin_live_host_stale",
    "plugin_socket_candidate_mismatch",
    "plugin_version_mismatch",
}


def _install_manager_issue_groups(report: Any) -> tuple[list[str], list[str]]:
    repairable: list[str] = []
    advisory: list[str] = []
    for issue in report.issues:
        row = issue.to_dict()
        code = str(row.get("code") or "")
        severity = str(row.get("severity") or "")
        target = repairable if code in _INSTALL_MANAGER_REPAIRABLE_CODES else advisory
        target.append(f"{code}:{severity}")
    return repairable, advisory


def _install_manager_check_detail(report: Any) -> str:
    return (
        f"ide={report.plugin.get('ide')}; socket={report.socket}; "
        f"package={report.package_version or '-'}; source={report.source_version or '-'}; "
        f"connected={report.plugin.get('connected')}; "
        f"installed={report.plugin.get('installed_version') or '-'}; "
        f"expected={report.plugin.get('expected_version') or '-'}"
    )


def _check_interface_registry() -> SelfCheck:
    try:
        from koru.interface_registry import load_interface_registry

        registry = load_interface_registry()
    except Exception as exc:
        return SelfCheck(
            "interface_registry",
            "fail",
            f"load failed: {type(exc).__name__}: {exc}",
        )
    families = sorted({item.family for item in registry.interfaces})
    return SelfCheck(
        "interface_registry",
        "ok",
        f"interfaces={len(registry.interfaces)}; families={','.join(families)}",
    )


def _check_environment_profile(project: Path, *, ide: str) -> SelfCheck:
    try:
        from koru.environment_profile import resolve_environment_profile

        profile = resolve_environment_profile(project, ide=ide)
    except Exception as exc:
        return SelfCheck(
            "environment_profile",
            "fail",
            f"resolve failed: {type(exc).__name__}: {exc}",
        )
    return SelfCheck(
        "environment_profile",
        "ok",
        (
            f"{profile.decision_key}; "
            f"submit_key={profile.ide.submit_key}; "
            f"keyboard_fallback={profile.ide.keyboard_fallback_default}"
        ),
    )


def _package_component(project: Path) -> EcosystemComponent:
    source = _source_version(project) or ""
    installed = _installed_version() or ""
    repair = f"{sys.executable} -m pip install -e {project}"
    if not installed:
        return EcosystemComponent(
            "koru_package",
            "python_package",
            "warn",
            current="-",
            expected=source,
            repair=repair,
            detail="importlib metadata for package 'koru' is missing",
        )
    if source and source != installed:
        return EcosystemComponent(
            "koru_package",
            "python_package",
            "warn",
            current=installed,
            expected=source,
            repair=repair,
            detail="installed package version differs from source pyproject",
        )
    return EcosystemComponent(
        "koru_package",
        "python_package",
        "ok",
        current=installed,
        expected=source,
        detail=f"python={sys.executable}",
    )


def _entrypoint_component(project: Path) -> EcosystemComponent:
    path_koru = shutil.which("koru") or ""
    local = project / ".venv" / "bin" / "koru"
    local_s = str(local) if local.is_file() else ""
    repair = f"export PATH={local.parent}:$PATH" if local_s else ""
    if local_s and path_koru and not _is_relative_to(Path(path_koru), project / ".venv"):
        editable_source = _installed_editable_source_root()
        if editable_source is not None and editable_source == project.resolve():
            return EcosystemComponent(
                "koru_entrypoint",
                "cli_entrypoint",
                "ok",
                current=path_koru,
                expected=local_s,
                detail="PATH entrypoint is outside project venv, but editable source matches",
            )
        return EcosystemComponent(
            "koru_entrypoint",
            "cli_entrypoint",
            "warn",
            current=path_koru,
            expected=local_s,
            repair=repair,
            detail="PATH entrypoint is outside project venv",
        )
    return EcosystemComponent(
        "koru_entrypoint",
        "cli_entrypoint",
        "ok",
        current=path_koru or "-",
        expected=local_s or "-",
    )


def _install_manager_component(
    *,
    ide: str,
    socket_path: Path | None,
) -> list[EcosystemComponent]:
    try:
        report = collect_install_manager_report(ide=ide, socket_path=socket_path)
    except Exception as exc:
        return [
            EcosystemComponent(
                "autopilot_install_manager",
                "control_plane",
                "fail",
                repair=f"koru autopilot manage --ide {ide} --fix",
                detail=f"collect failed: {type(exc).__name__}: {exc}",
            )
        ]
    repairable, advisory = _install_manager_issue_groups(report)
    status = "warn" if repairable else ("warn" if advisory else "ok")
    repair = (
        f"koru autopilot manage --ide {report.plugin.get('ide') or ide} --fix"
        if repairable
        else ""
    )
    plugin_status = "ok"
    if repairable or advisory:
        plugin_status = status
    current = str(
        report.plugin.get("connected_version")
        or report.plugin.get("installed_version")
        or "-"
    )
    expected = str(report.plugin.get("expected_version") or "-")
    return [
        EcosystemComponent(
            "autopilot_install_manager",
            "control_plane",
            status,
            current="ok" if report.ok else "issues",
            expected="ok",
            repair=repair,
            detail=_install_manager_check_detail(report),
        ),
        EcosystemComponent(
            f"autopilot_plugin:{report.plugin.get('ide') or ide}",
            "ide_plugin",
            plugin_status,
            current=current,
            expected=expected,
            repair=repair,
            detail=(
                f"connected={report.plugin.get('connected')}; "
                f"build={report.plugin.get('connected_build_sha') or '-'}; "
                f"expected_build={report.plugin.get('expected_build_sha') or '-'}"
            ),
        ),
    ]


def _interface_registry_component() -> EcosystemComponent:
    try:
        from koru.interface_registry import load_interface_registry

        registry = load_interface_registry()
    except Exception as exc:
        return EcosystemComponent(
            "interface_registry",
            "runtime_contract",
            "fail",
            detail=f"load failed: {type(exc).__name__}: {exc}",
        )
    families = sorted({item.family for item in registry.interfaces})
    return EcosystemComponent(
        "interface_registry",
        "runtime_contract",
        "ok",
        current=str(len(registry.interfaces)),
        expected="loadable",
        detail=f"families={','.join(families)}",
    )


def _environment_profile_component(project: Path, *, ide: str) -> EcosystemComponent:
    try:
        from koru.environment_profile import resolve_environment_profile

        profile = resolve_environment_profile(project, ide=ide)
    except Exception as exc:
        return EcosystemComponent(
            "environment_profile",
            "runtime_contract",
            "fail",
            detail=f"resolve failed: {type(exc).__name__}: {exc}",
        )
    return EcosystemComponent(
        "environment_profile",
        "runtime_contract",
        "ok",
        current=profile.decision_key,
        expected=f"ide={ide}",
        detail=(
            f"submit_key={profile.ide.submit_key}; "
            f"keyboard_fallback={profile.ide.keyboard_fallback_default}"
        ),
    )


def _ecosystem_components(
    project: Path,
    *,
    ide: str,
    socket_path: Path | None,
) -> list[EcosystemComponent]:
    components = [
        _package_component(project),
        _entrypoint_component(project),
    ]
    components.extend(_install_manager_component(ide=ide, socket_path=socket_path))
    components.append(_interface_registry_component())
    components.append(_environment_profile_component(project, ide=ide))
    return components


def run_self_control(
    project: Path,
    *,
    ide: str = "auto",
    socket_path: Path | None = None,
) -> SelfControlReport:
    project = project.resolve()
    report = SelfControlReport(project=project)
    report.checks.append(_check_package_identity(project))
    report.checks.append(_check_entrypoint_identity(project))
    report.checks.extend(_install_manager_checks(project, ide=ide, socket_path=socket_path))
    report.checks.append(_check_interface_registry())
    report.checks.append(_check_environment_profile(project, ide=ide))
    report.ecosystem_components.extend(
        _ecosystem_components(project, ide=ide, socket_path=socket_path)
    )
    return report


def repair_self_control(
    project: Path,
    *,
    ide: str = "auto",
    socket_path: Path | None = None,
    yes: bool = False,
    runner: Runner = _run,
) -> SelfControlReport:
    report = run_self_control(project, ide=ide, socket_path=socket_path)
    if not yes:
        report.actions.append(
            {"action": "refuse_without_yes", "ok": False, "message": "pass --yes to repair"}
        )
        return report

    package_check = next(
        (check for check in report.checks if check.name == "package_identity"),
        None,
    )
    if package_check is not None and package_check.repair:
        proc = runner([sys.executable, "-m", "pip", "install", "-e", str(project)], project)
        report.actions.append(
            {
                "action": "pip_install_editable",
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": (proc.stdout or "")[-2000:],
                "stderr": (proc.stderr or "")[-2000:],
            }
        )

    manager_check = next(
        (check for check in report.checks if check.name == "autopilot_install_manager"),
        None,
    )
    if manager_check is not None and manager_check.repair:
        repaired = repair_installation(ide=ide, socket_path=socket_path, dry_run=False)
        report.actions.extend(repaired.actions)

    return report


def format_self_control_report(report: SelfControlReport) -> str:
    lines = [
        f"koru self-control: project={report.project}",
        (
            f"koru self-control: ok={report.ok} "
            f"needs_repair={report.needs_repair} summary={report.summary()}"
        ),
    ]
    for check in report.checks:
        repair = f" repair=`{check.repair}`" if check.repair else ""
        lines.append(f"  - {check.status.upper()} {check.name}: {check.detail}{repair}")
    if report.ecosystem_components:
        lines.append("koru self-control: ecosystem")
        for component in report.ecosystem_components:
            repair = f" repair=`{component.repair}`" if component.repair else ""
            lines.append(
                f"  - {component.status.upper()} {component.name} "
                f"({component.kind}): current={component.current or '-'} "
                f"expected={component.expected or '-'}{repair}"
            )
    if report.actions:
        lines.append("koru self-control: actions")
        for action in report.actions:
            lines.append("  - " + json.dumps(action, sort_keys=True))
    return "\n".join(lines)


__all__ = [
    "EcosystemComponent",
    "SelfCheck",
    "SelfControlReport",
    "format_self_control_report",
    "repair_self_control",
    "run_self_control",
]
