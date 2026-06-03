"""Tests for :mod:`koru.agent_backend_runtime`."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from koru.agent_backend_runtime import (
    McpToolBackend,
    NoopBackend,
    OsInjectorBackend,
    PluginSocketBackend,
    SllmShellBackend,
    build_agent_backend,
)


def test_plugin_socket_backend_forwards_send_chat_to_drive() -> None:
    client = MagicMock()
    client.drive.return_value = {"ok": True, "backend": "mock"}
    backend = PluginSocketBackend(client)
    project = Path("/tmp/koru-proj")
    out = backend.send_chat(
        project,
        "hello agent",
        ide="windsurf",
        submit=True,
        ticket_id="PLF-1",
    )
    client.drive.assert_called_once_with("hello agent", submit=True, ide="windsurf")
    assert out == {"ok": True, "backend": "mock"}


# --- McpToolBackend ----------------------------------------------------------


def test_mcp_tool_backend_returns_ok_marker() -> None:
    """MCP backend is a no-op push: returns ok with backend marker."""
    backend = McpToolBackend(mcp_server="koru-stdio")
    out = backend.send_chat(
        Path("/tmp/p"),
        "ignored prompt",
        ide="cursor",
        submit=True,
        ticket_id="PLF-7",
    )
    assert out["ok"] is True
    assert out["backend"] == "mcp_tool"
    assert out["mcp_server"] == "koru-stdio"
    assert "MCP" in out["message"] or "mcp" in out["message"].lower()


def test_mcp_tool_backend_no_server_field() -> None:
    backend = McpToolBackend()
    out = backend.send_chat(Path("/tmp"), "x", ide="cursor", submit=False)
    assert out["ok"] is True
    assert out["mcp_server"] is None


# --- NoopBackend -------------------------------------------------------------


def test_noop_backend_returns_ok_with_reason() -> None:
    backend = NoopBackend(reason="ci-smoke")
    out = backend.send_chat(Path("/tmp"), "anything", ide="auto", submit=True)
    assert out["ok"] is True
    assert out["backend"] == "noop"
    assert "ci-smoke" in out["message"]


# --- build_agent_backend factory --------------------------------------------


def test_factory_resolves_plugin_socket_with_client() -> None:
    client = MagicMock()
    backend = build_agent_backend(backend_id="plugin_socket", client=client)
    assert isinstance(backend, PluginSocketBackend)
    assert backend.client is client


def test_factory_plugin_socket_requires_client() -> None:
    with pytest.raises(ValueError, match="plugin_socket"):
        build_agent_backend(backend_id="plugin_socket", client=None)


def test_factory_resolves_mcp_tool() -> None:
    backend = build_agent_backend(backend_id="mcp_tool", mcp_server="koru-stdio")
    assert isinstance(backend, McpToolBackend)
    assert backend.mcp_server == "koru-stdio"


def test_factory_resolves_mcp_tool_without_server() -> None:
    backend = build_agent_backend(backend_id="mcp_tool")
    assert isinstance(backend, McpToolBackend)
    assert backend.mcp_server is None


def test_factory_resolves_sllm_shell() -> None:
    backend = build_agent_backend(backend_id="sllm_shell", shell_client_id="claude-code")
    assert isinstance(backend, SllmShellBackend)
    assert backend.client_id == "claude-code"


def test_factory_uses_sllm_backend_aliases() -> None:
    backend = build_agent_backend(backend_id="vendor_cli", shell_client_id="aider")
    assert isinstance(backend, SllmShellBackend)
    assert backend.client_id == "aider"


def test_sllm_shell_backend_delegates_to_bridge(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    def fake_drive_shell_chat(**kwargs):
        calls.update(kwargs)
        return {"ok": True, "backend": "sllm_shell", "client_id": kwargs["client_id"]}

    monkeypatch.setattr("koru.agent_backend_runtime.drive_shell_chat", fake_drive_shell_chat)
    backend = SllmShellBackend(client_id="aider", execute=False)

    out = backend.send_chat(Path("/tmp/project"), "fix tests", ide="auto", submit=True)

    assert out["ok"] is True
    assert calls["client_id"] == "aider"
    assert calls["prompt"] == "fix tests"
    assert calls["execute"] is False


def test_factory_resolves_none_to_noop() -> None:
    for bid in ("none", "noop", ""):
        backend = build_agent_backend(backend_id=bid, noop_reason="test-reason")
        assert isinstance(backend, NoopBackend)
        assert backend.reason == "test-reason"


def test_factory_resolves_os_injector_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_OS_INJECTOR_PROFILE", "windsurf")
    monkeypatch.setenv("KORU_OS_INJECTOR_CONFIG", "/tmp/koru-os.json")
    backend = build_agent_backend(backend_id="os_injector")
    assert isinstance(backend, OsInjectorBackend)
    assert backend.profile_id == "windsurf"


def test_factory_os_injector_requires_profile_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KORU_OS_INJECTOR_PROFILE", raising=False)
    with pytest.raises(ValueError, match="KORU_OS_INJECTOR_PROFILE"):
        build_agent_backend(backend_id="os_injector")


def test_factory_normalizes_case_and_whitespace() -> None:
    backend = build_agent_backend(backend_id=" Plugin_Socket ", client=MagicMock())
    assert isinstance(backend, PluginSocketBackend)


def test_factory_rejects_unknown_backend_id() -> None:
    with pytest.raises(ValueError, match="unknown agent backend id"):
        build_agent_backend(backend_id="custom_thing")


# --- All backends conform to AgentBackend protocol --------------------------


@pytest.mark.parametrize(
    "backend_id, kwargs",
    [
        ("plugin_socket", {"client": MagicMock(drive=MagicMock(return_value={"ok": True}))}),
        ("mcp_tool", {}),
        ("none", {}),
    ],
)
def test_all_backends_implement_send_chat(backend_id, kwargs) -> None:
    backend = build_agent_backend(backend_id=backend_id, **kwargs)
    out = backend.send_chat(
        Path("/tmp"),
        "test prompt",
        ide="auto",
        submit=True,
        ticket_id=None,
    )
    assert isinstance(out, dict)
    assert "ok" in out
