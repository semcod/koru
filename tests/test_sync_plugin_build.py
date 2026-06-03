"""Tests for scripts/sync-plugin-build.py version-bump behaviour.

These guard the 'same version, different build' trap: when plugin source
content changes, the patch version must be bumped so VS Code-family IDEs treat
the freshly installed VSIX as a genuine upgrade instead of silently keeping the
previous extension host loaded.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "sync-plugin-build.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sync_plugin_build", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sync_plugin_build = _load_script()


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("0.2.7", "0.2.8"),
        ("1.0.0", "1.0.1"),
        ("0.2.9", "0.2.10"),
        ("10.20.30", "10.20.31"),
    ],
)
def test_bump_patch_increments_plain_semver(version: str, expected: str) -> None:
    assert sync_plugin_build._bump_patch(version) == expected


@pytest.mark.parametrize("version", ["0.2", "1.2.3-beta", "1.2.3+build", "", "latest"])
def test_bump_patch_refuses_non_plain_semver(version: str) -> None:
    assert sync_plugin_build._bump_patch(version) is None


def _make_plugin(plugin_dir: Path, *, version: str, source: str) -> Path:
    src = plugin_dir / "src"
    src.mkdir(parents=True)
    (src / "extension.ts").write_text(source, encoding="utf-8")
    package = plugin_dir / "package.json"
    package.write_text(
        json.dumps({"name": "koru-autopilot-test", "version": version}, indent=2) + "\n",
        encoding="utf-8",
    )
    return package


def _read(package: Path) -> dict:
    return json.loads(package.read_text(encoding="utf-8"))


def test_update_package_bumps_version_when_source_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin_dir = tmp_path / "koru-autopilot-test"
    package = _make_plugin(plugin_dir, version="0.2.7", source="export const a = 1;\n")
    # Point the script's repo-relative hashing at our temp tree.
    monkeypatch.setattr(sync_plugin_build, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sync_plugin_build, "SHARED_SRC", tmp_path / "missing-shared")

    # First run writes the initial build sha and bumps once (no prior sha).
    assert sync_plugin_build.update_package(plugin_dir) is True
    first = _read(package)
    assert first["version"] == "0.2.8"
    first_sha = first["koruAutopilotBuild"]["sha"]

    # Re-running with identical source is a no-op: no further bump.
    assert sync_plugin_build.update_package(plugin_dir) is False
    assert _read(package)["version"] == "0.2.8"

    # Changing source content triggers a new sha and another patch bump.
    (plugin_dir / "src" / "extension.ts").write_text("export const a = 2;\n", encoding="utf-8")
    assert sync_plugin_build.update_package(plugin_dir) is True
    second = _read(package)
    assert second["version"] == "0.2.9"
    assert second["koruAutopilotBuild"]["sha"] != first_sha


def test_content_sha_is_independent_of_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin_dir = tmp_path / "koru-autopilot-test"
    package = _make_plugin(plugin_dir, version="0.2.7", source="export const a = 1;\n")
    monkeypatch.setattr(sync_plugin_build, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sync_plugin_build, "SHARED_SRC", tmp_path / "missing-shared")

    sha_at_v7 = sync_plugin_build.compute_build_sha(plugin_dir)
    data = _read(package)
    data["version"] = "9.9.9"
    package.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    sha_at_v999 = sync_plugin_build.compute_build_sha(plugin_dir)

    assert sha_at_v7 == sha_at_v999
