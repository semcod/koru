"""List delivery preserves the scoped runner and its publication boundary."""

import fcntl
import json
from types import SimpleNamespace

import pytest

from koru.cli_ticket import ticket_main
from koru.ticket_command.batch import run_issue_list
from koru.ticket_command.profile import git, load_profile, parse_issue, parse_target
from koru.ticket_command.service import run_ticket
from tests.test_ticket_command import repo as repo
from tests.test_ticket_command_reporting import execution as execution

LIST = "https://github.com/maskservice/c2004/issues/"


def issue(number, **overrides):
    return SimpleNamespace(
        number=number,
        **{
            "html_url": LIST + str(number),
            "state": "open",
            "pull_request": None,
            **overrides,
        },
    )


def backend_for(pages):
    observed = []
    issues = {item.number: item for page in pages for item in page}

    def get_issues(**kwargs):
        assert kwargs == {"state": "open", "sort": "created", "direction": "asc"}
        for page in pages:
            observed.append("page")
            yield from page

    return SimpleNamespace(repo=SimpleNamespace(get_issues=get_issues, get_issue=issues.__getitem__)), observed


@pytest.mark.parametrize("url", [LIST, LIST.rstrip("/")])
def test_list_preview_routes_without_writing_even_on_dirty_main(repo, monkeypatch, capsys, url):
    import koru.ticket_command.batch as batch

    root, profiles = repo
    (root / "value.py").write_text("Other session\n")
    backend, observed = backend_for([[issue(13), issue(7, pull_request=object())], [issue(12)]])
    monkeypatch.setattr(batch, "github_backend", lambda _: backend)
    monkeypatch.setattr(batch, "run_ticket", lambda *a, **kw: pytest.fail("preview executed a ticket"))
    assert ticket_main([url, "--profiles", str(profiles), "--dry-run"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["issues"] == [LIST + "12", LIST + "13"]
    assert result["delivery"] == "main-only" and result["state"] == "planned"
    assert observed == ["page", "page"]
    assert not (root / ".subactor").exists()
    assert (root / "value.py").read_text() == "Other session\n"


@pytest.mark.parametrize("url", [LIST + "?state=all", LIST + "#all", LIST + "*", LIST + "/", LIST + "0"])
def test_list_target_rejects_ambiguous_suffixes(url):
    with pytest.raises(ValueError):
        parse_target(url)


def test_single_issue_api_does_not_accept_a_list(repo):
    root, profiles = repo
    with pytest.raises(ValueError):
        parse_issue(LIST)
    with pytest.raises(ValueError):
        run_ticket(LIST, profiles)
    assert not (root / ".subactor").exists()


def test_snapshot_is_paginated_deduplicated_and_frozen_before_execution(repo, monkeypatch):
    import koru.ticket_command.batch as batch

    _, profiles = repo
    pages = [[issue(13), issue(7, pull_request=object())], [issue(12), issue(13)]]
    backend, observed = backend_for(pages)
    calls = []

    def execute(url, path, **kwargs):
        assert observed == ["page", "page"]
        assert path == profiles and kwargs["backend"] is backend
        assert kwargs["expected_profile_sha256"] == load_profile(url, profiles)["profile_sha256"]
        calls.append(url)
        # Issues opened during delivery belong to the next invocation.
        pages.append([issue(99)])
        return {"state": "reported", "head": "a" * 40}

    monkeypatch.setattr(batch, "run_ticket", execute)
    result = run_issue_list(LIST, profiles, backend=backend)
    assert calls == [LIST + "12", LIST + "13"]
    assert result["state"] == "completed"
    assert [r["issue"] for r in result["results"]] == calls


def test_empty_list_never_executes(repo, monkeypatch):
    import koru.ticket_command.batch as batch

    _, profiles = repo
    backend, _ = backend_for([[]])
    monkeypatch.setattr(batch, "run_ticket", lambda *a, **kw: pytest.fail("empty list executed"))
    assert run_issue_list(LIST, profiles, backend=backend)["results"] == []


@pytest.mark.parametrize("outcome", ["blocked", "committed", "published", "exception"])
def test_stops_after_failure_or_incomplete_delivery(repo, monkeypatch, outcome):
    import koru.ticket_command.batch as batch

    _, profiles = repo
    backend, _ = backend_for([[issue(12), issue(13), issue(14)]])
    calls = []

    def execute(url, *args, **kwargs):
        calls.append(url)
        if url.endswith("/12"):
            return {"state": "reported"}
        if outcome == "exception":
            raise TimeoutError("Private remote diagnostic must not appear in CLI output")
        return {"state": outcome}

    monkeypatch.setattr(batch, "run_ticket", execute)
    result = run_issue_list(LIST, profiles, backend=backend)
    assert calls == [LIST + "12", LIST + "13"]
    assert result["state"] == "stopped" and result["stopped_at"] == LIST + "13"
    assert result["results"][0]["state"] == "reported"
    assert "Private remote" not in json.dumps(result)


def test_cli_returns_failure_for_a_stopped_list(monkeypatch, capsys):
    import koru.ticket_command.batch as batch

    monkeypatch.setattr(batch, "run_issue_list", lambda *a, **kw: {"state": "stopped", "stopped_at": LIST + "12"})
    assert ticket_main([LIST]) == 1
    assert json.loads(capsys.readouterr().out)["stopped_at"] == LIST + "12"


@pytest.mark.parametrize(
    "bad", [issue(12, html_url="https://github.com/other/repo/issues/12"), issue(12, html_url=LIST + "13")]
)
def test_bad_paginated_identity_prevents_any_execution(repo, monkeypatch, bad):
    import koru.ticket_command.batch as batch

    _, profiles = repo
    backend, _ = backend_for([[issue(10)], [bad]])
    monkeypatch.setattr(batch, "run_ticket", lambda *a, **kw: pytest.fail("partial snapshot was executed"))
    with pytest.raises(RuntimeError, match="no tickets were started"):
        run_issue_list(LIST, profiles, backend=backend)


def test_later_page_failure_does_not_execute_partial_snapshot(repo, monkeypatch):
    import koru.ticket_command.batch as batch

    _, profiles = repo

    def get_issues(**kwargs):
        yield issue(12)
        raise TimeoutError("Private diagnostic")

    backend = SimpleNamespace(repo=SimpleNamespace(get_issues=get_issues))
    monkeypatch.setattr(batch, "run_ticket", lambda *a, **kw: pytest.fail("partial snapshot was executed"))
    with pytest.raises(RuntimeError, match="no tickets were started") as error:
        run_issue_list(LIST, profiles, backend=backend)
    assert "Private diagnostic" not in str(error.value)


def test_closed_new_issue_is_skipped_but_existing_receipt_is_resumed(repo, monkeypatch):
    import koru.ticket_command.batch as batch

    root, profiles = repo
    backend, _ = backend_for([[issue(12), issue(13), issue(14)]])
    backend.repo.get_issue = lambda number: issue(number, state="closed" if number < 14 else "open")
    path = root / ".subactor/cache/koru-tickets/issue-13/state.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}")
    calls = []
    monkeypatch.setattr(batch, "run_ticket", lambda url, *a, **kw: calls.append(url) or {"state": "reported"})
    result = run_issue_list(LIST, profiles, backend=backend)
    assert calls == [LIST + "13", LIST + "14"]
    assert result["results"][0] == {"issue": LIST + "12", "state": "closed"}
    assert result["state"] == "completed"


@pytest.mark.parametrize("change", ["disable", "profile"])
def test_authority_change_stops_the_next_issue(repo, monkeypatch, change):
    import koru.ticket_command.batch as batch

    _, profiles = repo
    backend, _ = backend_for([[issue(12), issue(13)]])
    calls = []

    def execute(url, *args, **kwargs):
        calls.append(url)
        if change == "disable":
            monkeypatch.setenv("KORU_GLOBAL_DISABLE", "1")
        else:
            profiles.write_text(profiles.read_text() + "\n")
        return {"state": "reported"}

    monkeypatch.setattr(batch, "run_ticket", execute)
    result = run_issue_list(LIST, profiles, backend=backend)
    assert result["state"] == "stopped" and calls == [LIST + "12"]


def test_profile_change_during_fresh_issue_read_cannot_expand_scope(repo):
    root, profiles = repo
    backend, _ = backend_for([[issue(12)]])

    def get_issue(number):
        profiles.write_text(profiles.read_text() + "\n")
        return issue(number)

    backend.repo.get_issue = get_issue
    result = run_issue_list(LIST, profiles, backend=backend)
    assert result["state"] == "stopped"
    assert not (root / ".subactor/cache/koru-tickets/issue-12").exists()


@pytest.mark.parametrize("lock_name", ["repository.lock", "queue.lock"])
def test_active_repository_writer_or_queue_prevents_new_execution(repo, lock_name):
    root, profiles = repo
    backend, _ = backend_for([[issue(12)]])
    path = root / ".subactor/cache/koru-tickets" / lock_name
    path.parent.mkdir(parents=True)
    with path.open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if lock_name == "repository.lock":
            # This lock belongs to any issue, not just issue 12.
            with pytest.raises(RuntimeError, match="active Koru"):
                run_ticket(LIST + "99", profiles, backend=backend)
            assert run_issue_list(LIST, profiles, backend=backend)["state"] == "stopped"
        else:
            with pytest.raises(RuntimeError, match="active Koru"):
                run_issue_list(LIST, profiles, backend=backend)
    assert (root / "value.py").read_text() == "value = 1\n"


def test_native_list_repair_waits_for_comment_recovery_and_never_replays(execution, monkeypatch):
    import koru.ticket_command.service as service

    root, profiles, backend, first, publications = execution
    first.number = 12
    second = issue(13, title="Next repair", body="Next private body", comments=[])
    second.get_comments = lambda: iter(second.comments)

    def comment(body):
        result = SimpleNamespace(body=body, html_url=second.html_url + "#issuecomment-2")
        second.comments.append(result)
        return result

    second.create_comment = comment
    backend.repo.get_issues = lambda **kw: (item for item in [first, second] if item.state == "open")
    backend.repo.get_issue = {12: first, 13: second}.__getitem__
    monkeypatch.setattr(
        service, "prepare_workspace", lambda p: (root, f"GITHUB-{p['number']}", git(root, "rev-parse", "HEAD"))
    )
    models = []

    def model(*_):
        n = int((root / "value.py").read_text().split("=")[1])
        if n == 2:
            # Next repair only starts after publication AND Planfile reporting.
            state = json.loads((root / ".subactor/cache/koru-tickets/issue-12/state.json").read_text())
            assert state["state"] == "reported"
        models.append(n)
        patch = (
            "diff --git a/value.py b/value.py\n--- a/value.py\n+++ b/value.py\n"
            f"@@ -1 +1 @@\n-value = {n}\n+value = {n + 1}\n"
        )
        return SimpleNamespace(returncode=0, stdout=patch)

    failed = run_issue_list(LIST, profiles, backend=backend, runner=model)
    assert failed["state"] == "stopped" and models == [1]
    assert len(first.comments) == 1 and second.comments == []
    first.state = "closed"
    queue_path = root / ".subactor/cache/koru-tickets/queue.json"
    before_preview = queue_path.read_bytes()
    preview = run_issue_list(LIST, profiles, dry_run=True, backend=backend)
    assert preview["issues"] == [LIST + "12", LIST + "13"]
    assert queue_path.read_bytes() == before_preview
    resumed = run_issue_list(LIST, profiles, backend=backend, runner=model)
    assert resumed["state"] == "completed" and models == [1, 2]
    replay = run_issue_list(LIST, profiles, backend=backend, runner=model)
    assert replay["state"] == "completed" and replay["issues"] == [LIST + "13"]
    assert models == [1, 2] and len(publications) == 2
    assert len(first.comments) == len(second.comments) == 1
    assert git(root, "branch", "--list") == "* main"
    assert git(root, "status", "--porcelain") == ""


def test_dirty_main_stops_and_preserves_private_diagnostic(repo):
    root, profiles = repo
    backend, _ = backend_for([[issue(12), issue(13)]])
    (root / "value.py").write_text("Other session\n")
    result = run_issue_list(LIST, profiles, backend=backend)
    assert result["state"] == "stopped" and result["stopped_at"] == LIST + "12"
    private = json.loads((root / ".subactor/cache/koru-tickets/queue.json").read_text())
    assert "other work" in private["diagnostic"]["message"]
    assert "diagnostic" not in result
    assert (root / "value.py").read_text() == "Other session\n"
    assert not (root / ".subactor/cache/koru-tickets/issue-13").exists()


def test_pending_list_rejects_profile_change_before_reading_github(repo, monkeypatch):
    import koru.ticket_command.batch as batch

    root, profiles = repo
    backend, _ = backend_for([[issue(12)]])
    monkeypatch.setattr(batch, "run_ticket", lambda *a, **kw: {"state": "blocked"})
    assert run_issue_list(LIST, profiles, backend=backend)["state"] == "stopped"
    profiles.write_text(profiles.read_text() + "\n")
    backend.repo.get_issues = lambda **kw: pytest.fail("pending list was silently replaced")
    with pytest.raises(ValueError, match="reconcile the pending issue list"):
        run_issue_list(LIST, profiles, backend=backend)


def test_disabled_list_does_not_read_github_or_create_working_data(repo, monkeypatch):
    import koru.ticket_command.batch as batch

    root, profiles = repo
    monkeypatch.setenv("KORU_GLOBAL_DISABLE", "1")
    monkeypatch.setattr(batch, "github_backend", lambda *a: pytest.fail("disabled list accessed GitHub"))
    with pytest.raises(ValueError, match="disabled"):
        run_issue_list(LIST, profiles)
    assert not (root / ".subactor").exists()
