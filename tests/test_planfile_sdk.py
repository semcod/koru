"""Contract tests for Koru's PlanfileClient lifecycle gateway."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from koru.queue.planfile_sdk import parse_lifecycle_request, planfile_lifecycle_command


def _transition(*, code: str = "ok", ticket: dict | None = None, error: str = ""):
    return SimpleNamespace(code=code, ticket=ticket, error=error, attempts=1)


class _Client:
    def __init__(self, _project: str, transition=None) -> None:
        self.transition = transition
        self.calls: list[tuple[str, str, dict]] = []

    def _result(self, operation: str, ticket_id: str, kwargs: dict):
        self.calls.append((operation, ticket_id, kwargs))
        return self.transition or _transition(ticket={"id": ticket_id, "status": "open"})

    def claim(self, ticket_id: str, **kwargs):
        return self._result("claim", ticket_id, kwargs)

    def start(self, ticket_id: str, **kwargs):
        return self._result("start", ticket_id, kwargs)

    def complete(self, ticket_id: str, **kwargs):
        return self._result("complete", ticket_id, kwargs)

    def fail(self, ticket_id: str, **kwargs):
        return self._result("fail", ticket_id, kwargs)

    def ready(self, ticket_id: str, **kwargs):
        return self._result("ready", ticket_id, kwargs)

    def block(self, ticket_id: str, **kwargs):
        return self._result("block", ticket_id, kwargs)

    def note(self, ticket_id: str, note: str):
        return self._result("note", ticket_id, {"note": note})


def test_parse_lifecycle_request_maps_cli_without_policy() -> None:
    claim = parse_lifecycle_request(
        ["ticket", "claim", "PLF-1", "--assigned-to", "koru", "--lease-seconds", "60"]
    )
    note = parse_lifecycle_request(["ticket", "update", "PLF-1", "--note", "evidence"])
    failed = parse_lifecycle_request(
        ["ticket", "fail", "PLF-1", "--error", "temporary", "--actor", "koru"]
    )
    ready = parse_lifecycle_request(
        ["ticket", "ready", "PLF-1", "--note", "Retry 2/3 scheduled"]
    )

    assert claim is not None
    assert claim.operation == "claim"
    assert claim.kwargs == {"assigned_to": "koru", "lease_seconds": 60}
    assert note is not None
    assert note.operation == "note"
    assert note.kwargs == {"note": "evidence"}
    assert failed is not None
    assert failed.operation == "fail"
    assert failed.kwargs == {"error": "temporary", "actor": "koru"}
    assert ready is not None
    assert ready.operation == "ready"
    assert ready.kwargs == {"note": "Retry 2/3 scheduled"}
    assert parse_lifecycle_request(["ticket", "delete", "PLF-1"]) is None
    assert parse_lifecycle_request(["ticket", "done", "PLF-1", "--unknown", "x"]) is None


def test_parse_lifecycle_request_covers_block_complete_and_edge_cases() -> None:
    # Characterisation before refactor: block, the complete alias, and the
    # validation edge cases the existing tests never exercised.
    block = parse_lifecycle_request(
        ["ticket", "block", "PLF-1", "--reason", "dep", "--actor", "koru"]
    )
    assert block is not None
    assert block.operation == "block"
    assert block.kwargs == {"reason": "dep", "actor": "koru"}

    complete = parse_lifecycle_request(["ticket", "complete", "PLF-1", "--note", "n"])
    assert complete is not None
    assert complete.operation == "complete"
    assert complete.kwargs == {"note": "n"}

    start = parse_lifecycle_request(
        ["ticket", "start", "PLF-1", "--assigned-to", "koru"]
    )
    assert start is not None and start.kwargs == {"assigned_to": "koru"}

    # short/long flag collisions and unknown options must all reject
    assert parse_lifecycle_request(
        ["ticket", "fail", "PLF-1", "--error", "a", "-e", "b"]
    ) is None
    assert parse_lifecycle_request(
        ["ticket", "ready", "PLF-1", "--note", "a", "-n", "b"]
    ) is None
    assert parse_lifecycle_request(["ticket", "fail", "PLF-1"]) is None  # error required
    assert parse_lifecycle_request(["ticket", "block", "PLF-1", "--bad", "x"]) is None
    assert parse_lifecycle_request(["ticket", "claim", "PLF-1", "--lease-seconds", "abc"]) is None
    assert parse_lifecycle_request(["ticket", "update", "PLF-1", "--reason", "x"]) is None
    assert parse_lifecycle_request(["ticket"]) is None
    assert parse_lifecycle_request(["ticket", "claim", "  "]) is None
    # -n short form for ready
    ready_short = parse_lifecycle_request(["ticket", "ready", "PLF-1", "-n", "go"])
    assert ready_short is not None and ready_short.kwargs == {"note": "go"}


def test_sdk_executes_mutation_once_and_returns_typed_failure(tmp_path: Path) -> None:
    client = _Client(
        str(tmp_path),
        transition=_transition(code="invalid_transition", error="already done"),
    )
    cli_calls: list[list[str]] = []

    def runner(command, _project):
        cli_calls.append(list(command))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    result = planfile_lifecycle_command(
        tmp_path,
        ["ticket", "done", "PLF-1"],
        runner,
        prefer_sdk=True,
        verify=False,
        client_factory=lambda _project: client,
    )

    assert result.returncode == 1
    assert result.transition_code == "invalid_transition"
    assert result.stderr == "already done"
    assert client.calls == [("complete", "PLF-1", {})]
    assert cli_calls == []


def test_successful_sdk_transition_is_verified_by_read_only_cli(tmp_path: Path) -> None:
    ticket = {
        "id": "PLF-2",
        "status": "in_progress",
        "execution": {"state": "running", "assigned_to": "koru"},
    }
    client = _Client(str(tmp_path), transition=_transition(ticket=ticket))
    cli_calls: list[list[str]] = []

    def runner(command, _project):
        cli_calls.append(list(command))
        return SimpleNamespace(returncode=0, stdout=json.dumps(ticket), stderr="")

    result = planfile_lifecycle_command(
        tmp_path,
        ["ticket", "start", "PLF-2", "--assigned-to", "koru"],
        runner,
        prefer_sdk=True,
        verify=True,
        client_factory=lambda _project: client,
    )

    assert result.returncode == 0
    assert result.transition_code == "ok"
    assert result.transport == "sdk"
    assert result.parity == "verified"
    assert client.calls == [("start", "PLF-2", {"assigned_to": "koru"})]
    assert len(cli_calls) == 1
    assert cli_calls[0][-5:] == ["ticket", "show", "PLF-2", "--format", "json"]


def test_parity_mismatch_is_telemetry_not_second_mutation(tmp_path: Path, caplog) -> None:
    sdk_ticket = {"id": "PLF-3", "status": "done", "execution": {"state": "done"}}
    cli_ticket = {"id": "PLF-3", "status": "open", "execution": {"state": "ready"}}
    client = _Client(str(tmp_path), transition=_transition(ticket=sdk_ticket))

    result = planfile_lifecycle_command(
        tmp_path,
        ["ticket", "done", "PLF-3"],
        lambda *_args: SimpleNamespace(returncode=0, stdout=json.dumps(cli_ticket), stderr=""),
        prefer_sdk=True,
        verify=True,
        client_factory=lambda _project: client,
    )

    assert result.returncode == 0
    assert result.parity == "mismatch"
    assert client.calls == [("complete", "PLF-3", {})]
    assert "parity mismatch" in caplog.text


def test_missing_sdk_falls_back_to_existing_cli_path(tmp_path: Path, monkeypatch) -> None:
    calls: list[list[str]] = []

    def runner(command, _project):
        calls.append(list(command))
        return SimpleNamespace(returncode=0, stdout="legacy", stderr="")

    monkeypatch.setenv("KORU_PLANFILE_CMD", "/pinned/planfile")
    result = planfile_lifecycle_command(
        tmp_path,
        ["ticket", "start", "PLF-4"],
        runner,
        prefer_sdk=True,
        client_factory=lambda _project: (_ for _ in ()).throw(ModuleNotFoundError()),
    )

    assert result.returncode == 0
    assert result.stdout == "legacy"
    assert calls == [["/pinned/planfile", "ticket", "start", "PLF-4"]]


def test_older_sdk_falls_back_for_lifecycle_method_it_does_not_expose(
    tmp_path: Path, monkeypatch,
) -> None:
    calls: list[list[str]] = []

    def runner(command, _project):
        calls.append(list(command))
        return SimpleNamespace(returncode=0, stdout="legacy fail", stderr="")

    monkeypatch.setenv("KORU_PLANFILE_CMD", "/pinned/planfile")
    result = planfile_lifecycle_command(
        tmp_path,
        ["ticket", "fail", "PLF-5", "--error", "temporary"],
        runner,
        prefer_sdk=True,
        client_factory=lambda _project: SimpleNamespace(start=lambda *_args: None),
    )

    assert result.returncode == 0
    assert result.stdout == "legacy fail"
    assert calls == [
        ["/pinned/planfile", "ticket", "fail", "PLF-5", "--error", "temporary"]
    ]


def test_real_planfile_client_lifecycle_and_cli_readback(tmp_path: Path) -> None:
    from planfile import Planfile

    from koru.observability_writer import observability_event_store_path
    from koru.queue.planfile_ticket_note import append_shell_evidence_note
    from koru.queue.runners import run_process

    backend = Planfile(str(tmp_path))
    ticket = backend.create_ticket(name="Koru SDK contract")

    claim = planfile_lifecycle_command(
        tmp_path,
        [
            "ticket",
            "claim",
            ticket.id,
            "--assigned-to",
            "koru-test",
            "--lease-seconds",
            "60",
        ],
        run_process,
    )
    start = planfile_lifecycle_command(
        tmp_path,
        ["ticket", "start", ticket.id, "--assigned-to", "koru-test"],
        run_process,
    )
    failed = planfile_lifecycle_command(
        tmp_path,
        ["ticket", "fail", ticket.id, "--error", "temporary failure"],
        run_process,
    )
    ready = planfile_lifecycle_command(
        tmp_path,
        ["ticket", "ready", ticket.id, "--note", "Retry 2/3 scheduled"],
        run_process,
    )
    start = planfile_lifecycle_command(
        tmp_path,
        ["ticket", "start", ticket.id, "--assigned-to", "koru-test"],
        run_process,
    )
    noted, note_kind = append_shell_evidence_note(
        tmp_path,
        ticket.id,
        "typed evidence",
        run_id="sdk-contract",
        planfile_runner=run_process,
    )
    done = planfile_lifecycle_command(
        tmp_path,
        ["ticket", "done", ticket.id],
        run_process,
    )

    stored = backend.get_ticket(ticket.id)
    assert [(claim.transition_code, claim.parity), (start.transition_code, start.parity)] == [
        ("ok", "verified"),
        ("ok", "verified"),
    ]
    assert (failed.transition_code, failed.parity) == ("ok", "verified")
    assert (ready.transition_code, ready.parity) == ("ok", "verified")
    assert (done.transition_code, done.parity) == ("ok", "verified")
    assert (noted.transition_code, noted.parity, note_kind) == ("ok", "verified", "sdk")
    assert stored.status.value == "done"
    assert stored.execution.state == "done"
    assert stored.outputs.notes == ["Retry 2/3 scheduled", "typed evidence"]
    events = [
        json.loads(line)
        for line in observability_event_store_path(tmp_path).read_text(encoding="utf-8").splitlines()
    ]
    sdk_commands = [
        event["payload"]["data"]
        for event in events
        if event["event_type"] == "control.command"
        and event["payload"]["data"]["transport"] == "python_sdk"
    ]
    assert [command["operation"] for command in sdk_commands] == [
        "ticket.claim",
        "ticket.start",
        "ticket.fail",
        "ticket.ready",
        "ticket.start",
        "ticket.note",
        "ticket.complete",
    ]
    assert all(command["replayable"] is False for command in sdk_commands)
