import hashlib
import json
from pathlib import Path

import pytest

from koru.ticket_command.profile import git, validator_environment
from koru.ticket_command.publication import publish
from koru.ticket_command.workspace import prepare_workspace


def test_validator_environment_is_pinned_and_never_shell_evaluated(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    env = tmp_path / "protected.env"
    marker = tmp_path / "must-not-exist"
    env.write_text(f'VALIDATOR_PYTHON="/protected/python"\nLITERAL="$(touch {marker})"\n')
    adapter = {"environment_file": str(env), "environment_sha256": hashlib.sha256(env.read_bytes()).hexdigest()}
    values = validator_environment(adapter, root)
    assert values["VALIDATOR_PYTHON"] == "/protected/python"
    assert values["LITERAL"] == f"$(touch {marker})"
    assert not marker.exists()
    env.write_text("VALIDATOR_PYTHON=/different/python\n")
    with pytest.raises(ValueError, match="operator pin"):
        validator_environment(adapter, root)


def test_repository_cannot_supply_validator_environment(tmp_path):
    env = tmp_path / "validator.env"
    env.write_text("VALIDATOR_ROOT=/repository\n")
    with pytest.raises(ValueError, match="outside the repository"):
        validator_environment({"environment_file": str(env)}, tmp_path)


def test_main_publication_never_calls_pr_or_validator(tmp_path, monkeypatch):
    import koru.ticket_command.publication as module

    calls = []
    head = "a" * 40

    def fake_git(root, *args):
        calls.append(args)
        return {
            ("rev-parse", "HEAD"): head,
            ("branch", "--show-current"): "main",
            ("ls-remote", "origin", "refs/heads/main"): head + "\trefs/heads/main",
        }.get(args, "")

    monkeypatch.setattr(module, "git", fake_git)
    monkeypatch.setattr(module, "command", lambda *_: pytest.fail("main-only called a PR command"))
    result = publish({"delivery": "main-only"}, {"workspace": str(tmp_path), "head": head}, tmp_path)
    assert result["publication"] == "direct-main"
    assert calls == [
        ("rev-parse", "HEAD"),
        ("branch", "--show-current"),
        ("push", "origin", "main"),
        ("ls-remote", "origin", "refs/heads/main"),
    ]


def test_push_rejection_never_tries_another_route(tmp_path, monkeypatch):
    import koru.ticket_command.publication as module

    def fake_git(root, *args):
        if args[0] == "push":
            raise RuntimeError("protected main refused")
        return "main" if args[0] == "branch" else "a" * 40

    monkeypatch.setattr(module, "git", fake_git)
    monkeypatch.setattr(module, "command", lambda *_: pytest.fail("attempted an alternative publication route"))
    with pytest.raises(RuntimeError, match="refused"):
        publish({"delivery": "main-only"}, {"workspace": str(tmp_path), "head": "a" * 40}, tmp_path)


def test_validator_receives_exact_bindings_and_merge_must_be_observed(tmp_path, monkeypatch):
    import koru.ticket_command.publication as module

    head = "a" * 40
    calls = []
    monkeypatch.setattr(module, "git", lambda root, *args: "ticket/001-fix" if args[0] == "branch" else head)

    def run(root, args, **kwargs):
        calls.append(args)
        if args[:3] == ["gh", "pr", "list"]:
            return json.dumps(
                [{"number": 4, "headRefOid": head, "state": "OPEN", "url": "https://github.com/a/b/pull/4"}]
            )
        if args[:3] == ["gh", "pr", "view"]:
            return json.dumps({"state": "OPEN", "headRefOid": head})
        return ""

    monkeypatch.setattr(module, "command", run)
    profile = {
        "delivery": "validator",
        "primary": tmp_path,
        "repository": "a/b",
        "validator": {"launcher": "/protected/run-local-direct-pr.sh", "key_file": "/protected/key-reference"},
    }
    with pytest.raises(RuntimeError, match="remains pending"):
        publish(profile, {"workspace": str(tmp_path), "head": head, "ticket": "ticket-001"}, tmp_path)
    assert calls[1] == [
        "/protected/run-local-direct-pr.sh",
        "--repository",
        "a/b",
        "--pull-request",
        "4",
        "--ticket",
        "ticket-001",
        "--expected-head-sha",
        head,
        "--key-file",
        "/protected/key-reference",
        "--output-dir",
        str(tmp_path / "validator"),
        "--merge",
    ]


def test_missing_pull_request_is_created_then_bound(tmp_path, monkeypatch):
    import koru.ticket_command.publication as module

    head = "b" * 40
    calls = []
    listings = []
    monkeypatch.setattr(module, "git", lambda root, *args: "ticket/002-cc" if args[0] == "branch" else head)

    def run(root, args, **kwargs):
        calls.append(args)
        if args[:3] == ["gh", "pr", "list"]:
            listings.append(args)
            if len(listings) > 1:
                return json.dumps(
                    [{"number": 7, "headRefOid": head, "state": "MERGED", "url": "https://github.com/a/b/pull/7"}]
                )
            return json.dumps([])
        if args[:3] == ["gh", "pr", "create"]:
            return "https://github.com/a/b/pull/7\n"
        if args[:3] == ["gh", "pr", "view"]:
            return json.dumps(
                {
                    "state": "MERGED",
                    "headRefOid": head,
                    "url": "https://github.com/a/b/pull/7",
                    "mergeCommit": {"oid": "c" * 40},
                }
            )
        return ""

    monkeypatch.setattr(module, "command", run)
    profile = {
        "delivery": "validator",
        "primary": tmp_path,
        "repository": "a/b",
        "number": 5,
        "url": "https://github.com/a/b/issues/5",
    }
    result = publish(profile, {"workspace": str(tmp_path), "head": head, "ticket": "ticket-002"}, tmp_path)
    assert result == {
        "state": "published",
        "publication": "validator",
        "head": head,
        "pull_request": "https://github.com/a/b/pull/7",
        "merge_commit": "c" * 40,
    }
    assert calls[1] == [
        "gh",
        "pr",
        "create",
        "--repo",
        "a/b",
        "--base",
        "main",
        "--head",
        "ticket/002-cc",
        "--title",
        "fix: resolve issue 5",
        "--body-file",
        str(tmp_path / "pull-request.md"),
    ]
    assert listings[0] == listings[1]
    assert (tmp_path / "pull-request.md").read_text() == (
        "Resolve https://github.com/a/b/issues/5 under ticket-002.\n\n"
        "Local verification passed. Independent OneDev/Validator checks are required before merge.\n"
    )


def test_created_pull_request_binding_uses_the_raw_listing(tmp_path, monkeypatch):
    import koru.ticket_command.publication as module

    head = "b" * 40
    other = "d" * 40
    listings = 0
    monkeypatch.setattr(module, "git", lambda root, *args: "ticket/002-cc" if args[0] == "branch" else head)

    def run(root, args, **kwargs):
        nonlocal listings
        if args[:3] == ["gh", "pr", "list"]:
            listings += 1
            if listings > 1:
                return json.dumps(
                    [
                        {"number": 7, "headRefOid": head, "state": "OPEN", "url": "https://github.com/a/b/pull/7"},
                        {"number": 3, "headRefOid": other, "state": "CLOSED", "url": "https://github.com/a/b/pull/3"},
                    ]
                )
            return json.dumps([])
        return ""

    monkeypatch.setattr(module, "command", run)
    profile = {
        "delivery": "validator",
        "primary": tmp_path,
        "repository": "a/b",
        "number": 5,
        "url": "https://github.com/a/b/issues/5",
    }
    with pytest.raises(ValueError, match="does not bind the verified head"):
        publish(profile, {"workspace": str(tmp_path), "head": head, "ticket": "ticket-002"}, tmp_path)


def test_canonical_worktree_uses_real_git_relative_pointers(tmp_path, monkeypatch):
    import koru.ticket_command.workspace as module

    root = tmp_path / "project"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "Test")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "core.hooksPath", str(tmp_path / "empty-hooks"))
    (root / "project").mkdir()
    (root / "scripts").mkdir()
    (root / ".governance").mkdir()
    (root / ".gitignore").write_text(".worktrees/\n.subactor/\n")
    checker = root / ".governance/worktree_path_check.py"
    checker.write_text("# fixture pinned checker")
    (root / "scripts/install-agent-hosts.sh").write_text("exit 0\n")
    git(root, "add", ".")
    git(root, "commit", "-m", "initial")
    base = git(root, "rev-parse", "HEAD")
    git(root, "update-ref", "refs/remotes/origin/main", base)
    actual_command = module.command
    actual_git = module.git

    def run(where, args, **kwargs):
        if "feature-probe" in args:
            return '{"supported":true}'
        if "project/new-ticket.sh" in args:
            ticket = root / "project/ticket-001"
            ticket.mkdir()
            (ticket / "README.md").write_text("Managed allocation")
            return "Successfully scaffolded project/ticket-001"
        if "plan" in args:
            return json.dumps(
                {
                    "branch": "ticket/001-github-12",
                    "leasePath": str(root / ".subactor/leases/ticket-001--github-12.json"),
                    "worktreePath": str(root / ".worktrees/ticket-001--github-12"),
                }
            )
        if "validate" in args:
            return '{"ok":true}'
        return actual_command(where, args, **kwargs)

    monkeypatch.setattr(module, "command", run)
    monkeypatch.setattr(module, "git", lambda where, *args: "" if args[0] == "fetch" else actual_git(where, *args))
    profile = {
        "primary": root,
        "delivery": "validator",
        "repository": "a/b",
        "number": 12,
        "url": "https://github.com/a/b/issues/12",
        "allowed_paths": ["src/**"],
        "worktree_checker_sha256": hashlib.sha256(checker.read_bytes()).hexdigest(),
        "intent": {"workstream": "application"},
    }
    workspace, ticket, observed_base = prepare_workspace(profile)
    assert workspace == root / ".worktrees/ticket-001--github-12"
    assert ticket == "ticket-001" and observed_base == base
    assert not (root / "project/ticket-001").exists()
    assert (root / ".subactor/leases/ticket-001--github-12.json").exists()
    pointer = (workspace / ".git").read_text().strip().removeprefix("gitdir: ")
    assert not Path(pointer).is_absolute()
    backlink = (workspace / pointer / "gitdir").read_text().strip()
    assert not Path(backlink).is_absolute()
