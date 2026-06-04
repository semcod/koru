from __future__ import annotations

import json
import os
from argparse import Namespace
from datetime import UTC, datetime

from koru import autonomous_plugin_wait as plugin_wait_mod
from koru.autonomous_cycle_orchestrator import (
    _emit_autopilot_observability_outcome,
    _plugin_gate_status,
)
from koru.autonomous_plugin_wait import (
    _emit_plugin_bootstrap_blocker_trace,
    wait_for_plugin_connection,
)
from koru.autopilot.cli_command import _action_trace
from koru.control_commands import (
    api_command,
    control_command,
    control_command_replay_plan,
    desktop_gui_command,
    parse_control_command_dsl,
    plugin_socket_command,
    shell_command,
)
from koru.observability_dsl import (
    OBSERVABILITY_CONTEXT,
    KoruObsEvent,
    parse_observability_dsl,
    render_compact_observability_line,
    render_observability_path,
    stored_event_to_dsl,
)
from koru.observability_writer import (
    observability_dsl_log_path,
    observability_event_store_path,
    write_observability_event,
)
from koru.queue import QueueLoopResult
from koru.queue import runners as queue_runners
from koruobserve.cli import observe_main


def test_observability_dsl_roundtrips_event() -> None:
    event = KoruObsEvent(
        ts="2026-05-25T16:51:03Z",
        corr="cli-drive",
        session="auto-732",
        cycle=732,
        ticket="STARTER-276",
        component="autopilot",
        kind="autopilot.drive.failed",
        severity="error",
        data={
            "code": "autopilot_daemon_timeout",
            "message": "daemon unreachable: timed out",
            "submit": True,
            "timeout_s": 8,
        },
    )

    parsed = parse_observability_dsl(event.to_dsl())

    assert parsed == event
    assert "failure code=autopilot_daemon_timeout" in event.to_dsl()
    assert 'message="daemon unreachable: timed out"' in event.to_dsl()


def test_observability_writer_persists_jsonl_dsl_log_and_terminal_compact(
    tmp_path, capsys
) -> None:
    event = KoruObsEvent(
        corr="cli-drive",
        component="autopilot",
        kind="autopilot.route.decision",
        data={
            "name": "route_transport",
            "chosen": "plugin",
            "because": "plugin_connected",
            "require_plugin": True,
        },
    )

    stored = write_observability_event(event, project=tmp_path)

    path = observability_event_store_path(tmp_path)
    rows = [json.loads(raw) for raw in path.read_text(encoding="utf-8").splitlines()]
    assert stored.context == OBSERVABILITY_CONTEXT
    assert rows[0]["event_type"] == "autopilot.route.decision"
    assert rows[0]["aggregate_id"] == "cli-drive"
    assert rows[0]["payload"]["data"]["chosen"] == "plugin"

    dsl_text = observability_dsl_log_path(tmp_path).read_text(encoding="utf-8")
    assert "decision because=plugin_connected chosen=plugin" in dsl_text
    terminal = capsys.readouterr().err
    assert "koru ▸ OBS:" in terminal
    assert "decision" in terminal
    assert "because=plugin_connected" in terminal
    assert "chosen=plugin" in terminal


