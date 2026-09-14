from __future__ import annotations

import json
from pathlib import Path

from koru.ticket_command.profile import command, git, validator_environment


def publish(profile: dict, state: dict, folder: Path) -> dict:
    workspace = Path(state["workspace"])
    head = state["head"]
    if git(workspace, "rev-parse", "HEAD") != head:
        raise ValueError("HEAD changed after verification; publication stopped")
    branch = git(workspace, "branch", "--show-current")
    if profile["delivery"] == "main-only":
        if branch != "main":
            raise ValueError("main-only publication requires main")
        git(workspace, "push", "origin", "main")
        observed = git(workspace, "ls-remote", "origin", "refs/heads/main").split()[0]
        if observed != head:
            raise RuntimeError("remote main no longer matches the tested commit")
        return {"state": "published", "publication": "direct-main", "head": head}

    prefix = state["ticket"].replace("ticket-", "ticket/", 1) + "-"
    if not branch.startswith(prefix):
        raise ValueError("validator delivery requires the allocated ticket branch")
    git(workspace, "push", "origin", branch)
    pulls = json.loads(
        command(
            workspace,
            [
                "gh",
                "pr",
                "list",
                "--repo",
                profile["repository"],
                "--head",
                branch,
                "--state",
                "all",
                "--json",
                "number,headRefOid,state,url",
            ],
        )
    )
    matching = [p for p in pulls if p["headRefOid"] == head and p["state"] in {"OPEN", "MERGED"}]
    if len(matching) > 1:
        raise ValueError("ambiguous pull-request identity")
    if not matching:
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
        matching = json.loads(
            command(
                workspace,
                [
                    "gh",
                    "pr",
                    "list",
                    "--repo",
                    profile["repository"],
                    "--head",
                    branch,
                    "--json",
                    "number,headRefOid,state,url",
                ],
            )
        )
    if len(matching) != 1 or matching[0]["headRefOid"] != head:
        raise ValueError("pull request does not bind the verified head")
    pr = matching[0]
    if pr["state"] != "MERGED":
        adapter = profile["validator"]
        command(
            workspace,
            [
                adapter["launcher"],
                "--repository",
                profile["repository"],
                "--pull-request",
                str(pr["number"]),
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
    observed = json.loads(
        command(
            workspace,
            [
                "gh",
                "pr",
                "view",
                str(pr["number"]),
                "--repo",
                profile["repository"],
                "--json",
                "state,headRefOid,mergeCommit,url",
            ],
        )
    )
    if observed["state"] != "MERGED" or observed["headRefOid"] != head:
        raise RuntimeError("protected validation/merge remains pending; execution will not repeat")
    return {
        "state": "published",
        "publication": "validator",
        "head": head,
        "pull_request": observed["url"],
        "merge_commit": observed["mergeCommit"]["oid"],
    }
