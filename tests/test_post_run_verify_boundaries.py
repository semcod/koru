"""Fail-closed configuration and bounded native verification regressions."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
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


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan"), "bad", True])
def test_invalid_deadline_never_executes(tmp_path, timeout):
    shell = Mock()
    planfile = Mock()
    outcomes = verify_completed_tickets(
        tmp_path, ["T-1"],
        config=PostRunVerifyConfig(enabled=True, commands=("true",), timeout_seconds=timeout),
        shell_runner=shell, planfile_runner=planfile,
    )
    assert outcomes[0]["action"] == "not_run"
    assert "finite and positive" in outcomes[0]["detail"]
    planfile.assert_not_called()
    shell.assert_not_called()


def test_valid_commands_stop_after_first_failure(tmp_path):
    shell = Mock(side_effect=[
        subprocess.CompletedProcess([], 0, "", ""),
        subprocess.CompletedProcess([], 7, "", "failed test"),
    ])
    assert run_verify_commands(tmp_path, ["first", "second", "third"], shell_runner=shell) == (
        False, "failed test", 7,
    )
    assert [call.args for call in shell.call_args_list] == [("first", tmp_path), ("second", tmp_path)]


@pytest.mark.parametrize("error,code", [(subprocess.TimeoutExpired("test", 1), 124), (OSError("missing"), 127)])
def test_injected_runner_errors_return_failure(tmp_path, error, code):
    shell = Mock(side_effect=error)
    result = run_verify_commands(tmp_path, ["first", "second"], shell_runner=shell)
    assert result[0] is False and result[2] == code
    shell.assert_called_once_with("first", tmp_path)


@pytest.mark.skipif(os.name != "posix", reason="Native bounded executor uses POSIX process groups")
def test_configured_deadline_stops_descendants_and_later_commands(tmp_path: Path):
    started, late = tmp_path / "started", tmp_path / "late"
    child = (
        f"from pathlib import Path; import time; Path({str(started)!r}).touch(); "
        f"time.sleep(1); Path({str(late)!r}).touch()"
    )
    parent = f"import subprocess,time; subprocess.Popen([{sys.executable!r}, '-c', {child!r}]); time.sleep(10)"
    command = f"{shlex.quote(sys.executable)} -c {shlex.quote(parent)}"
    # Load the actual configuration path, including the timeout override.
    import yaml

    (tmp_path / "koru.yaml").write_text(yaml.safe_dump({"queue": {"post_run_verify": {
        "enabled": True, "commands": [command, "touch later-command"], "timeout_seconds": 0.5,
    }}}))
    config = load_post_run_verify_config(tmp_path)
    assert config.timeout_seconds == 0.5
    planfile = Mock(return_value=subprocess.CompletedProcess([], 0, "", ""))
    before = time.monotonic()
    outcomes = verify_completed_tickets(tmp_path, ["T-1"], config=config, planfile_runner=planfile)
    assert time.monotonic() - before < 5
    assert outcomes[0]["ok"] is False and outcomes[0]["exit_code"] == 124
    assert "timed out" in outcomes[0]["detail"]
    planfile.assert_called_once()
    assert started.exists()
    time.sleep(1.1)
    assert not late.exists()
    assert not (tmp_path / "later-command").exists()


@pytest.mark.parametrize("raw", ["0", "-1", ".inf", ".nan", "null", "true", "bad"])
def test_invalid_yaml_deadline_reports_not_run(tmp_path, raw):
    (tmp_path / "koru.yaml").write_text(
        "queue:\n  post_run_verify:\n    enabled: true\n    commands: ['true']\n"
        f"    timeout_seconds: {raw}\n"
    )
    config = load_post_run_verify_config(tmp_path)
    shell, planfile = Mock(), Mock()
    outcomes = verify_completed_tickets(
        tmp_path, ["T-1"], config=config, shell_runner=shell, planfile_runner=planfile,
    )
    assert outcomes[0]["action"] == "not_run"
    shell.assert_not_called()
    planfile.assert_not_called()


def test_configured_deadline_preserves_custom_runner_signature(tmp_path):
    shell = Mock(return_value=subprocess.CompletedProcess([], 0, "", ""))
    outcomes = verify_completed_tickets(
        tmp_path, ["T-1"],
        config=PostRunVerifyConfig(enabled=True, commands=("custom",), timeout_seconds=0.1),
        shell_runner=shell, planfile_runner=Mock(),
    )
    assert outcomes[0]["ok"] is True
    shell.assert_called_once_with("custom", tmp_path)