def test_observability_writer_terminal_compact_can_be_disabled(
    tmp_path, capsys, monkeypatch
) -> None:
    monkeypatch.setenv("KORU_OBSERVABILITY_TERMINAL", "0")

    write_observability_event(
        KoruObsEvent(
            corr="cli-drive",
            component="autopilot",
            kind="autopilot.intent",
            data={"goal": "deliver_prompt_to_ide_chat"},
        ),
        project=tmp_path,
        write_dsl_log=False,
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_stored_event_to_dsl_uses_store_timestamp(tmp_path) -> None:
    event = KoruObsEvent(
        corr="cli-drive",
        component="autopilot",
        kind="autopilot.drive.phase",
        data={"name": "submit", "status": "awaiting_ack"},
    )
    stored = write_observability_event(event, project=tmp_path, write_dsl_log=False)

    dsl = stored_event_to_dsl(stored)

    assert dsl.startswith(f"@{stored.occurred_at}")
    assert "phase name=submit status=awaiting_ack" in dsl


def test_compact_observability_line_is_semantic_and_short() -> None:
    line = render_compact_observability_line(
        KoruObsEvent(
            ts="2026-05-25T17:10:34Z",
            corr="cli-drive",
            session="wayland",
            cycle=735,
            ticket="STARTER-277",
            component="autopilot",
            kind="autopilot.drive.failed",
            severity="error",
            data={
                "code": "autopilot_daemon_timeout",
                "message": "daemon unreachable: timed out",
                "route": "too noisy for compact view",
            },
        )
    )

    assert line.startswith("[17:10:34] koru ▸ OBS:")
    assert "session=wayland" in line
    assert "ticket=STARTER-277" in line
    assert "failure code=autopilot_daemon_timeout" in line
    assert 'message="daemon unreachable: timed out"' in line
    assert "too noisy" not in line


def test_observability_path_summarizes_trace_axis() -> None:
    events = [
        KoruObsEvent(
            corr="cli-drive",
            component="autopilot",
            kind="autopilot.intent",
            data={"goal": "deliver_prompt_to_ide_chat"},
        ),
        KoruObsEvent(
            corr="cli-drive",
            component="autopilot",
            kind="autopilot.route.decision",
            data={"chosen": "plugin"},
        ),
        KoruObsEvent(
            corr="cli-drive",
            component="autopilot",
            kind="autopilot.drive.phase",
            data={"name": "submit", "status": "awaiting_ack"},
        ),
        KoruObsEvent(
            corr="cli-drive",
            component="autopilot",
            kind="autopilot.drive.failed",
            data={"code": "autopilot_daemon_timeout"},
        ),
        KoruObsEvent(
            corr="cli-drive",
            component="autonomy",
            kind="autonomy.blocker",
            data={"name": "drive_failed"},
        ),
        KoruObsEvent(
            corr="cli-drive",
            component="autonomy",
            kind="autonomy.next",
            data={"action": "retry_next_cycle"},
        ),
    ]

    assert render_observability_path(events) == (
        "OBS intent(deliver_prompt_to_ide_chat) -> decision(plugin) -> "
        "phase(submit awaiting_ack) -> failure(autopilot_daemon_timeout) -> "
        "blocker(drive_failed) -> next(retry_next_cycle)"
    )


def test_control_command_dsl_roundtrips_to_replay_plan(tmp_path) -> None:
    event = shell_command(
        tmp_path,
        corr="shell-1",
        argv=["planfile", "ticket", "done", "STARTER-1"],
        cwd=str(tmp_path),
    )

    parsed = parse_control_command_dsl(event.to_dsl())
    plan = control_command_replay_plan(parsed)

    assert parsed.kind == "control.command"
    assert plan["surface"] == "shell_cli"
    assert plan["argv"] == ["planfile", "ticket", "done", "STARTER-1"]
    assert plan["cwd"] == str(tmp_path)
    compact = render_compact_observability_line(event)
    assert "argv_text=" in compact
    assert "args=" not in compact
    assert "planfile" in compact
    assert "STARTER-1" in compact


def test_queue_shell_and_api_runners_emit_control_commands(tmp_path, monkeypatch) -> None:
    shell_result = queue_runners.run_shell_command("printf ok", tmp_path)
    assert shell_result.stdout == "ok"

    class _Response:
        status = 202
        headers = {"x-test": "yes"}

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def read(self) -> bytes:
            return b'{"ok": true}'

    monkeypatch.setattr(queue_runners.urllib.request, "urlopen", lambda *_a, **_k: _Response())

    api_result = queue_runners.run_api_request(
        {
            "endpoint": "http://127.0.0.1:8765/api/tickets/update?dry=1",
            "method": "POST",
            "headers": {"authorization": "Bearer secret", "x-visible": "1"},
            "body": {"id": "STARTER-1", "status": "done"},
        },
        tmp_path,
    )

    rows = [
        json.loads(raw)
        for raw in observability_event_store_path(tmp_path).read_text(encoding="utf-8").splitlines()
    ]
    commands = [row["payload"] for row in rows if row["event_type"] == "control.command"]
    assert api_result.status_code == 202
    assert commands[0]["data"]["surface"] == "shell_cli"
    assert commands[1]["data"]["surface"] == "api"
    assert commands[1]["data"]["args"]["query"] == {"dry": "1"}
    assert commands[1]["data"]["args"]["headers"]["authorization"] == "<redacted>"
    assert commands[1]["data"]["args"]["headers"]["x-visible"] == "1"


def test_autopilot_trace_can_render_observability_dsl(tmp_path, capsys) -> None:
    write_observability_event(
        KoruObsEvent(
            corr="cli-drive",
            component="autopilot",
            kind="autopilot.drive.phase",
            data={"name": "submit", "status": "awaiting_ack"},
        ),
        project=tmp_path,
        write_dsl_log=False,
        emit_terminal=False,
    )

    rc = _action_trace(Namespace(project=tmp_path, format="dsl", limit=10))

    assert rc == 0
    out = capsys.readouterr().out
    assert "corr=cli-drive" in out
    assert "phase name=submit status=awaiting_ack" in out


def test_observe_trace_renders_compact_timeline_with_filters(tmp_path, capsys) -> None:
    write_observability_event(
        KoruObsEvent(
            ts="2026-05-25T17:10:26Z",
            corr="cli-drive",
            ticket="STARTER-277",
            component="autopilot",
            kind="autopilot.intent",
            data={"goal": "deliver_prompt_to_ide_chat", "target": "vscodium", "chars": 584},
        ),
        project=tmp_path,
        write_dsl_log=False,
        emit_terminal=False,
    )
    write_observability_event(
        KoruObsEvent(
            ts="2026-05-25T17:10:34Z",
            corr="cli-drive",
            ticket="STARTER-277",
            component="autonomy",
            kind="autonomy.next",
            data={"action": "retry_next_cycle"},
        ),
        project=tmp_path,
        write_dsl_log=False,
        emit_terminal=False,
    )
    write_observability_event(
        KoruObsEvent(
            corr="other",
            ticket="STARTER-999",
            component="autopilot",
            kind="autopilot.intent",
            data={"goal": "ignore"},
        ),
        project=tmp_path,
        write_dsl_log=False,
        emit_terminal=False,
    )

    rc = observe_main(
        [
            "--project",
            str(tmp_path),
            "trace",
            "--ticket",
            "STARTER-277",
            "--format",
            "compact",
        ]
    )

    assert rc == 0
    out = capsys.readouterr().out
    assert "intent goal=deliver_prompt_to_ide_chat target=vscodium chars=584" in out
    assert "next action=retry_next_cycle" in out
    assert "STARTER-999" not in out


def test_observe_trace_renders_path_view(tmp_path, capsys) -> None:
    write_observability_event(
        KoruObsEvent(
            corr="cli-drive",
            ticket="STARTER-277",
            component="autopilot",
            kind="autopilot.intent",
            data={"goal": "deliver_prompt_to_ide_chat"},
        ),
        project=tmp_path,
        write_dsl_log=False,
        emit_terminal=False,
    )
    write_observability_event(
        KoruObsEvent(
            corr="cli-drive",
            ticket="STARTER-277",
            component="autopilot",
            kind="autopilot.drive.phase",
            data={"name": "submit", "status": "awaiting_ack"},
        ),
        project=tmp_path,
        write_dsl_log=False,
        emit_terminal=False,
    )

    rc = observe_main(
        [
            "--project",
            str(tmp_path),
            "trace",
            "--ticket",
            "STARTER-277",
            "--format",
            "path",
        ]
    )

    assert rc == 0
    assert capsys.readouterr().out.strip() == (
        "OBS intent(deliver_prompt_to_ide_chat) -> phase(submit awaiting_ack)"
    )


def test_autonomy_failed_drive_emits_blocker_and_next(tmp_path) -> None:
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["STARTER-276"],
        last_status="waiting_input",
        last_message="",
        last_ticket_id="STARTER-276",
    )

    _emit_autopilot_observability_outcome(
        project=tmp_path,
        cycle=732,
        queue_result=queue_result,
        reply={"ok": False, "message": "autopilot daemon unreachable: timed out"},
        ok=False,
        autopilot_status="failed",
        decision_kind="ticket_prompt",
        autopilot_ide="vscodium",
    )

    rows = [
        json.loads(raw)
        for raw in observability_event_store_path(tmp_path).read_text(encoding="utf-8").splitlines()
    ]
    assert [row["event_type"] for row in rows] == ["autonomy.blocker", "autonomy.next"]
    assert rows[0]["payload"]["data"]["name"] == "drive_failed"
    assert rows[0]["payload"]["ticket"] == "STARTER-276"
    assert rows[1]["payload"]["data"]["action"] == "retry_next_cycle"


