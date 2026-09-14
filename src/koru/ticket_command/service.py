from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path

from koru.ticket_command.execution import propose_and_apply, snapshot, verify
from koru.ticket_command.profile import command, git, load_profile, no_symlinks
from koru.ticket_command.publication import publish
from koru.ticket_command.workspace import preflight_workspace, prepare_workspace


def _effect_guard(profile: dict, profiles: Path) -> None:
    from koru.global_control import is_globally_disabled

    if is_globally_disabled():
        raise ValueError("Koru is globally disabled")
    if load_profile(profile["url"], profiles)["profile_sha256"] != profile["profile_sha256"]:
        raise ValueError("execution profile changed during the run")


def _save(path: Path, state: dict) -> None:
    pending = path.with_suffix(".pending")
    no_symlinks(pending)
    with pending.open("w") as stream:
        json.dump(state, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    pending.replace(path)


def github_backend(profile: dict):
    from planfile.sync.github import GitHubBackend

    credential = os.environ.get("GITHUB_TOKEN")
    if not credential:
        credential = command(profile["primary"], ["gh", "auth", "token"])
    return GitHubBackend(profile["repository"], credential)


def _intake(profile: dict, folder: Path, backend):
    from planfile import Planfile

    issue = backend.repo.get_issue(profile["number"])
    if issue.html_url != profile["url"] or getattr(issue, "pull_request", None):
        raise ValueError("GitHub returned a different target or a pull request")
    if issue.state != "open":
        raise ValueError("issue is not open; a new execution requires an open issue")
    # Dedicated Planfile ledger avoids reserializing a shared repository backlog.
    pf = Planfile(str(folder / "ledger"))
    existing = pf.list_tickets()
    ticket = next((t for t in existing if t.sync.get("github", {}).get("url") == profile["url"]), None)
    if ticket is None:
        ticket = pf.create_ticket(
            name=issue.title,
            description=issue.body or "",
            sync={"github": {"id": str(profile["number"]), "url": profile["url"]}},
        )
    return ticket.id, {"title": issue.title, "body": (issue.body or "")[:50_000]}


def _report(profile: dict, state: dict, folder: Path, backend) -> dict:
    from planfile.core.store import Store
    from planfile.sync.ticket_comments import queue_comment, sync_comment

    store = Store(folder / "ledger")
    body = (
        f"Koru published a verified change for this issue.\n\n"
        f"- Commit: `{state['head']}`\n"
        f"- Delivery: `{state['publication']}`\n"
        f"- Local verification: {len(profile['verify'])} configured checks passed.\n"
    )
    if state.get("pull_request"):
        body += f"- Pull request: {state['pull_request']}\n"
    event = queue_comment(store, state["planfile_ticket"], event_id=state["head"], public_body=body)
    receipt = sync_comment(store, backend, event)
    ticket = store.get_ticket(state["planfile_ticket"])
    if ticket.status != "done":
        outputs = ticket.outputs.model_dump() if ticket.outputs else {}
        outputs["result"] = {"head": state["head"], "publication": state["publication"], "comment": receipt["url"]}
        store.update_ticket(
            ticket.id, status="done", actor="koru", reason="Verified publication and result delivery", outputs=outputs
        )
    return {"state": "reported", "comment": receipt["url"]}


def _report_blocked(state: dict, folder: Path, backend) -> str:
    from planfile.core.store import Store
    from planfile.sync.ticket_comments import queue_comment, sync_comment

    store = Store(folder / "ledger")
    event = queue_comment(
        store,
        state["planfile_ticket"],
        event_id="execution-blocked",
        public_body="Koru stopped this execution before publication. "
        "The proposal or workspace failed a local execution check. "
        "Private diagnostic data is retained locally; automatic execution replay is disabled.",
    )
    return sync_comment(store, backend, event)["url"]


def run_ticket(url: str, profiles: Path, *, dry_run=False, backend=None, runner=None) -> dict:
    profile = load_profile(url, profiles)
    if dry_run:
        return {
            "state": "planned",
            "repository": profile["repository"],
            "delivery": profile["delivery"],
            "primary": str(profile["primary"]),
            "issue": url,
        }
    # This boundary also protects direct module invocation, outside cli.py.
    from koru.global_control import is_globally_disabled

    if is_globally_disabled():
        raise ValueError("Koru is globally disabled")
    folder = profile["primary"] / f".subactor/cache/koru-tickets/issue-{profile['number']}"
    no_symlinks(folder)
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = folder / "state.json"
    no_symlinks(path)
    lock = folder / "run.lock"
    no_symlinks(lock)
    with lock.open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("this issue already has an active Koru execution") from exc
        state = (
            json.loads(path.read_text())
            if path.exists()
            else {"state": "new", "profile_sha256": profile["profile_sha256"]}
        )
        if state["profile_sha256"] != profile["profile_sha256"]:
            raise ValueError("local execution profile changed; reconcile the existing run first")
        if state["state"] == "reported":
            return {k: v for k, v in state.items() if k not in {"issue", "baseline", "applied_snapshot"}}
        if state["state"] == "blocked":
            if not state.get("failure_comment") and state.get("planfile_ticket"):
                _effect_guard(profile, profiles)
                state["failure_comment"] = _report_blocked(state, folder, backend or github_backend(profile))
                _save(path, state)
            return {
                "state": "blocked",
                "message": "execution needs reconciliation; automatic replay is disabled",
                "comment": state.get("failure_comment"),
            }
        if state["state"] in {"preparing", "executing", "committing"}:
            raise RuntimeError("previous execution needs reconciliation; automatic replay is disabled")
        if state["state"] == "new":
            preflight_workspace(profile)
        backend = backend or github_backend(profile)
        if state["state"] == "new":
            # Fail before allocating/executing if native scoped reporting is unavailable.
            try:
                from planfile.sync.ticket_comments import queue_comment  # noqa: F401
            except ImportError as exc:
                raise RuntimeError("install Planfile with native scoped ticket-comment support first") from exc

            planfile_ticket, issue = _intake(profile, folder, backend)
            state.update(state="preparing")
            _save(path, state)
            workspace, ticket, base = prepare_workspace(profile)
            state.update(
                state="prepared",
                workspace=str(workspace),
                ticket=ticket,
                base=base,
                planfile_ticket=planfile_ticket,
                issue=issue,
                baseline=snapshot(workspace),
            )
            _save(path, state)
        workspace = Path(state["workspace"])
        no_symlinks(workspace)
        if state["state"] == "prepared":
            _effect_guard(profile, profiles)
            if snapshot(workspace) != state["baseline"]:
                raise RuntimeError("workspace changed since preparation")
            verify(profile, workspace)
            state["state"] = "executing"
            _save(path, state)
            try:
                paths = propose_and_apply(profile, workspace, state["issue"], runner)
                state.update(state="applied", paths=paths, applied_snapshot=snapshot(workspace))
                _save(path, state)
            except Exception:
                state["state"] = "blocked"
                _save(path, state)
                try:
                    _effect_guard(profile, profiles)
                    state["failure_comment"] = _report_blocked(state, folder, backend)
                    _save(path, state)
                except Exception:
                    pass  # Reporting remains pending; it cannot restart execution.
                raise
        if state["state"] == "applied":
            _effect_guard(profile, profiles)
            if snapshot(workspace) != state["applied_snapshot"]:
                raise RuntimeError("workspace changed after the patch; preserve it for reconciliation")
            verify(profile, workspace)
            if snapshot(workspace) != state["applied_snapshot"]:
                raise RuntimeError("verification modified tracked work; publication stopped")
            state["state"] = "committing"
            _save(path, state)
            paths = list(state["paths"])
            if profile["delivery"] == "validator":
                paths.append(f"project/{state['ticket']}")
            if git(workspace, "diff", "--cached", "--name-only"):
                raise RuntimeError("index contains other work; commit stopped")
            if git(workspace, "rev-parse", "HEAD") != state["base"]:
                raise RuntimeError("HEAD changed during execution; commit stopped")
            git(workspace, "add", "--", *paths)
            if snapshot(workspace) != state["applied_snapshot"]:
                raise RuntimeError("files changed while staging; preserve the index for reconciliation")
            git(workspace, "diff", "--cached", "--check")
            git(workspace, "commit", "-m", f"fix: address GitHub issue {profile['number']} ({state['ticket']})")
            state.update(state="committed", head=git(workspace, "rev-parse", "HEAD"))
            _save(path, state)
        if state["state"] == "committed":
            _effect_guard(profile, profiles)
            state.update(publish(profile, state, folder))
            _save(path, state)
        if state["state"] == "published":
            _effect_guard(profile, profiles)
            state.update(_report(profile, state, folder, backend))
            _save(path, state)
        return {k: v for k, v in state.items() if k not in {"issue", "baseline", "applied_snapshot"}}
