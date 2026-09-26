from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

from koru.ticket_command.profile import command, git, no_symlinks


def preflight_workspace(profile: dict) -> None:
    root = profile["primary"]
    if profile["delivery"] == "main-only":
        if git(root, "branch", "--show-current") != "main":
            raise ValueError("main-only execution requires the main checkout")
        if git(root, "status", "--porcelain"):
            raise ValueError("main checkout contains other work; preserve it before ticket execution")


def _main_only_workspace(profile: dict) -> tuple[Path, str, str]:
    root = profile["primary"]
    git(root, "fetch", "origin", "main")
    if git(root, "rev-parse", "HEAD") != git(root, "rev-parse", "origin/main"):
        raise ValueError("main is not synchronized with origin/main")
    return root, f"GITHUB-{profile['number']}", git(root, "rev-parse", "HEAD")


def _pinned_checker_args(root: Path, profile: dict) -> list[str]:
    """Validate governed-delivery preconditions; return the checker argv prefix."""
    checker = root / ".governance/worktree_path_check.py"
    expected = profile.get("worktree_checker_sha256")
    if not expected or hashlib.sha256(checker.read_bytes()).hexdigest() != expected:
        raise ValueError("adopted worktree checker does not match the local profile pin")
    args = [sys.executable, str(checker)]
    probe = json.loads(command(root, args + ["feature-probe", "--from-worktree", str(root)]))
    if not probe.get("supported"):
        raise ValueError("Git must support worktree add and repair --relative-paths (2.51+)")
    if not isinstance(profile.get("intent"), dict):
        raise ValueError("governed delivery requires a locally accepted intent template")
    return args


def _allocate_ticket(root: Path, profile: dict) -> str:
    # The managed allocator serializes IDs before any branch is created.
    output = command(
        root,
        [
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
        ],
    )
    match = re.search(r"scaffolded project/(ticket-[0-9]+)", output)
    if not match:
        raise ValueError("managed allocator did not return a ticket identity; inspect its reservation")
    return match[1]


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
    checked = json.loads(
        command(root, args + ["validate", "--check-filesystem", "-"], stdin=json.dumps(layout))
    )
    if not checked.get("ok"):
        raise ValueError("canonical worktree layout failed validation")
    return layout


def _write_lease(layout: dict) -> None:
    lease = Path(layout["leasePath"])
    no_symlinks(lease)
    lease.parent.mkdir(parents=True, exist_ok=True)
    with lease.open("x") as stream:
        stream.write(json.dumps(layout))


def _materialize_worktree(root: Path, layout: dict, ticket: str, base: str) -> Path:
    workspace = Path(layout["worktreePath"])
    git(root, "worktree", "add", "--relative-paths", "-b", layout["branch"], str(workspace), base)
    shutil.move(root / "project" / ticket, workspace / "project" / ticket)
    return workspace


def _seed_ticket_records(profile: dict, workspace: Path, ticket: str, base: str) -> None:
    intent = json.loads(json.dumps(profile["intent"]))
    intent.update(
        ticket=ticket,
        summary=f"Resolve {profile['url']}",
        allowedPaths=[*profile["allowed_paths"], f"project/{ticket}/**"],
    )
    if "delivery" in intent:
        intent["delivery"]["acceptedBaseSha"] = base
    (workspace / "project" / ticket / "intent.json").write_text(json.dumps(intent, indent=2) + "\n")
    (workspace / "project" / ticket / "README.md").write_text(
        f"# {ticket}: GitHub issue {profile['number']}\n\n- **ID**: {ticket}\n- **Owner**: koru\n"
        "- **Status**: IN_PROGRESS\n- **Workflow state**: EDIT\n\n"
        f"SESSION_EXECUTION_AUTHORIZATION: explicit `koru ticket {profile['url']}` invocation.\n\n"
        "Acceptance criteria and verification are bound by the locally accepted intent.\n"
    )
    command(workspace, ["bash", "scripts/install-agent-hosts.sh"])


def prepare_workspace(profile: dict) -> tuple[Path, str, str]:
    root = profile["primary"]
    preflight_workspace(profile)
    if profile["delivery"] == "main-only":
        return _main_only_workspace(profile)
    args = _pinned_checker_args(root, profile)
    git(root, "fetch", "origin", "main")
    base = git(root, "rev-parse", "origin/main")
    ticket = _allocate_ticket(root, profile)
    layout = _planned_layout(root, profile, args, ticket)
    _write_lease(layout)
    workspace = _materialize_worktree(root, layout, ticket, base)
    _seed_ticket_records(profile, workspace, ticket, base)
    return workspace, ticket, base