def test_plugin_gate_skip_emits_semantic_observability_trace(
    tmp_path, capsys, monkeypatch
) -> None:
    import koru.observability_writer as writer

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            assert tz is UTC
            return cls(2026, 5, 25, 17, 43, 7, tzinfo=UTC)

    monkeypatch.setattr(writer, "datetime", _FixedDatetime)

    class _Client:
        def status(self) -> dict[str, object]:
            return {"plugins": []}

    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["STARTER-277"],
        last_status="waiting_input",
        last_message="",
        last_ticket_id="STARTER-277",
    )
    messages: list[str] = []
    telemetry: dict[str, object] = {}

    status = _plugin_gate_status(
        tmp_path,
        736,
        queue_result,
        _Client(),
        "vscodium",
        "continue STARTER-277",
        True,
        telemetry,
        messages.append,
    )

    rows = [
        json.loads(raw)
        for raw in observability_event_store_path(tmp_path).read_text(encoding="utf-8").splitlines()
    ]
    assert status == "skipped(plugin_not_connected)"
    assert telemetry["autopilot_skipped_plugin_blocker"] == "plugin_not_connected"
    assert [row["event_type"] for row in rows] == [
        "autopilot.intent",
        "autopilot.route.decision",
        "autopilot.drive.failed",
        "autonomy.blocker",
        "autonomy.next",
    ]
    assert {row["payload"]["corr"] for row in rows} == {"auto-736-preflight"}
    assert rows[0]["payload"]["ticket"] == "STARTER-277"
    assert rows[2]["payload"]["data"]["code"] == "plugin_not_connected"
    assert rows[4]["payload"]["data"]["action"] == "reload_reconnect_plugin"
    terminal = capsys.readouterr().err
    assert any(
        line.startswith("[17:43:07] koru ▸ OBS-PATH:")
        for line in terminal.splitlines()
    )
    assert "OBS-PATH:" in terminal
    assert "intent(deliver_prompt_to_ide_chat) -> decision(skip)" in terminal
    assert "failure(plugin_not_connected)" in terminal


