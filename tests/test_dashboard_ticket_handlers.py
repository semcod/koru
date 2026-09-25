from __future__ import annotations

import subprocess
from pathlib import Path
from unittest import mock

from koruapi.dashboard_tickets import DashboardTicketCommands, DashboardTicketQueries


def test_dashboard_ticket_queries_list_tickets_parses_payload(tmp_path: Path) -> None:
    queries = DashboardTicketQueries()
    result = subprocess.CompletedProcess(
        ["planfile", "ticket", "list"],
        0,
        stdout='[{"id":"T-1","status":"open"}]',
        stderr="",
    )

    with mock.patch("koruapi.dashboard_tickets.planfile_command", return_value=result):
        tickets = queries.list_tickets(tmp_path)

    assert tickets == [{"id": "T-1", "status": "open"}]


def test_dashboard_ticket_commands_bulk_approve_runs_claim_start_done(tmp_path: Path) -> None:
    queries = DashboardTicketQueries()
    commands = DashboardTicketCommands(queries=queries)
    ok = subprocess.CompletedProcess(["planfile"], 0, stdout="", stderr="")

    with mock.patch.object(DashboardTicketQueries, "waiting_input_ticket_ids", return_value={"T-1"}):
        with mock.patch("koruapi.dashboard_tickets.planfile_command", return_value=ok) as cmd:
            result = commands.bulk_waiting_input_action(
                tmp_path,
                ticket_ids=["T-1"],
                action="approve",
                reason="",
            )

    assert result["ok"] is True
    assert result["applied"][0]["ok"] is True
    calls = [call.args[1] for call in cmd.call_args_list]
    assert ["ticket", "claim", "T-1", "--assigned-to", "koru-web"] in calls
    assert ["ticket", "start", "T-1"] in calls
    assert ["ticket", "done", "T-1"] in calls


def test_dashboard_ticket_commands_bulk_reject_runs_block(tmp_path: Path) -> None:
    queries = DashboardTicketQueries()
    commands = DashboardTicketCommands(queries=queries)
    ok = subprocess.CompletedProcess(["planfile"], 0, stdout="", stderr="")

    with mock.patch.object(DashboardTicketQueries, "waiting_input_ticket_ids", return_value={"T-2"}):
        with mock.patch("koruapi.dashboard_tickets.planfile_command", return_value=ok) as cmd:
            result = commands.bulk_waiting_input_action(
                tmp_path,
                ticket_ids=["T-2"],
                action="reject",
                reason="No",
            )

    assert result["ok"] is True
    calls = [call.args[1] for call in cmd.call_args_list]
    assert ["ticket", "block", "T-2", "--reason", "No"] in calls


def test_dashboard_ticket_queries_waiting_input_includes_human_tickets(tmp_path: Path) -> None:
    queries = DashboardTicketQueries()
    result = subprocess.CompletedProcess(
        ["planfile", "ticket", "list"],
        0,
        stdout='[{"id":"T-1","status":"waiting_input"},{"id":"T-2","status":"open","executor":{"kind":"human"}},{"id":"T-3","status":"open","executor":{"kind":"llm"}}]',
        stderr="",
    )
    with mock.patch("koruapi.dashboard_tickets.planfile_command", return_value=result):
        waiting = queries.waiting_input_ticket_ids(tmp_path)
    assert waiting == {"T-1", "T-2"}


def test_dashboard_ticket_commands_bulk_delegate(tmp_path: Path) -> None:
    queries = DashboardTicketQueries()
    commands = DashboardTicketCommands(queries=queries)

    with mock.patch.object(DashboardTicketQueries, "waiting_input_ticket_ids", return_value={"T-1"}):
        with mock.patch.object(
            DashboardTicketCommands,
            "delegate_ticket_from_dashboard",
            return_value={"ok": True, "ticket_id": "T-1"},
        ) as mock_del:
            result = commands.bulk_waiting_input_action(
                tmp_path,
                ticket_ids=["T-1"],
                action="delegate",
                reason="Delegated from web",
            )

    assert result["ok"] is True
    assert result["applied"][0]["action"] == "delegate"
    mock_del.assert_called_once_with(
        tmp_path,
        ticket_id="T-1",
        executor_kind="llm",
        notes="Delegated from web",
    )


