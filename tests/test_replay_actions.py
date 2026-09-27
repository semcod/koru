from __future__ import annotations

import subprocess
from unittest import mock

from koru.autonomy.replay_actions import (
    ReplayAction,
    ReplayCommandHandlers,
    ReplayQueryHandlers,
    execute_replay_action,
    ide_reload_window,
    parse_replay_dsl,
    quick_action_to_replay,
    ticket_open,
    trace_show_decisions,
)
from koru.autonomy.replay_handlers import ReplayQueryHandlers as MovedReplayQueryHandlers
from koru.autonomy.replay_parser import parse_replay_dsl as moved_parse_replay_dsl
from koru.autonomy.replay_quick_actions import (
    quick_action_to_replay as moved_quick_action_to_replay,
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


def test_replay_actions_facade_keeps_moved_public_imports_stable() -> None:
    assert ReplayQueryHandlers is MovedReplayQueryHandlers
    assert parse_replay_dsl is moved_parse_replay_dsl
    assert quick_action_to_replay is moved_quick_action_to_replay


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


def test_replay_query_handlers_show_decisions_uses_shell_pipeline(tmp_path) -> None:
    handlers = ReplayQueryHandlers()
    action = ReplayAction(domain="trace", verb="show-decisions", args={"url": "http://127.0.0.1:8765"})
    ok = subprocess.CompletedProcess(["bash"], 0, stdout="[]", stderr="")

    with mock.patch("koru.autonomy.replay_handlers.subprocess.run", return_value=ok) as run:
        result = handlers.show_decisions(action, project=tmp_path)

    assert result.ok is True
    assert result.output == "[]"
    assert run.call_args.kwargs["cwd"] == tmp_path


def test_replay_command_handlers_ticket_input_requires_ticket_id(tmp_path) -> None:
    handlers = ReplayCommandHandlers()
    action = ReplayAction(domain="ticket", verb="input")

    result = handlers.ticket_input(action, project=tmp_path)

    assert result.ok is False
    assert "ticket_id required" in result.output


def test_scan_replay_preserves_history_and_only_invokes_scanner(tmp_path, monkeypatch):
    import json
    import sys

    sentinels = [tmp_path / "project/ticket-001/README.md", tmp_path / ".planfile/sprints/current.yaml"]
    for path in sentinels:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"existing durable history\n")
    scanner = tmp_path / "fake_scanner.py"
    scanner.write_text(
        "import json,sys; from pathlib import Path; "
        "Path('scan-args.json').write_text(json.dumps(sys.argv[1:]))"
    )
    original_run = subprocess.run

    def invoke(argv, **kwargs):
        # A replay must not wrap deletion or an autonomous loop in a shell.
        assert argv[:3] == [sys.executable, "-m", "koru"] and "auto" not in argv
        assert kwargs.get("shell", False) is False
        return original_run([sys.executable, str(scanner), *argv[3:]], **kwargs)

    monkeypatch.setattr(subprocess, "run", invoke)
    result = execute_replay_action(parse_replay_dsl("scan force"), project=tmp_path)
    assert result.ok
    assert json.loads((tmp_path / "scan-args.json").read_text()) == ["scan", "--apply"]
    assert all(path.read_bytes() == b"existing durable history\n" for path in sentinels)


def test_scan_quick_action_keeps_legacy_labels_and_safe_metadata():
    for label in ("scan signals", "force fresh scan", "force scan"):
        action = quick_action_to_replay(f"[{label}] `koru scan --apply`")
        assert action is not None
        assert action.to_dsl() == "scan force"
        assert "preserving" in action.label or "without deleting" in action.label
        assert "rm " not in action.to_shell()
        assert action.validate_cmd is None


def test_scan_replay_propagates_scanner_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: subprocess.CompletedProcess(a[0], 7, "failed scan", ""))
    result = execute_replay_action(parse_replay_dsl("scan force"), project=tmp_path)
    assert result.ok is False
    assert result.returncode == 7
