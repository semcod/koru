from __future__ import annotations

from koruapi import env2llm_registry
from koruapi.mcp_server_env2llm import (
    tool_env2llm_get_registry,
    tool_env2llm_list_commands,
    tool_env2llm_mqtt_status,
)


def _assert_service_descriptor(payload: dict) -> None:
    descriptor = payload["service_descriptor"]
    assert descriptor["schema"] == "env2llm.service-descriptor.v1"
    assert descriptor["kind"] == "registry"
    assert len(descriptor["request_hash"]) == 64
    assert len(descriptor["descriptor_hash"]) == 64


def test_env2llm_get_registry_without_dependency(monkeypatch) -> None:
    monkeypatch.setattr(env2llm_registry, "_ENV2LLM_AVAILABLE", False)
    payload = env2llm_registry.env2llm_get_registry()
    assert payload["ok"] is False
    assert "env2llm" in payload["error"]


def test_mcp_tool_env2llm_get_registry(monkeypatch, tmp_path) -> None:
    if not env2llm_registry.env2llm_available():
        payload = tool_env2llm_get_registry({"project_dir": str(tmp_path)})
        assert payload["ok"] is False
        return

    payload = tool_env2llm_get_registry({"project_dir": str(tmp_path)})
    assert payload["ok"] is True
    assert "registry" in payload
    _assert_service_descriptor(payload)


def test_mcp_tool_env2llm_list_commands(monkeypatch, tmp_path) -> None:
    if not env2llm_registry.env2llm_available():
        payload = tool_env2llm_list_commands({"project_dir": str(tmp_path)})
        assert payload["ok"] is False
        return

    payload = tool_env2llm_list_commands({"project_dir": str(tmp_path)})
    assert payload["ok"] is True
    assert "commands" in payload
    _assert_service_descriptor(payload)


def test_mcp_tool_env2llm_mqtt_status(monkeypatch, tmp_path) -> None:
    if not env2llm_registry.env2llm_available():
        payload = tool_env2llm_mqtt_status({"project_dir": str(tmp_path)})
        assert payload["ok"] is False
        return

    payload = tool_env2llm_mqtt_status({"project_dir": str(tmp_path)})
    assert payload["ok"] is True
    assert "enabled" in payload
    _assert_service_descriptor(payload)