def test_delegate_ticket_from_dashboard_updates_fields(tmp_path: Path) -> None:
    import yaml

    from koruapi.dashboard_tickets import delegate_ticket_from_dashboard

    sprints_dir = tmp_path / ".planfile" / "sprints"
    sprints_dir.mkdir(parents=True)
    sprint_file = sprints_dir / "current.yaml"
    initial_data = {
        "sprint": {
            "name": "current",
            "tickets": {
                "T-1": {
                    "id": "T-1",
                    "status": "waiting_input",
                    "executor": {"kind": "human", "mode": "interactive"},
                    "execution": {"state": "blocked", "queue": "default"},
                    "inputs": {"prompt": "Initial task"},
                    "outputs": {"notes": []},
                    "labels": ["koru"],
                }
            },
        }
    }
    sprint_file.write_text(yaml.safe_dump(initial_data), encoding="utf-8")

    res = delegate_ticket_from_dashboard(
        tmp_path,
        ticket_id="T-1",
        executor_kind="llm",
        prompt_addition="Extra instruction",
        notes="Operator approved",
        priority="high",
        queue_name="urgent",
    )
    assert res["ok"] is True
    assert res["changed"] is True

    updated_data = yaml.safe_load(sprint_file.read_text(encoding="utf-8"))
    ticket = updated_data["sprint"]["tickets"]["T-1"]
    assert ticket["status"] == "open"
    assert ticket["execution"]["state"] == "ready"
    assert ticket["execution"]["queue"] == "urgent"
    assert ticket["priority"] == "high"
    assert ticket["executor"]["kind"] == "llm"
    assert ticket["executor"]["mode"] == "automatic"
    assert "Extra instruction" in ticket["inputs"]["prompt"]
    assert "llm-ready" in ticket["labels"]
    assert any("Operator Delegation: Operator approved" in note for note in ticket["outputs"]["notes"])


def test_post_ticket_delegate_success() -> None:
    from koruapi.dashboard_routes import _post_ticket_delegate
    from koruapi.dashboard_serve_utils import ServeConfig

    handler = mock.Mock()
    handler._selected_project.return_value = Path("/tmp/proj")
    config = mock.Mock(spec=ServeConfig)

    with mock.patch(
        "koruapi.dashboard_routes.delegate_ticket_from_dashboard", return_value={"ok": True, "ticket_id": "T-1"}
    ) as mock_fn:
        _post_ticket_delegate(handler, config, {"ticket_id": "T-1", "executor_kind": "llm", "prompt_addition": "notes"})

    mock_fn.assert_called_once_with(
        Path("/tmp/proj"),
        ticket_id="T-1",
        executor_kind="llm",
        executor_mode="automatic",
        prompt_addition="notes",
        notes=None,
        priority=None,
        queue_name=None,
    )
    handler._send_json.assert_called_once_with({"ok": True, "ticket_id": "T-1"})


def test_post_ticket_delegate_missing_id() -> None:
    from koruapi.dashboard_routes import _post_ticket_delegate
    from koruapi.dashboard_serve_utils import ServeConfig

    handler = mock.Mock()
    config = mock.Mock(spec=ServeConfig)
    _post_ticket_delegate(handler, config, {})
    handler._send_json.assert_called_once_with({"error": "ticket_id is required"}, status=400)


def test_post_waiting_input_bulk_supports_delegate() -> None:
    from koruapi.dashboard_routes import _post_waiting_input_bulk
    from koruapi.dashboard_serve_utils import ServeConfig

    handler = mock.Mock()
    handler._selected_project.return_value = Path("/tmp/proj")
    config = mock.Mock(spec=ServeConfig)

    with mock.patch(
        "koruapi.dashboard_routes.bulk_waiting_input_action", return_value={"ok": True, "action": "delegate"}
    ) as mock_bulk:
        _post_waiting_input_bulk(
            handler, config, {"action": "delegate", "ticket_ids": ["T-1"], "reason": "Bulk delegate"}
        )

    mock_bulk.assert_called_once_with(
        Path("/tmp/proj"),
        ticket_ids=["T-1"],
        action="delegate",
        reason="Bulk delegate",
    )
    handler._send_json.assert_called_once_with({"ok": True, "action": "delegate"})
