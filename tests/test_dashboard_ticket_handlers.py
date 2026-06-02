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
