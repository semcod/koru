"""Tests for the experimental IDE / LLM backend profile registry."""

from __future__ import annotations

from koru.agent_backends import get_agent_backend_profile, list_agent_backend_ids


def test_agent_backend_registry_lists_stable_ids() -> None:
    ids = list_agent_backend_ids()

    assert "vscode_family_plugin_socket" in ids
    assert "mcp_stdio_server" in ids
    assert "vendor_agent_cli" in ids


def test_mcp_profile_is_tools_only_and_not_push_chat() -> None:
    profile = get_agent_backend_profile("mcp_stdio_server")

    assert profile is not None
    assert profile.mcp_tools_only is True
    assert profile.can_push_chat is False


def test_plugin_profile_can_push_chat_but_not_pull_chat_text() -> None:
    profile = get_agent_backend_profile("vscode_family_plugin_socket")

    assert profile is not None
    assert profile.can_push_chat is True
    assert profile.can_pull_chat_text is False
    assert profile.needs_gui_session is True


def test_unknown_agent_backend_profile_returns_none() -> None:
    assert get_agent_backend_profile("missing") is None
