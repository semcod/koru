from __future__ import annotations

import json
from pathlib import Path

from koru.ticket_command.profile import command, git, validator_environment


def publish(profile: dict, state: dict, folder: Path) -> dict:
    workspace = Path(state["workspace"])
    head = state["head"]
    _require_verified_head(workspace, head)
    branch = git(workspace, "branch", "--show-current")
    if profile["delivery"] == "main-only":
        return _publish_direct_main(workspace, head, branch)
    return _publish_through_validator(profile, state, folder, workspace, head, branch)


def _require_verified_head(workspace: Path, head: str) -> None:
    if git(workspace, "rev-parse", "HEAD") != head:
        raise ValueError("HEAD changed after verification; publication stopped")


def _publish_direct_main(workspace: Path, head: str, branch: str) -> dict:
    if branch != "main":
        raise ValueError("main-only publication requires main")
    git(workspace, "push", "origin", "main")
    observed = git(workspace, "ls-remote", "origin", "refs/heads/main").split()[0]
    if observed != head:
        raise RuntimeError("remote main no longer matches the tested commit")
    return {"state": "published", "publication": "direct-main", "head": head}


def _publish_through_validator(
    profile: dict, state: dict, folder: Path, workspace: Path, head: str, branch: str
) -> dict:
    prefix = state["ticket"].replace("ticket-", "ticket/", 1) + "-"
    if not branch.startswith(prefix):
        raise ValueError("validator delivery requires the allocated ticket branch")
    git(workspace, "push", "origin", branch)
    matching = [
        p
        for p in _listed_pulls(workspace, profile["repository"], branch)
        if p["headRefOid"] == head and p["state"] in {"OPEN", "MERGED"}
    ]
    if len(matching) > 1:
        raise ValueError("ambiguous pull-request identity")
    if not matching:
        _create_pull_request(profile, state, folder, workspace, branch)
        matching = _listed_pulls(workspace, profile["repository"], branch)
    if len(matching) != 1 or matching[0]["headRefOid"] != head:
        raise ValueError("pull request does not bind the verified head")
    pull = matching[0]
    if pull["state"] != "MERGED":
        _merge_through_validator(profile, state, folder, workspace, pull, head)
    observed = _observed_pull(workspace, profile["repository"], pull["number"])
    if observed["state"] != "MERGED" or observed["headRefOid"] != head:
        raise RuntimeError("protected validation/merge remains pending; execution will not repeat")
    return {
        "state": "published",
        "publication": "validator",
        "head": head,
        "pull_request": observed["url"],
        "merge_commit": observed["mergeCommit"]["oid"],
    }


def _listed_pulls(workspace: Path, repository: str, branch: str) -> list[dict]:
    return json.loads(
        command(
            workspace,
            [
                "gh",
                "pr",
                "list",
                "--repo",
                repository,
                "--head",
                branch,
                "--state",
                "all",
                "--json",
                "number,headRefOid,state,url",
            ],
        )
    )


def _create_pull_request(profile: dict, state: dict, folder: Path, workspace: Path, branch: str) -> None:
    body = folder / "pull-request.md"
    body.write_text(
        f"Resolve {profile['url']} under {state['ticket']}.\n\nLocal verification passed. "
        "Independent OneDev/Validator checks are required before merge.\n"
    )
    command(
        workspace,
        [
            "gh",
            "pr",
            "create",
            "--repo",
            profile["repository"],
            "--base",
            "main",
            "--head",
            branch,
            "--title",
            f"fix: resolve issue {profile['number']}",
            "--body-file",
            str(body),
        ],
    )


def _merge_through_validator(profile: dict, state: dict, folder: Path, workspace: Path, pull: dict, head: str) -> None:
    adapter = profile["validator"]
    command(
        workspace,
        [
            adapter["launcher"],
            "--repository",
            profile["repository"],
            "--pull-request",
            str(pull["number"]),
            "--ticket",
            state["ticket"],
            "--expected-head-sha",
            head,
            "--key-file",
            adapter["key_file"],
            "--output-dir",
            str(folder / "validator"),
            "--merge",
        ],
        env=validator_environment(adapter, profile["primary"]),
    )


def _observed_pull(workspace: Path, repository: str, number: int) -> dict:
    return json.loads(
        command(
            workspace,
            [
                "gh",
                "pr",
                "view",
                str(number),
                "--repo",
                repository,
                "--json",
                "state,headRefOid,mergeCommit,url",
            ],
        )
    )