def test_plugin_gate_mismatch_attempts_recovery_reload_for_same_workspace(
    tmp_path,
    monkeypatch,
) -> None:
    import koru.autonomous_cycle_orchestrator as orchestrator
    import koru.ide_adapters.ide_reload as ide_reload

    reason = (
        "ide=vscodium version=0.2.7 blocked: connected autopilot plugin "
        "build mismatch: connected=old expected=new; reload the IDE window "
        "after installing the current VSIX, then run `koru: Connect autopilot daemon`."
    )
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["STARTER-370"],
        last_status="waiting_input",
        last_message="",
        last_ticket_id="STARTER-370",
    )

    class _Client:
        def status(self) -> dict[str, object]:
            return {
                "plugins": [
                    {
                        "ide": "vscodium",
                        "workspaceFolders": [str(tmp_path)],
                    }
                ]
            }

    class _Outcome:
        attempted = True
        ok = True
        method = "reuse-window"
        detail = None

    reload_env: list[str | None] = []

    def _fake_reload(ide: str, *, project) -> _Outcome:
        assert ide == "vscodium"
        assert project == tmp_path
        reload_env.append(os.environ.get("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD"))
        return _Outcome()

    orchestrator._PLUGIN_GATE_RECOVERY_LAST_TS.clear()
    monkeypatch.delenv("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_COMMAND_PALETTE_RELOAD", raising=False)
    monkeypatch.setattr(ide_reload, "_running_from_integrated_ide_terminal", lambda: False)
    monkeypatch.setattr(ide_reload, "_on_wayland", lambda: False)
    monkeypatch.setattr(
        orchestrator,
        "_client_has_usable_plugin",
        lambda _client, _ide: (False, reason),
    )
    monkeypatch.setattr(ide_reload, "try_reload_vscode_family_ide", _fake_reload)

    telemetry: dict[str, object] = {}
    messages: list[str] = []
    status = _plugin_gate_status(
        tmp_path,
        1196,
        queue_result,
        _Client(),
        "vscodium",
        "continue STARTER-370",
        True,
        telemetry,
        messages.append,
    )

    assert status == "skipped(plugin_version_mismatch)"
    assert telemetry["autopilot_plugin_recovery_attempted"] is True
    assert reload_env == ["1"]
    assert os.environ.get("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD") is None
    assert any("requested IDE reload/reconnect" in message for message in messages)


