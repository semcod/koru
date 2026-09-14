"""Exercise the native Planfile ledger/outbox with only GitHub transport faked."""

import json
import sys
from types import SimpleNamespace

import pytest

from koru.ticket_command.profile import git
from koru.ticket_command.service import run_ticket

URL = "https://github.com/maskservice/c2004/issues/12"
DIFF = "diff --git a/value.py b/value.py\n--- a/value.py\n+++ b/value.py\n@@ -1 +1 @@\n-value = 1\n+value = 2\n"


@pytest.mark.parametrize("from_environment", [True, False])
def test_github_backend_uses_runtime_credentials_only(tmp_path, monkeypatch, from_environment):
    import planfile.sync.github as github

    import koru.ticket_command.service as service

    calls = []
    credential = "fixture-runtime-credential"
    if from_environment:
        monkeypatch.setenv("GITHUB_TOKEN", credential)
    else:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    def auth(root, argv):
        assert not from_environment
        assert root == tmp_path and argv == ["gh", "auth", "token"]
        return credential

    monkeypatch.setattr(service, "command", auth)
    monkeypatch.setattr(github, "GitHubBackend", lambda *args: calls.append(args) or "backend")
    assert service.github_backend({"primary": tmp_path, "repository": "maskservice/c2004"}) == "backend"
    assert calls == [("maskservice/c2004", credential)]
    assert list(tmp_path.iterdir()) == []


@pytest.fixture
def execution(tmp_path, monkeypatch):
    pytest.importorskip("planfile.sync.ticket_comments")
    import koru.ticket_command.service as service

    root = tmp_path / "repository"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "Test")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "core.hooksPath", str(tmp_path / "empty-hooks"))
    git(root, "remote", "add", "origin", "git@github.com:maskservice/c2004.git")
    (root / ".gitignore").write_text(".subactor/\n")
    (root / "value.py").write_text("value = 1\n")
    git(root, "add", ".")
    git(root, "commit", "-m", "Initial")
    base = git(root, "rev-parse", "HEAD")
    profiles = tmp_path / "profiles.json"
    profiles.write_text(
        json.dumps(
            {
                "schema": "koru.ticket-profiles/v1",
                "repositories": {
                    "maskservice/c2004": {
                        "primary": str(root),
                        "delivery": "main-only",
                        "allowed_paths": ["value.py"],
                        "context_files": ["value.py"],
                        "verify": [[sys.executable, "-c", "compile(open('value.py').read(), 'value.py', 'exec')"]],
                    }
                },
            }
        )
    )
    monkeypatch.setenv("KORU_GLOBAL_CONTROL_DIR", str(tmp_path / "control"))
    monkeypatch.delenv("KORU_GLOBAL_DISABLE", raising=False)
    monkeypatch.setattr(service, "prepare_workspace", lambda _: (root, "GITHUB-12", base))
    publications = []

    def publish(profile, state, folder):
        publications.append(state["head"])
        return {"state": "published", "publication": "direct-main"}

    monkeypatch.setattr(service, "publish", publish)
    issue = SimpleNamespace(
        html_url=URL, title="Repair", body="Private issue content", state="open", pull_request=None, comments=[]
    )
    issue.get_comments = lambda: iter(issue.comments)

    def create_comment(body):
        comment = SimpleNamespace(body=body, html_url=URL + "#issuecomment-1")
        issue.comments.append(comment)
        raise TimeoutError("Simulated lost response after GitHub accepted the comment")

    issue.create_comment = create_comment
    backend = SimpleNamespace(
        config={"repo": "maskservice/c2004"},
        repo=SimpleNamespace(full_name="maskservice/c2004", get_issue=lambda number: issue if number == 12 else None),
    )
    return root, profiles, backend, issue, publications


def test_native_comment_recovers_without_repeating_repair(execution):
    from planfile.core.store import Store

    root, profiles, backend, issue, publications = execution
    models = []

    def model(*_):
        models.append(True)
        return SimpleNamespace(returncode=0, stdout=DIFF)

    with pytest.raises(TimeoutError):
        run_ticket(URL, profiles, backend=backend, runner=model)
    result = run_ticket(URL, profiles, backend=backend, runner=model)
    assert run_ticket(URL, profiles, backend=backend, runner=model) == result
    assert result["state"] == "reported"
    assert len(models) == len(publications) == len(issue.comments) == 1
    assert "Private issue content" not in issue.comments[0].body
    assert issue.state == "open"
    store = Store(root / ".subactor/cache/koru-tickets/issue-12/ledger")
    ticket = store.get_ticket(result["planfile_ticket"])
    assert ticket.status == "done"
    assert ticket.outputs.result["comment"] == result["comment"]


def test_blocked_comment_recovers_without_repeating_rejected_proposal(execution):
    root, profiles, backend, issue, publications = execution
    before = git(root, "rev-parse", "HEAD")
    models = []

    def model(*_):
        models.append(True)
        return SimpleNamespace(returncode=0, stdout=DIFF.replace("value.py", "unapproved.py"))

    with pytest.raises(ValueError, match="scope"):
        run_ticket(URL, profiles, backend=backend, runner=model)
    result = run_ticket(URL, profiles, backend=backend, runner=model)
    assert result["state"] == "blocked" and result["comment"]
    assert len(models) == len(issue.comments) == 1
    assert publications == []
    assert git(root, "rev-parse", "HEAD") == before
    assert not (root / "unapproved.py").exists()


def test_dirty_main_preflight_does_not_poison_future_execution(execution):
    root, profiles, backend, issue, _ = execution
    (root / "value.py").write_text("Other session\n")
    with pytest.raises(ValueError, match="other work"):
        run_ticket(URL, profiles, backend=backend)
    assert not (root / ".subactor/cache/koru-tickets/issue-12/state.json").exists()
    assert issue.comments == []
