from __future__ import annotations

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