def test_plugin_bootstrap_blocker_emits_control_command_dsl(tmp_path, capsys) -> None:
    emitted = _emit_plugin_bootstrap_blocker_trace(
        tmp_path,
        autopilot_ide="vscodium",
        reason="daemon status plugin list is empty",
        wait_seconds=5.0,
        plugin_install_status="already_installed",
    )

    assert emitted is True
    rows = [
        json.loads(raw)
        for raw in observability_event_store_path(tmp_path).read_text(encoding="utf-8").splitlines()
    ]
    assert [row["event_type"] for row in rows] == [
        "autopilot.intent",
        "autopilot.route.decision",
        "autopilot.drive.failed",
        "autonomy.blocker",
        "autonomy.next",
        "control.command",
        "control.command",
    ]
    assert {row["payload"]["corr"] for row in rows} == {"bootstrap-plugin-vscodium"}
    gui_command = rows[5]["payload"]["data"]
    assert gui_command["surface"] == "desktop_gui"
    assert gui_command["interface_id"] == "ide_command_palette"
    assert gui_command["operation"] == "command_palette_sequence"
    assert gui_command["replayable"] is False
    shell = rows[6]["payload"]["data"]
    assert shell["surface"] == "shell_cli"
    assert shell["args"]["argv"] == ["koru", "autopilot", "status", "--explain"]
    terminal = capsys.readouterr().err
    assert "OBS-PATH:" in terminal
    assert "command(ide_command_palette command_palette_sequence)" in terminal
    assert "command(shell_cli koru)" in terminal


def test_plugin_wait_trace_replaces_legacy_reload_lines(tmp_path) -> None:
    messages: list[str] = []
    reload_lines: list[str] = []

    class _Client:
        pass

    result = wait_for_plugin_connection(
        Namespace(autopilot_plugin_wait_seconds=0.0, emit_events="text"),
        "vscodium",
        "already_installed",
        None,
        client=_Client(),
        project=tmp_path,
        wait_for_plugin=lambda *_args, **_kwargs: False,
        stdio_info=lambda msg, **_kwargs: messages.append(msg),
        plugin_status_reason=lambda *_args: "daemon status plugin list is empty",
        plugin_blocker_line=lambda reason, ide: f"blocker {ide} {reason}",
        plugin_reason_requires_reload=lambda _reason: True,
        retry_after_reload=lambda *_args, **_kwargs: None,
        emit_reload_lines=lambda ide, **_kwargs: reload_lines.append(ide),
    )

    assert result is False
    assert any("no connected autopilot plugin" in msg for msg in messages)
    assert reload_lines == []
    rows = [
        json.loads(raw)
        for raw in observability_event_store_path(tmp_path).read_text(encoding="utf-8").splitlines()
    ]
    assert rows[-2]["event_type"] == "control.command"
    assert rows[-1]["payload"]["data"]["args"]["argv"] == [
        "koru",
        "autopilot",
        "status",
        "--explain",
    ]


