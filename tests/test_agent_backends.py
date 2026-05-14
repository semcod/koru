"""Registry tests for ``koru.agent_backends``."""

from __future__ import annotations

from koru.agent_backends import (
    get_agent_backend_profile,
    iter_agent_backend_profiles,
    list_agent_backend_ids,
    load_agent_integration_config,
    normalize_agent_backend_id,
    validate_agent_integration_config,
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


def test_backend_aliases_normalize_to_profiles() -> None:
    assert normalize_agent_backend_id("plugin_socket") == "vscode_family_plugin_socket"
    assert get_agent_backend_profile("mcp_tool") is get_agent_backend_profile("mcp_stdio_server")


def test_load_agent_integration_config_from_koru_yaml(tmp_path) -> None:
    (tmp_path / "koru.yaml").write_text(
        """
schema: "1.0"
ide_integration:
  default_lane: windsurf
  lanes:
    windsurf:
      backend: plugin_socket
      ide: windsurf
      socket: /run/user/1000/koru-autopilot-windsurf.sock
      prompt_mode: continue_ticket
    cursor:
      backend: mcp_tool
      mcp_server: koru
""",
        encoding="utf-8",
    )

    config = load_agent_integration_config(tmp_path)

    assert config is not None
    assert config.default_lane == "windsurf"
    assert config.lanes["windsurf"].backend == "vscode_family_plugin_socket"
    assert config.lanes["windsurf"].ide == "windsurf"
    assert config.lanes["cursor"].backend == "mcp_stdio_server"
    assert validate_agent_integration_config(config) == []


def test_validate_agent_integration_config_reports_unknown_backend(tmp_path) -> None:
    (tmp_path / "koru.yaml").write_text(
        """
schema: "1.0"
ide_integration:
  default_lane: missing
  lanes:
    windsurf:
      backend: no_such_backend
""",
        encoding="utf-8",
    )

    config = load_agent_integration_config(tmp_path)

    errors = validate_agent_integration_config(config)
    assert "default_lane 'missing' is not defined in lanes" in errors
    assert "lane 'windsurf' uses unknown backend 'no_such_backend'" in errors
