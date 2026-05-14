"""Registry tests for ``koru.agent_backends``."""

from __future__ import annotations

from koru.agent_backends import (
    get_agent_backend_profile,
    iter_agent_backend_profiles,
    list_agent_backend_ids,
)


def test_list_contains_core_backends() -> None:
    ids = list_agent_backend_ids()
    assert "vscode_family_plugin_socket" in ids
    assert "mcp_stdio_server" in ids


def test_iter_matches_list_count() -> None:
    assert len(iter_agent_backend_profiles()) == len(list_agent_backend_ids())


def test_get_profile_returns_none_for_unknown() -> None:
    assert get_agent_backend_profile("no-such-backend") is None


def test_mcp_profile_is_tools_only() -> None:
    p = get_agent_backend_profile("mcp_stdio_server")
    assert p is not None
    assert p.mcp_tools_only is True
    assert p.can_push_chat is False