def test_plugin_wait_build_mismatch_enables_reuse_window_for_same_workspace(
    tmp_path,
    monkeypatch,
) -> None:
    retry_env: list[str | None] = []
    reconnect_calls: list[str] = []

    class _Client:
        def status(self) -> dict:
            return {
                "plugins": [
                    {
                        "ide": "vscodium",
                        "workspaceFolders": [str(tmp_path)],
                    }
                ]
            }

    def _retry(*_args, **_kwargs):
        retry_env.append(os.environ.get("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD"))
        return True

    import koru.ide_adapters.ide_reload as ide_reload

    monkeypatch.delenv("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_COMMAND_PALETTE_RELOAD", raising=False)
    monkeypatch.setattr(ide_reload, "_running_from_integrated_ide_terminal", lambda: False)
    monkeypatch.setattr(ide_reload, "_on_wayland", lambda: False)
    monkeypatch.setattr(
        plugin_wait_mod,
        "_try_plugin_reconnect_pipeline",
        lambda *_args, **_kwargs: reconnect_calls.append("reconnect") or False,
    )

    result = wait_for_plugin_connection(
        Namespace(autopilot_plugin_wait_seconds=0.0, emit_events="text"),
        "vscodium",
        "already_installed",
        None,
        client=_Client(),
        project=tmp_path,
        wait_for_plugin=lambda *_args, **_kwargs: False,
        stdio_info=lambda *_args, **_kwargs: None,
        plugin_status_reason=lambda *_args: (
            "ide=vscodium version=0.2.7 blocked: connected autopilot "
            "plugin build mismatch: connected=old expected=new"
        ),
        plugin_blocker_line=lambda reason, ide: f"blocker {ide} {reason}",
        plugin_reason_requires_reload=lambda reason: "build mismatch" in reason,
        retry_after_reload=_retry,
    )

    assert result is True
    assert retry_env == ["1"]
    assert reconnect_calls == []
    assert os.environ.get("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD") is None


def test_control_commands_cover_api_shell_plugin_and_desktop_surfaces(tmp_path) -> None:
    api_command(
        tmp_path,
        corr="api-1",
        method="GET",
        path="/api/autonomy/trace",
        query={"ticket": "STARTER-276"},
    )
    shell_command(
        tmp_path,
        corr="shell-1",
        argv=["koru", "autopilot", "trace", "--format", "dsl"],
    )
    plugin_socket_command(
        tmp_path,
        corr="plugin-1",
        message_type="chat.send",
        ide="vscodium",
        payload={"chars": 553, "submit": True},
    )
    desktop_gui_command(
        tmp_path,
        corr="desktop-1",
        operation="type_text",
        backend="xdotool",
        payload={"chars": 12},
    )

    rows = [
        json.loads(raw)
        for raw in observability_event_store_path(tmp_path).read_text(encoding="utf-8").splitlines()
    ]
    assert [row["event_type"] for row in rows] == ["control.command"] * 4
    surfaces = [row["payload"]["data"]["surface"] for row in rows]
    assert surfaces == ["api", "shell_cli", "ide_chat", "desktop_gui"]
    operations = "\n".join(row["payload"]["data"]["operation"] for row in rows)
    assert "GET /api/autonomy/trace" in operations
    assert "chat.send" in operations


def test_control_command_dsl_preserves_structured_args_with_spaces() -> None:
    event = control_command(
        corr="shell-space",
        surface="shell_cli",
        interface_id="subprocess_local_tools",
        transport="subprocess",
        operation="koru",
        args={"argv": ["koru", "autopilot", "drive", "--prompt", "hello world"]},
    )

    parsed = parse_observability_dsl(event.to_dsl())

    assert parsed.data["args"]["argv"][-1] == "hello world"
