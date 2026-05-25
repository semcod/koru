from __future__ import annotations

from koru.interface_registry import (
    get_interface_descriptor,
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


def test_interface_registry_contains_antigravity_and_mcp() -> None:
    ids = list_interface_ids()
    assert "antigravity_native_send" in ids
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
