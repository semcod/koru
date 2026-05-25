from __future__ import annotations

import json
from argparse import Namespace

from koru.autonomous_cycle_orchestrator import _emit_autopilot_observability_outcome
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


def test_observability_writer_persists_jsonl_and_dsl_log(tmp_path) -> None:
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

    assert line.startswith("[17:10:34] koru > OBS:")
    assert "session=wayland" in line
    assert "ticket=STARTER-277" in line
    assert "failure code=autopilot_daemon_timeout" in line
    assert 'message="daemon unreachable: timed out"' in line
    assert "too noisy" not in line


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
