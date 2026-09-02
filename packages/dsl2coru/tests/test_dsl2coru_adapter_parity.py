"""Parity: same compatibility command → same result across bus input codecs."""

from __future__ import annotations

from dsl2coru.bus import dispatch
from dsl2coru.codec import envelope_to_bytes


def _mock_runner(argv: list[str]) -> tuple[int, str, str]:
    return 0, f"ok:{argv[0]}", ""


def test_status_across_adapters(monkeypatch) -> None:
    monkeypatch.setattr("dsl2koru.handlers.command.default_runner", _mock_runner)

    line = "STATUS"
    payload = {"verb": "STATUS"}
    r_text = dispatch(line)
    r_dict = dispatch(payload)
    r_pb = dispatch(envelope_to_bytes(payload))
    assert r_text.ok is True
    assert r_dict.ok == r_text.ok
    assert r_pb.ok == r_text.ok
    assert r_text.action == r_dict.action == r_pb.action == "status"


def test_legacy_dispatch_and_handlers_are_canonical_aliases() -> None:
    from dsl2coru import bus as legacy_bus
    from dsl2coru.handlers import argv as legacy_argv
    from dsl2coru.handlers import command as legacy_command
    from dsl2coru.handlers import query as legacy_query
    from dsl2coru.handlers import runner as legacy_runner
    from dsl2coru.handlers import ui as legacy_ui
    from dsl2koru import bus as canonical_bus
    from dsl2koru.handlers import argv, command, query, runner, ui

    assert legacy_bus.dispatch is canonical_bus.dispatch
    assert legacy_argv.to_cli_args is argv.to_cli_args
    assert legacy_command.run_command is command.run_command
    assert legacy_query.run_query is query.run_query
    assert legacy_runner.default_runner is runner.default_runner
    assert legacy_ui.run_ui_command is ui.run_ui_command
