from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_script(name: str):
    script = Path(__file__).resolve().parents[1] / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py"), script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sync_plugin_version_updates_extracted_koruide_package(tmp_path: Path) -> None:
    module = _load_script("sync-plugin-version.py")

    version_file = (
        tmp_path
        / "packages"
        / "koruide"
        / "src"
        / "koruide"
        / "plugin_version.py"
    )
    version_file.parent.mkdir(parents=True)
    version_file.write_text(
        'EXPECTED_PLUGIN_VERSIONS = {"vscode": "0.2.12"}\n',
        encoding="utf-8",
    )
    module.REPO_ROOT = tmp_path

    assert module._update_expected_versions("vscode", "0.2.13") is True
    assert '"vscode": "0.2.13"' in version_file.read_text(encoding="utf-8")


def test_legacy_vscode_sync_uses_version_mapping(tmp_path: Path) -> None:
    module = _load_script("sync-vscode-plugin-version.py")
    version_file = (
        tmp_path
        / "packages"
        / "koruide"
        / "src"
        / "koruide"
        / "plugin_version.py"
    )
    version_file.parent.mkdir(parents=True)
    version_file.write_text(
        'EXPECTED_PLUGIN_VERSIONS = {"vscode": "0.2.12"}\n'
        'EXPECTED_VSCODE_PLUGIN_VERSION = EXPECTED_PLUGIN_VERSIONS["vscode"]\n',
        encoding="utf-8",
    )

    assert module.get_plugin_version_from_source(tmp_path) == "0.2.12"
    module.update_plugin_version_source("0.2.13", tmp_path)
    assert module.get_plugin_version_from_source(tmp_path) == "0.2.13"


def test_legacy_vscode_sync_reads_and_updates_package_json(tmp_path: Path) -> None:
    module = _load_script("sync-vscode-plugin-version.py")
    package_json = tmp_path / "plugins" / "koru-autopilot-vscode" / "package.json"
    package_json.parent.mkdir(parents=True)
    package_json.write_text(
        '{"name": "koru-autopilot-vscode", "version": "0.2.12"}\n',
        encoding="utf-8",
    )

    assert module.get_plugin_version_from_package(tmp_path) == "0.2.12"
    module.update_package_json("0.2.13", tmp_path)
    assert module.get_plugin_version_from_package(tmp_path) == "0.2.13"


def test_legacy_vscode_sync_updates_github_workflow(tmp_path: Path) -> None:
    module = _load_script("sync-vscode-plugin-version.py")
    workflow_file = tmp_path / ".github" / "workflows" / "native-ide-matrix.yml"
    workflow_file.parent.mkdir(parents=True)
    workflow_file.write_text(
        'env:\n'
        '  KORU_FAKE_EXTENSION_VERSION: "0.2.12"\n',
        encoding="utf-8",
    )

    module.update_github_workflow("0.2.13", tmp_path)
    assert 'KORU_FAKE_EXTENSION_VERSION: "0.2.13"' in workflow_file.read_text(
        encoding="utf-8"
    )
