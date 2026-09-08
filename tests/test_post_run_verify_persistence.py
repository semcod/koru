"""Failed verification must not claim an unacknowledged lifecycle transition."""

import json
import subprocess
from unittest.mock import Mock

import pytest

from koru.autonomy.post_run_verify import PostRunVerifyConfig, verify_completed_tickets


def result(code=0, payload=None):
    return subprocess.CompletedProcess([], code, json.dumps(payload) if payload is not None else "", "")


@pytest.mark.parametrize("policy,status,action", [("reopen", "open", "reopened"), ("block", "blocked", "blocked")])
@pytest.mark.parametrize(
    "failure", [None, "write", "launch", "timeout", "read", "stale", "empty", "malformed", "read_timeout"],
)
def test_failure_action_requires_write_and_readback(tmp_path, policy, status, action, failure):
    write = {
        "write": result(1), "launch": OSError("offline"), "timeout": subprocess.TimeoutExpired("planfile", 1),
    }.get(failure, result())
    read = {
        "read": result(1), "stale": result(payload={"status": "done"}),
        "empty": result(), "malformed": subprocess.CompletedProcess([], 0, "{", ""),
        "read_timeout": subprocess.TimeoutExpired("planfile", 1),
    }.get(failure, result(payload={"id": "T-1", "status": status}))
    runner = Mock(side_effect=[write, read])
    outcomes = verify_completed_tickets(
        tmp_path, ["T-1"], config=PostRunVerifyConfig(enabled=True, commands=("check",), on_failure=policy),
        shell_runner=Mock(return_value=result(9)), planfile_runner=runner,
    )
    assert outcomes[0]["ok"] is False
    assert outcomes[0]["exit_code"] == 9
    assert outcomes[0]["action"] == (action if failure is None else "persistence_failed")
    assert runner.call_count == (1 if failure in {"write", "launch", "timeout"} else 2)
    assert runner.call_args_list[0].args[0][2] == ("block" if policy == "block" else "update")
    if runner.call_count == 2:
        assert runner.call_args_list[1].args[0] == ["planfile", "ticket", "show", "T-1", "--format", "json"]


def test_failed_transition_does_not_skip_remaining_tickets(tmp_path):
    runner = Mock(side_effect=[result(1), result(), result(payload={"id": "T-2", "status": "open"})])
    shell = Mock(return_value=result(7))
    outcomes = verify_completed_tickets(
        tmp_path, ["T-1", "T-2"], config=PostRunVerifyConfig(enabled=True, commands=("check",)),
        shell_runner=shell, planfile_runner=runner,
    )
    assert [o["action"] for o in outcomes] == ["persistence_failed", "reopened"]
    shell.assert_called_once_with("check", tmp_path)
