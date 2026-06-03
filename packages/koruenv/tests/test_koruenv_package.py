from __future__ import annotations

import json

from koruenv import cli as koruenv_cli
from koruenv import lane as koruenv_lane


def test_lane_env_xdg_runtime() -> None:
    overlay = koruenv_lane.build_lane_environ(
        ide="windsurf",
        instance="windsurf-main",
        environ={"XDG_RUNTIME_DIR": "/run/user/1000"},
    )

    assert overlay["KORU_AUTOPILOT_IDE"] == "windsurf"
    assert overlay["KORU_AUTOPILOT_INSTANCE"] == "windsurf-main"
    assert overlay["KORU_AUTOPILOT_SOCKET"] == "/run/user/1000/koru-autopilot-windsurf-main.sock"


def test_cli_env_bash(capsys) -> None:
    rc = koruenv_cli.main(["env", "cursor", "cursor-main", "--shell", "bash"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "export KORU_AUTOPILOT_IDE=cursor" in out
    assert "export KORU_AUTOPILOT_INSTANCE=cursor-main" in out


def test_cli_env_jsonl_log_contract(capsys) -> None:
    rc = koruenv_cli.main(["--log-format", "jsonl", "env", "cursor", "cursor-main", "--shell", "bash"])

    assert rc == 0
    err_lines = [line for line in capsys.readouterr().err.splitlines() if line.strip().startswith("{")]
    assert err_lines
    payload = json.loads(err_lines[0])
    assert set(["ts", "corr", "component", "level", "action", "result"]).issubset(payload)
    assert payload["action"] == "env"
    assert payload["result"] == "ok"
