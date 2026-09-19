"""Tests for cli_auto multi-agent dispatch."""

from __future__ import annotations

from unittest.mock import patch

from koru.cli_auto import _auto_main, _is_multi_agent_argv


def test_is_multi_agent_argv():
    assert _is_multi_agent_argv(["10"])
    assert _is_multi_agent_argv(["5", "--sync"])
    assert _is_multi_agent_argv(["--workers", "4"])
    assert _is_multi_agent_argv(["-n", "3"])
    assert _is_multi_agent_argv(["--concurrency=8"])

    assert not _is_multi_agent_argv([])
    assert not _is_multi_agent_argv(["up"])
    assert not _is_multi_agent_argv(["doctor"])
    assert not _is_multi_agent_argv(["--replace-existing"])


def test_auto_main_routes_to_multi_agent():
    with patch("koru.multi_agent.run_multi_agent_auto", return_value=0) as mock_run:
        exit_code = _auto_main(["10", "--dry-run"])
        assert exit_code == 0
        mock_run.assert_called_once_with(["10", "--dry-run"])
