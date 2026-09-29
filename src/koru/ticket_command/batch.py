"""Finite, sequential GitHub issue delivery using the scoped single-issue runner."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from contextlib import nullcontext
from pathlib import Path

from koru.ticket_command.profile import load_profile, no_symlinks, parse_issue
from koru.ticket_command.service import _effect_guard, _save, execution_lock, github_backend, run_ticket
from koru.ticket_command.workspace import preflight_workspace

SCHEMA = "koru.issue-list-run/v1"


def _snapshot(profile: dict, backend) -> list[str]:
    targets = {}
    # PyGithub's PaginatedList follows every page; GitHub includes PRs here.
    try:
        for issue in backend.repo.get_issues(state="open", sort="created", direction="asc"):
            if getattr(issue, "pull_request", None) or issue.state != "open":
                continue
            repository, number = parse_issue(issue.html_url)
            if repository != profile["repository"] or number != issue.number:
                raise ValueError("unexpected issue identity")
            targets[number] = issue.html_url
    except Exception as exc:
        raise RuntimeError("GitHub issue list could not be read; no tickets were started") from exc
    return [targets[number] for number in sorted(targets)]


def _targets(profile: dict, backend, path: Path) -> list[str]:
    if path.exists():
        previous = json.loads(path.read_text())
        if previous.get("schema") != SCHEMA:
            raise ValueError("issue-list receipt needs reconciliation")
        if previous["state"] != "completed":
            if previous["profile_sha256"] != profile["profile_sha256"]:
                raise ValueError("execution profile changed; reconcile the pending issue list first")
            targets = previous["issues"]
            if not isinstance(targets, list) or any(parse_issue(url)[0] != profile["repository"] for url in targets):
                raise ValueError("issue-list receipt has an invalid repository target")
            return targets
    return _snapshot(profile, backend)


def _sync_configured(profile: dict) -> bool:
    primary = profile.get("primary")
    if not primary:
        return False
    planfile_dir = Path(primary) / ".planfile"
    return planfile_dir.is_dir() and (
        (planfile_dir / "github.planfile.yaml").exists()
        or (planfile_dir / "integrations.planfile.yaml").exists()
    )


def _bound_ticket_ids(profile: dict, targets: list[str]) -> list[str]:
    """Primary-backlog ticket ids bound to the selected GitHub issue URLs."""
    urls = set(targets)
    try:
        from planfile import Planfile

        pf = Planfile.auto_discover(Path(profile["primary"]))
        return [
            str(ticket.id)
            for ticket in pf.list_tickets()
            if ((getattr(ticket, "sync", None) or {}).get("github") or {}).get("url") in urls
        ]
    except Exception as exc:
        raise RuntimeError(
            "local Planfile bindings for the selected issues could not be read"
        ) from exc


def _sync_primary_planfile(profile: dict, ticket_ids: list[str]) -> None:
    """Synchronize only the backlog tickets bound to the selected issues.

    A configured but failed sync is a required-stage failure; callers must
    surface it in the durable run result instead of reporting success.
    """
    primary = profile.get("primary")
    if not primary or not ticket_ids or not _sync_configured(profile):
        return
    py = os.environ.get("PY") or sys.executable
    command = [py, "-m", "planfile.cli", "sync", "github", "--direction", "both"]
    for ticket_id in ticket_ids:
        command += ["--ticket", ticket_id]
    try:
        proc = subprocess.run(command, cwd=primary, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("planfile sync github timed out after 60s") from exc
    except OSError as exc:
        raise RuntimeError(f"planfile sync github could not start: {exc}") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[:2000]
        raise RuntimeError(f"planfile sync github exited {proc.returncode}: {detail}")


def run_issue_list(url: str, profiles: Path, *, dry_run=False, backend=None, runner=None) -> dict:
    profile = load_profile(url, profiles)
    if profile["number"] is not None:
        raise ValueError("expected an exact GitHub issues-list URL")
    _effect_guard(profile, profiles)
    path = profile["primary"] / ".subactor/cache/koru-tickets/queue.json"
    no_symlinks(path)
    lock = nullcontext() if dry_run else execution_lock(profile, "queue.lock")
    with lock:
        backend = backend or github_backend(profile)
        targets = _targets(profile, backend, path)
        _effect_guard(profile, profiles)
        result = {
            "state": "planned" if dry_run else "completed",
            "repository": profile["repository"],
            "delivery": profile["delivery"],
            "primary": str(profile["primary"]),
            "issues": targets,
            "results": [],
        }
        if dry_run:
            return result
        persisted = {"schema": SCHEMA, "profile_sha256": profile["profile_sha256"]}
        sync_ticket_ids: list[str] = []
        if targets and _sync_configured(profile):
            try:
                # A refused workspace is reported durably by the per-issue
                # runner; the backlog sync must not mutate anything first.
                preflight_workspace(profile)
            except (ValueError, RuntimeError):
                pass
            else:
                try:
                    sync_ticket_ids = _bound_ticket_ids(profile, targets)
                    _sync_primary_planfile(profile, sync_ticket_ids)
                except RuntimeError as exc:
                    result.update(
                        state="stopped",
                        message="Required planfile sync failed before issue execution",
                    )
                    persisted["diagnostic"] = {
                        "type": type(exc).__name__,
                        "message": str(exc)[:4000],
                    }
                    _save(path, {**persisted, **result})
                    return result
        # Persist the selection before any ticket effect. A restart must not
        # forget an unfinished ticket just because GitHub closed it meanwhile.
        _save(path, {**persisted, **result, "state": "running"})
        for target in targets:
            try:
                _effect_guard(profile, profiles)
                _, number = parse_issue(target)
                issue = backend.repo.get_issue(number)
                if issue.html_url != target or getattr(issue, "pull_request", None):
                    raise ValueError("GitHub returned a different target or a pull request")
                state_path = profile["primary"] / f".subactor/cache/koru-tickets/issue-{number}/state.json"
                no_symlinks(state_path)
                # A closed new issue is no longer eligible. Existing receipts must
                # still finish publication/reporting, even if GitHub closed it.
                if issue.state == "closed" and not state_path.exists():
                    result["results"].append({"issue": target, "state": "closed"})
                    continue
                receipt = run_ticket(
                    target,
                    profiles,
                    backend=backend,
                    runner=runner,
                    expected_profile_sha256=profile["profile_sha256"],
                )
                item = {"issue": target, "state": receipt["state"]}
                for key in ("head", "comment", "pull_request"):
                    if receipt.get(key):
                        item[key] = receipt[key]
                result["results"].append(item)
                if receipt["state"] != "reported":
                    result.update(state="stopped", stopped_at=target)
                    break
            except Exception as exc:
                # Remote exceptions can contain credentials or private issue text.
                # The single-issue runner owns durable, resumable execution state.
                result["results"].append({"issue": target, "state": "stopped"})
                result.update(
                    state="stopped",
                    stopped_at=target,
                    message="Ticket execution stopped; inspect its local execution state before resuming.",
                )
                persisted["diagnostic"] = {"type": type(exc).__name__, "message": str(exc)[:4000]}
                break
        # A stopped run (including a preflight refusal) must not touch the
        # local or remote backlog again.
        if result["state"] == "completed" and sync_ticket_ids:
            try:
                _sync_primary_planfile(profile, sync_ticket_ids)
            except RuntimeError as exc:
                result.update(
                    state="stopped",
                    message="Required planfile sync failed after issue reporting",
                )
                persisted["diagnostic"] = {
                    "type": type(exc).__name__,
                    "message": str(exc)[:4000],
                }
        _save(path, {**persisted, **result})
        return result
