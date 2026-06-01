from __future__ import annotations

from pathlib import Path

import pytest

from koru.interface_registry import (
    blocker_interface_payload,
    get_interface_descriptor,
    interface_registry_payload,
    interface_registry_path,
    list_interface_ids,
    load_interface_registry,
    summarize_interfaces_by_family,
)


def test_interface_registry_loads_expected_schema() -> None:
    registry = load_interface_registry()
    assert registry.schema == "koru.interface-registry/v1"
    assert len(registry.interfaces) >= 10


def test_interface_registry_path_exists() -> None:
    assert interface_registry_path().is_file()


def test_interface_registry_loads_from_bundled_without_project_docs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    registry = load_interface_registry()
    assert registry.schema == "koru.interface-registry/v1"
    assert len(registry.interfaces) >= 10


def test_interface_registry_prefers_project_docs_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs = tmp_path / "docs" / "interfaces"
    docs.mkdir(parents=True)
    registry_file = docs / "koru-interface-registry.yaml"
    registry_file.write_text(
        'schema: "koru.interface-registry/v1"\ninterfaces: []\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    assert interface_registry_path() == registry_file
    assert load_interface_registry().interfaces == ()


def test_interface_registry_contains_antigravity_and_mcp() -> None:
    ids = list_interface_ids()
    assert "antigravity_native_send" in ids
    assert "windsurf_native_send" in ids
    assert "mcp_stdio_server" in ids


def test_get_interface_descriptor_returns_structured_fields() -> None:
    item = get_interface_descriptor("plugin_socket_vscode_family")
    assert item is not None
    assert item.family == "ide_control"
    assert item.verification.mode == "strict_ack"
    assert "plugin_version_mismatch" in item.blocking_modes


def test_interface_registry_family_summary_has_multiple_families() -> None:
    summary = summarize_interfaces_by_family()
    assert summary["ide_control"] >= 2
    assert summary["observation"] >= 1
    assert summary["tool_invocation"] >= 1


def test_blocker_interface_payload_returns_recovery_for_plugin_mismatch() -> None:
    payload = blocker_interface_payload("plugin_version_mismatch")
    assert payload["blocked_by"] == "plugin_version_mismatch"
    ids = [item["id"] for item in payload["interfaces"]]
    assert "plugin_socket_vscode_family" in ids


def test_interface_registry_payload_contains_blocker_index() -> None:
    payload = interface_registry_payload()
    assert payload["schema"] == "koru.interface-registry/v1"
    assert "blockers" in payload
    assert "plugin_missing" in payload["blockers"]
    assert "plugin_not_connected" in payload["blockers"]
    assert "plugin_version_mismatch" in payload["blockers"]
