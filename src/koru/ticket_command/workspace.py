from __future__ import annotations

import hashlib
import json
import re
import sys
from collections.abc import Callable
from pathlib import Path

from koru.ticket_command.profile import command, git, no_symlinks


class WorkspaceAdmissionRequired(RuntimeError):
    """Allocation is preserved, but it does not authorize implementation."""


def preflight_workspace(profile: dict) -> None:
    root = profile["primary"]
    no_symlinks(root)
    if git(root, "branch", "--show-current") != "main":
        raise ValueError("ticket allocation requires the registered primary on main")
    if git(root, "status", "--porcelain"):
        raise ValueError("main checkout contains other work; preserve it before ticket execution")


def _main_only_workspace(profile: dict) -> tuple[Path, str, str]:
    root = profile["primary"]
    git(root, "fetch", "origin", "main")
    if git(root, "rev-parse", "HEAD") != git(root, "rev-parse", "origin/main"):
        raise ValueError("main is not synchronized with origin/main")
    return root, f"GITHUB-{profile['number']}", git(root, "rev-parse", "HEAD")


def _pinned_checker_args(root: Path, profile: dict) -> list[str]:
    checker = root / ".governance/worktree_path_check.py"
    no_symlinks(checker)
    expected = profile.get("worktree_checker_sha256")
    if not expected or hashlib.sha256(checker.read_bytes()).hexdigest() != expected:
        raise ValueError("adopted worktree checker does not match the local profile pin")
    args = [sys.executable, str(checker)]
    probe = json.loads(command(root, args + ["feature-probe", "--from-worktree", str(root)]))
    if not probe.get("supported"):
        raise ValueError("Git must support worktree add and repair --relative-paths (2.51+)")
    if not isinstance(profile.get("intent"), dict):
        raise ValueError("governed delivery requires a locally accepted intent template")
    paths = profile.get("allowed_paths")
    if not isinstance(paths, list) or not paths or any(not isinstance(p, str) or not p for p in paths):
        raise ValueError("allocation requires explicit accepted paths")
    return args


def _allocate_ticket(root: Path, profile: dict) -> tuple[str, Path]:
    argv = [
        "bash",
        "project/new-ticket.sh",
        "--title",
        f"Resolve GitHub issue {profile['number']}",
        "--agent",
        "koru",
        "--workstream",
        profile["intent"]["workstream"],
        "--kind",
        "BUG",
        "--priority",
        "P1",
        "--origin",
        "requested",
        "--worktree-slug",
        f"github-{profile['number']}",
    ]
    for path in profile["allowed_paths"]:
        argv.extend(["--path", path])
    output = command(root, argv)
    matches = re.findall(r"^Successfully allocated (ticket-[0-9]+) for '[^\n]*' in (.+)\.$", output, re.M)
    if len(matches) != 1:
        raise ValueError("managed allocator did not return one canonical allocation; preserve its reservation")
    ticket, workspace = matches[0]
    return ticket, Path(workspace)


def _planned_layout(root: Path, profile: dict, args: list[str], ticket: str) -> dict:
    layout = json.loads(
        command(
            root,
            args
            + [
                "plan",
                "--repository",
                profile["repository"],
                "--repository-name",
                root.name,
                "--ticket",
                ticket,
                "--slug",
                f"github-{profile['number']}",
                "--from-worktree",
                str(root),
            ],
        )
    )
    checked = json.loads(command(root, args + ["validate", "--check-filesystem", "-"], stdin=json.dumps(layout)))
    if not checked.get("ok"):
        raise ValueError("canonical worktree layout failed validation")
    return layout


def _validate_registration(root: Path, workspace: Path, layout: dict, base: str) -> None:
    no_symlinks(workspace)
    if workspace != Path(layout["worktreePath"]):
        raise ValueError("allocated workspace does not match the canonical layout")
    registrations = git(root, "worktree", "list", "--porcelain").split("\n\n")
    expected = {f"worktree {workspace}", f"HEAD {base}", f"branch refs/heads/{layout['branch']}"}
    if not any(expected.issubset(set(entry.splitlines())) for entry in registrations):
        raise ValueError("allocated workspace is not registered with the expected branch and HEAD")
    pointer_path = workspace / ".git"
    no_symlinks(pointer_path)
    pointer = pointer_path.read_text().strip().removeprefix("gitdir: ")
    if Path(pointer).is_absolute():
        raise ValueError("allocated worktree must use relative Git pointers")
    metadata = (workspace / pointer).resolve()
    common = Path(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    if metadata.parent != common / "worktrees":
        raise ValueError("allocated worktree belongs to another Git common directory")
    no_symlinks(metadata / "gitdir")
    backlink = (metadata / "gitdir").read_text().strip()
    if Path(backlink).is_absolute() or (metadata / backlink).resolve() != pointer_path:
        raise ValueError("allocated worktree must have a matching relative Git backlink")


def _validate_allocation_records(profile: dict, layout: dict, ticket: str, base: str) -> None:
    workspace = Path(layout["worktreePath"])
    intent_path = workspace / "project" / ticket / "intent.json"
    lease_path = Path(layout["leasePath"])
    no_symlinks(intent_path)
    no_symlinks(lease_path)
    intent = json.loads(intent_path.read_text())
    carriers = {f"project/{ticket}/**", "TODO.md", "project/TICKETS.md"}
    expected_paths = set(profile["allowed_paths"]) | carriers
    if (
        intent.get("ticket") != ticket
        or intent.get("workstream") != profile["intent"]["workstream"]
        or set(intent.get("allowedPaths", [])) != expected_paths
    ):
        raise ValueError("allocated intent does not match the accepted ticket scope")
    lease = json.loads(lease_path.read_text())
    bindings = {
        "schema": "wellmanifest.change-lease/v1",
        "ticketId": ticket,
        "worktreeId": workspace.name,
        "branchRef": f"refs/heads/{layout['branch']}",
        "headSha": base,
        "phase": "claimed",
    }
    if any(lease.get(key) != value for key, value in bindings.items()):
        raise ValueError("allocator lease does not bind the allocated workspace")
    # This only validates allocation integrity. It is NOT controller admission.


def prepare_workspace(
    profile: dict,
    *,
    record_allocation: Callable[[dict], None] | None = None,
) -> tuple[Path, str, str]:
    root = profile["primary"]
    preflight_workspace(profile)
    if profile["delivery"] == "main-only":
        return _main_only_workspace(profile)
    args = _pinned_checker_args(root, profile)
    base = git(root, "rev-parse", "HEAD")
    ticket, workspace = _allocate_ticket(root, profile)
    # Persist identity before any dependent validation can fail. The run's
    # already-durable "preparing" state prevents another allocation on restart.
    if record_allocation is not None:
        record_allocation({"ticket": ticket, "workspace": str(workspace), "base": base})
    layout = _planned_layout(root, profile, args, ticket)
    _validate_registration(root, workspace, layout, base)
    _validate_allocation_records(profile, layout, ticket, base)
    raise WorkspaceAdmissionRequired(
        f"{ticket} allocated at {workspace}; protected controller admission is required before editing. "
        "Preserve this allocation and reconcile the run; allocation records are not a write lease."
    )
