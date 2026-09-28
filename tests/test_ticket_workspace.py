"""The allocator, checker and Git below are real adopted implementations."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from koru.ticket_command import service
from koru.ticket_command import workspace as module
from koru.ticket_command.profile import git


@pytest.fixture
def governed_profile(tmp_path):
    source = Path(__file__).resolve().parents[1]
    root = tmp_path / "repository with spaces"
    root.mkdir()
    shutil.copytree(source / ".governance", root / ".governance")
    (root / "project").mkdir()
    for name in ("new-ticket.sh", "readme.sh"):
        shutil.copy2(source / "project" / name, root / "project" / name)
    for name in ("README.md", "TODO.md"):
        (root / name).write_text("# Isolated allocator fixture\n")
    (root / "project/TICKETS.md").write_text(
        "# Tickets\n<!-- AUTO:TICKET_INDEX:START -->\n<!-- AUTO:TICKET_INDEX:END -->\n"
    )
    (root / ".gitignore").write_text("/.worktrees/\n/.subactor/leases/\n/.subactor/cache/\n")
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "Workspace regression")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "core.hooksPath", str(tmp_path / "empty-hooks"))
    git(root, "add", "--", ".")
    git(root, "commit", "-m", "fixture: adopt local allocator and checker")
    return {
        "primary": root,
        "delivery": "validator",
        "repository": "example/fixture",
        "number": 12,
        "url": "https://github.com/example/fixture/issues/12",
        "allowed_paths": ["src/example.py"],
        "worktree_checker_sha256": hashlib.sha256(
            (root / ".governance/worktree_path_check.py").read_bytes()
        ).hexdigest(),
        "intent": {"workstream": "application"},
    }


def test_real_allocator_is_consumed_once_without_granting_edit_authority(governed_profile, monkeypatch):
    profile = governed_profile
    root = profile["primary"]
    calls, allocations, originals = [], [], {}
    run = module.command

    def observe(where, argv, **kwargs):
        calls.append(argv)
        output = run(where, argv, **kwargs)
        if "project/new-ticket.sh" in argv:
            for path in [*root.glob(".subactor/leases/*.json"), *root.glob(".worktrees/*/project/ticket-*/*")]:
                if path.is_file():
                    originals[path] = path.read_bytes()
        return output

    monkeypatch.setattr(module, "command", observe)
    with pytest.raises(module.WorkspaceAdmissionRequired, match="protected controller admission"):
        module.prepare_workspace(profile, record_allocation=allocations.append)
    assert len(allocations) == 1
    allocation = allocations[0]
    assert allocation["ticket"] == "ticket-001"
    assert Path(allocation["workspace"]) == root / ".worktrees/ticket-001--github-12"
    assert allocation["base"] == git(root, "rev-parse", "HEAD")
    assert len(git(root, "worktree", "list", "--porcelain").split("\n\n")) == 2
    assert not git(root, "status", "--porcelain")
    assert sum("project/new-ticket.sh" in argv for argv in calls) == 1
    assert not any("fetch" in argv or "--refresh-remote" in argv for argv in calls)
    assert not (root / "project/ticket-001").exists()
    assert originals and all(path.read_bytes() == data for path, data in originals.items())


def test_dirty_primary_stops_before_allocation(governed_profile):
    root = governed_profile["primary"]
    (root / "README.md").write_text("Existing owner work\n")
    with pytest.raises(ValueError, match="contains other work"):
        module.prepare_workspace(governed_profile)
    assert not (root / ".worktrees").exists()
    assert (root / "README.md").read_text() == "Existing owner work\n"


@pytest.mark.parametrize("failure", ["absolute-link", "wrong-branch", "wrong-scope", "layout-lease", "symlink"])
def test_invalid_allocated_workspace_is_preserved_for_reconciliation(governed_profile, monkeypatch, failure):
    allocate = module._allocate_ticket
    captured = []

    def altered(root, profile):
        ticket, path = allocate(root, profile)
        lease = root / ".subactor/leases" / f"{path.name}.json"
        if failure == "absolute-link":
            pointer = (path / ".git").read_text().strip().removeprefix("gitdir: ")
            (path / ".git").write_text(f"gitdir: {(path / pointer).resolve()}\n")
        elif failure == "wrong-branch":
            git(path, "checkout", "-b", "unexpected")
        elif failure == "wrong-scope":
            intent = path / "project" / ticket / "intent.json"
            data = json.loads(intent.read_text())
            data["allowedPaths"].append("src/other.py")
            intent.write_text(json.dumps(data))
        elif failure == "layout-lease":
            lease.write_text('{"kind":"layout-record"}')
        else:
            original = lease.with_suffix(".original")
            lease.rename(original)
            lease.symlink_to(original)
        return ticket, path

    monkeypatch.setattr(module, "_allocate_ticket", altered)
    with pytest.raises((ValueError, RuntimeError)) as exc:
        module.prepare_workspace(governed_profile, record_allocation=captured.append)
    assert not isinstance(exc.value, module.WorkspaceAdmissionRequired)
    assert len(captured) == 1
    assert Path(captured[0]["workspace"]).is_dir()
    assert len(list(governed_profile["primary"].glob(".worktrees/*"))) == 1


def test_preparation_journal_keeps_identity_and_disables_automatic_reallocation(
    governed_profile, tmp_path, monkeypatch
):
    profile = {**governed_profile, "profile_sha256": "accepted"}
    folder = tmp_path / "run"
    folder.mkdir()
    path = folder / "state.json"
    state = {"state": "new", "profile_sha256": "accepted"}
    monkeypatch.setattr(service, "_intake", lambda *args: ("PLF-001", {"title": "fixture"}))
    with pytest.raises(module.WorkspaceAdmissionRequired):
        service._prepare_ticket_state(profile, state, path, folder, None)
    saved = json.loads(path.read_text())
    assert saved["state"] == "preparing"
    assert saved["planfile_ticket"] == "PLF-001"
    assert saved["allocation"]["ticket"] == "ticket-001"
    assert saved["preparation_blocker"] == "controller_admission_required"
    with pytest.raises(RuntimeError, match="automatic replay is disabled"):
        service._check_prior_state(saved, profile, tmp_path / "profiles.json", folder, path, None)
    assert len(list(profile["primary"].glob(".worktrees/*"))) == 1


def test_legacy_scaffold_output_never_creates_another_worktree(tmp_path, monkeypatch):
    calls = []

    def old_allocator(root, argv):
        calls.append(argv)
        return "Successfully scaffolded project/ticket-001"

    monkeypatch.setattr(module, "command", old_allocator)
    with pytest.raises(ValueError, match="preserve its reservation"):
        module._allocate_ticket(
            tmp_path, {"number": 1, "intent": {"workstream": "application"}, "allowed_paths": ["src/a.py"]}
        )
    assert len(calls) == 1


@pytest.mark.parametrize("phase", ["prepared", "applied", "committed"])
def test_legacy_run_cannot_resume_without_controller_admission(tmp_path, phase):
    with pytest.raises(module.WorkspaceAdmissionRequired, match="protected controller admission"):
        service._check_prior_state(
            {"state": phase, "profile_sha256": "same"},
            {"delivery": "validator", "profile_sha256": "same"},
            tmp_path / "profile",
            tmp_path,
            tmp_path / "state",
            None,
        )
