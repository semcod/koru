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


def test_ticket_next_displays_ticket_text_and_brief(tmp_path, monkeypatch, capsys):
    import json
    import koru.queue.runner as runner

    sample = {
        "id": "PLF-999",
        "name": "Refactor parser logic",
        "priority": "high",
        "status": "open",
        "executor": {"kind": "human"},
        "execution": {"queue": "default"},
        "labels": ["refactor", "parser"],
        "files": ["src/parser.py"],
        "description": "Clean up cyclomatic complexity in parser.",
    }
    monkeypatch.setattr(runner, "_next_ticket_or_result", lambda *a, **kw: (sample, None))

    assert ticket_main(["next", "--project", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "PLF-999" in out
    assert "Refactor parser logic" in out
    assert "high" in out
    assert "koru ticket auto PLF-999" in out

    assert ticket_main(["next", "--project", str(tmp_path), "--brief"]) == 0
    brief_out = capsys.readouterr().out.strip()
    assert brief_out == "PLF-999: Refactor parser logic"


def test_ticket_next_json_and_markdown_formats(tmp_path, monkeypatch, capsys):
    import json
    import koru.queue.runner as runner

    sample = {
        "id": "PLF-888",
        "name": "Implement feature X",
        "priority": "normal",
        "status": "open",
        "executor": {"kind": "command"},
        "execution": {"queue": "default"},
        "labels": ["feature"],
        "files": ["src/feature.py"],
        "description": "Detailed description of feature X.",
    }
    monkeypatch.setattr(runner, "_next_ticket_or_result", lambda *a, **kw: (sample, None))

    assert ticket_main(["next", "--project", str(tmp_path), "--format", "json"]) == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == "PLF-888"
    assert parsed["name"] == "Implement feature X"

    assert ticket_main(["next", "--project", str(tmp_path), "--format", "markdown"]) == 0
    md_out = capsys.readouterr().out
    assert "### Next Ticket: PLF-888 — Implement feature X" in md_out
    assert "`normal`" in md_out
    assert "koru ticket auto PLF-888" in md_out


def test_ticket_next_idle_queue(tmp_path, monkeypatch, capsys):
    import json
    import koru.queue.runner as runner

    monkeypatch.setattr(runner, "_next_ticket_or_result", lambda *a, **kw: (None, None))

    assert ticket_main(["next", "--project", str(tmp_path)]) == 0
    assert "idle" in capsys.readouterr().out.lower()

    assert ticket_main(["next", "--project", str(tmp_path), "--brief"]) == 0
    assert "(no runnable ticket)" in capsys.readouterr().out

    assert ticket_main(["next", "--project", str(tmp_path), "--format", "json"]) == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["status"] == "idle"
    assert parsed["ticket"] is None


def test_ticket_next_error_handling(tmp_path, monkeypatch, capsys):
    from types import SimpleNamespace
    import koru.queue.runner as runner

    error_res = SimpleNamespace(status="planfile_error", message="Syntax error in sprint file", exit_code=1)
    monkeypatch.setattr(runner, "_next_ticket_or_result", lambda *a, **kw: (None, error_res))

    assert ticket_main(["next", "--project", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "Syntax error in sprint file" in err
