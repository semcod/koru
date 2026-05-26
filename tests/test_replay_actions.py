from __future__ import annotations

from koru.autonomy.replay_actions import (
    execute_replay_action,
    ide_reload_window,
    parse_replay_dsl,
    quick_action_to_replay,
    ticket_open,
    trace_show_decisions,
)
from koru.cli_replay import replay_main


def test_replay_action_renders_copy_paste_shell_command() -> None:
    action = trace_show_decisions("http://127.0.0.1:8765")

    assert action.to_dsl() == "trace show-decisions --url=http://127.0.0.1:8765"
    assert action.to_shell() == "koru replay 'trace show-decisions --url=http://127.0.0.1:8765'"


def test_parse_replay_dsl_restores_known_action_metadata() -> None:
    action = parse_replay_dsl("ide reload-window vscodium")

    assert action == ide_reload_window("vscodium")
    assert action.replayable is False
    assert action.requires_active_window is True


def test_quick_action_to_replay_maps_open_ticket_url() -> None:
    action = quick_action_to_replay(
        "[open ticket] http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp#STARTER-7",
        waiting_ticket="STARTER-7",
    )

    assert action == ticket_open("STARTER-7", "http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp")


def test_execute_ticket_open_prints_dashboard_url(tmp_path) -> None:
    action = ticket_open("STARTER-7", "http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp")

    result = execute_replay_action(action, project=tmp_path)

    assert result.ok is True
    assert result.output.endswith("#STARTER-7")


def test_replay_cli_dry_run_explains_non_replayable_action(capsys) -> None:
    rc = replay_main(["ide reload-window vscodium", "--dry-run"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "replayable: False" in out
    assert "requires_active_window" not in out
