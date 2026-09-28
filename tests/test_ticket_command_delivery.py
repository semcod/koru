import hashlib
import json

import pytest

from koru.ticket_command.profile import validator_environment
from koru.ticket_command.publication import publish


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
