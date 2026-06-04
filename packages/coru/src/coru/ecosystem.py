"""Ecosystem sync — align coru, koru, koruenv, and IDE autopilot plugins."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PYTHON_PACKAGES = ("koruenv", "koru", "coru")
VSIX_PLUGIN_IDES = frozenset({"antigravity", "windsurf", "vscode", "vscodium", "cursor"})
AUTO_SYNC_PLUGIN_IDES = VSIX_PLUGIN_IDES - {"antigravity"}
RunFn = Callable[[Sequence[str]], int]
KoruRunFn = Callable[[str, Sequence[str]], int]


@dataclass
class SyncStep:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class SyncReport:
    project: Path
    steps: list[SyncStep] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(step.ok for step in self.steps)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "coru.ecosystem.sync/v1",
            "project": str(self.project),
            "ok": self.ok,
            "steps": [{"name": s.name, "ok": s.ok, "detail": s.detail} for s in self.steps],
        }


def _local_package_paths(repo_root: Path) -> list[str]:
    targets: list[str] = []
    if (repo_root / "pyproject.toml").is_file() and (repo_root / "src" / "koru").is_dir():
        targets.append(str(repo_root))
    for pkg in ("koruenv", "coru"):
        candidate = repo_root / "packages" / pkg
        if (candidate / "pyproject.toml").is_file():
            targets.append(str(candidate))
    return targets


def sync_python_packages(
    repo_root: Path,
    *,
    python: str | None = None,
    runner: RunFn | None = None,
) -> SyncStep:
    targets = _local_package_paths(repo_root)
    if not targets:
        return SyncStep("python_packages", True, "no editable monorepo packages found; skipped")
    py = python or sys.executable
    install_args: list[str] = []
    for target in targets:
        install_args.extend(["-e", target])
    cmd = [py, "-m", "pip", "install", "-U", *install_args]
    rc = (runner or _default_runner)(cmd)
    return SyncStep(
        "python_packages",
        rc == 0,
        f"pip install -U {' '.join(install_args)}" + ("" if rc == 0 else f" (rc={rc})"),
    )


def _default_runner(cmd: Sequence[str]) -> int:
    proc = subprocess.run(list(cmd), check=False)
    return proc.returncode


def _detect_running_plugin_ides() -> list[str]:
    try:
        from koru.autopilot.ide import detect_running_ides
    except Exception:  # noqa: BLE001 - optional during packaging
        return []
    return sorted(
        {
            row.id
            for row in detect_running_ides()
            if row.id in AUTO_SYNC_PLUGIN_IDES
        }
    )


def sync_plugins_for_ide(
    ide: str,
    *,
    koru_runner: KoruRunFn,
) -> SyncStep:
    rc = koru_runner(
        ide,
        [
            "autopilot",
            "install-plugin",
            "--ide",
            ide,
            "--format",
            "json",
        ],
    )
    return SyncStep(
        f"plugin_install:{ide}",
        rc == 0,
        f"koru autopilot install-plugin --ide {ide}" + ("" if rc == 0 else f" (rc={rc})"),
    )


def sync_manage_fix(
    ide: str,
    *,
    koru_runner: KoruRunFn,
) -> SyncStep:
    rc = koru_runner(ide, ["autopilot", "manage", "--ide", ide, "--fix", "--allow-unconnected"])
    return SyncStep(
        f"manage_fix:{ide}",
        rc == 0,
        f"koru autopilot manage --fix --ide {ide}" + ("" if rc == 0 else f" (rc={rc})"),
    )


def sync_self_repair(
    ide: str,
    *,
    project: Path,
    koru_runner: KoruRunFn,
) -> SyncStep:
    rc = koru_runner(
        ide,
        ["self", "repair", "--yes", "--ide", ide, "--project", str(project)],
    )
    return SyncStep(
        f"self_repair:{ide}",
        rc == 0,
        f"koru self repair --yes --ide {ide}" + ("" if rc == 0 else f" (rc={rc})"),
    )


def sync_ecosystem(
    repo_root: Path,
    *,
    ide: str | None = None,
    python: bool = True,
    plugins: bool = True,
    repair: bool = True,
    all_running_ides: bool = False,
    python_executable: str | None = None,
    koru_runner: KoruRunFn | None = None,
    pip_runner: RunFn | None = None,
) -> SyncReport:
    """Align Python packages and VSIX plugins with the current repo checkout."""
    repo_root = repo_root.resolve()
    report = SyncReport(project=repo_root)

    if python:
        report.steps.append(
            sync_python_packages(repo_root, python=python_executable, runner=pip_runner)
        )

    target_ides: list[str] = []
    if all_running_ides:
        target_ides = [ide for ide in _detect_running_plugin_ides() if ide in AUTO_SYNC_PLUGIN_IDES]
    elif ide:
        target_ides = [ide]

    if plugins and target_ides:
        if koru_runner is None:
            raise RuntimeError("koru_runner is required when syncing plugins")
        for target in target_ides:
            report.steps.append(sync_plugins_for_ide(target, koru_runner=koru_runner))

    if repair and target_ides:
        if koru_runner is None:
            raise RuntimeError("koru_runner is required when syncing repair")
        for target in target_ides:
            report.steps.append(sync_manage_fix(target, koru_runner=koru_runner))
            report.steps.append(
                sync_self_repair(target, project=repo_root, koru_runner=koru_runner)
            )

    return report


def format_sync_report(report: SyncReport) -> str:
    lines = [f"coru sync: project={report.project} ok={report.ok}"]
    for step in report.steps:
        mark = "ok" if step.ok else "FAIL"
        lines.append(f"  [{mark}] {step.name}: {step.detail}")
    plugin_steps = [step for step in report.steps if step.name.startswith("plugin_install:")]
    if plugin_steps or not report.ok:
        lines.append(
            "coru sync: after VSIX install, reload each IDE window "
            "(Developer: Reload Window) and run `Koru: Connect autopilot daemon`."
        )
        lines.append(
            "coru sync: manage may report plugin_not_connected until reload; "
            "that is expected."
        )
    return "\n".join(lines)


def format_sync_report_json(report: SyncReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True)


__all__ = [
    "KoruRunFn",
    "SyncReport",
    "SyncStep",
    "format_sync_report",
    "format_sync_report_json",
    "sync_ecosystem",
    "sync_python_packages",
]
