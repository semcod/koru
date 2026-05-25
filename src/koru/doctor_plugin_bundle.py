"""Autopilot plugin bundle checks for ``koru --doctor``."""

from __future__ import annotations

import json
from pathlib import Path

from koru.doctor_constants import PASS, SKIP, WARN
from koruide.plugin_version import EXPECTED_VSCODE_PLUGIN_VERSION


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