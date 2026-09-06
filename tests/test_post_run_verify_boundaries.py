"""Fail-closed configuration and bounded native verification regressions."""

from __future__ import annotations

import subprocess
from unittest.mock import Mock

import pytest

from koru.autonomy.post_run_verify import (
    PostRunVerifyConfig,
    load_post_run_verify_config,
    run_verify_commands,
    verify_after_ide_work,
    verify_completed_tickets,
)
from koru.autonomy.state import AutoloopState


@pytest.mark.parametrize("commands", [[], [""], ["  \t"], ["true", " "], [None], [17], "true"])
def test_invalid_commands_never_execute(tmp_path, commands):
    shell = Mock()
    ok, detail, code = run_verify_commands(tmp_path, commands, shell_runner=shell)
    assert not ok and code is None and "non-empty string" in detail
    shell.assert_not_called()


@pytest.mark.parametrize("raw", ["[]", "['   ']", "[true]", "[12]", "['true', null]"])
def test_invalid_yaml_commands_are_not_verified(tmp_path, raw):
    (tmp_path / "koru.yaml").write_text(
        f"queue:\n  post_run_verify:\n    enabled: true\n    commands: {raw}\n"
    )
    config = load_post_run_verify_config(tmp_path)
    shell, planfile = Mock(), Mock()
    outcomes = verify_completed_tickets(
        tmp_path, ["T-1"], config=config, shell_runner=shell, planfile_runner=planfile,
    )
    assert outcomes[0]["ok"] is False
    assert outcomes[0]["action"] == "not_run"
    shell.assert_not_called()
    planfile.assert_not_called()


def test_empty_ide_verification_is_not_cached_as_success(tmp_path):
    state = AutoloopState(pending_ide_verify_id="T-1")
    planfile = Mock(side_effect=[
        subprocess.CompletedProcess([], 0, '{"status":"done"}', ""),
        subprocess.CompletedProcess([], 0, '[]', ""),
    ])
    outcomes = verify_after_ide_work(
        tmp_path, state, config=PostRunVerifyConfig(enabled=True), planfile_runner=planfile,
    )
    assert outcomes[0]["action"] == "not_run"
    assert "T-1" not in state.post_verify_seen
    assert planfile.call_count == 2  # Read-only status/list; no transition.


def test_valid_commands_stop_after_first_failure(tmp_path):
    shell = Mock(side_effect=[
        subprocess.CompletedProcess([], 0, "", ""),
        subprocess.CompletedProcess([], 7, "", "failed test"),
    ])
    assert run_verify_commands(tmp_path, ["first", "second", "third"], shell_runner=shell) == (
        False, "failed test", 7,
    )
    assert [call.args for call in shell.call_args_list] == [("first", tmp_path), ("second", tmp_path)]


