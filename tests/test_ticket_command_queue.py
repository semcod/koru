import pytest

from koru.cli_ticket import ticket_main


def test_local_queue_preserved_without_fabricated_human_approval(tmp_path, monkeypatch):
    import koru.cli_ticket_queue as queue
    import koru.queue_cli_helpers as helpers

    observed = []
    monkeypatch.setattr(queue, "_sync_github", lambda *_: pytest.fail("implicit backlog synchronization"))
    monkeypatch.setattr(helpers, "emit_queue_run_started", lambda *_: None)
    monkeypatch.setattr(helpers, "open_queue_run_log", lambda *_: None)

    def run(args, log, **runners):
        observed.append(args)
        assert runners["prompt_runner"]("Approve publication?", "PLF-1") is None
        return 3

    monkeypatch.setattr(helpers, "run_queue_single_mode", run)
    assert ticket_main(["auto", "PLF-1", "--project", str(tmp_path)]) == 3
    assert observed[0].ticket == "PLF-1" and observed[0].project == tmp_path


def test_auto_url_uses_exact_issue_executor(monkeypatch):
    import koru.ticket_command.service as service

    calls = []
    monkeypatch.setattr(service, "run_ticket", lambda *args, **kw: calls.append((args, kw)) or {"state": "planned"})
    assert ticket_main(["auto", "https://github.com/maskservice/c2004/issues/12", "--dry-run"]) == 0
    assert calls[0][0][0] == "https://github.com/maskservice/c2004/issues/12"
    assert calls[0][1]["dry_run"]


def test_queue_dry_run_cannot_synchronize_or_execute(tmp_path, monkeypatch):
    import koru.cli_ticket_queue as queue

    monkeypatch.setattr(queue, "_sync_github", lambda *_: pytest.fail("dry-run synchronized backlog"))
    with pytest.raises(SystemExit) as caught:
        ticket_main(["auto", "--project", str(tmp_path), "--dry-run", "--sync"])
    assert caught.value.code == 2


@pytest.mark.parametrize("target", ["http://github.com/a/b/issues/12", "github.com/a/b/issues/*"])
def test_invalid_url_never_selects_all_local_tickets(target):
    with pytest.raises(SystemExit) as caught:
        ticket_main(["auto", target])
    assert caught.value.code == 2
