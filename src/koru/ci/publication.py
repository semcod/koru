"""Publication via subactor/validator-agent (freeze → dispatch → optional merge)."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import yaml

from koru.ci.github import (
    GitHubCliError,
    current_branch,
    find_open_pr_for_branch,
    gh_available,
    resolve_github_repo,
    resolve_pr_head_sha,
)
from koru.utils.subprocess_runner import resolve_planfile_subpath

DEFAULT_VALIDATOR_REPO = "subactor/validator-agent"
DEFAULT_VALIDATOR_SCRIPT = "bin/dispatch-direct-pr.sh"


@dataclass(frozen=True)
class PublicationConfig:
    validator_checkout: Path | None
    validator_repo: str
    validator_ref: str
    merge: bool
    wait_checks: bool
    watch: bool
    update_branch: bool

    @classmethod
    def from_mapping(cls, raw: dict[str, Any] | None) -> PublicationConfig:
        data = raw if isinstance(raw, dict) else {}
        checkout_raw = data.get("validator_checkout") or os.environ.get("KORU_VALIDATOR_CHECKOUT")
        checkout = Path(str(checkout_raw)).expanduser().resolve() if checkout_raw else None
        return cls(
            validator_checkout=checkout,
            validator_repo=str(data.get("validator_repo") or DEFAULT_VALIDATOR_REPO),
            validator_ref=str(data.get("validator_ref") or "main"),
            merge=bool(data.get("merge", False)),
            wait_checks=bool(data.get("wait_checks", True)),
            watch=bool(data.get("watch", False)),
            update_branch=bool(data.get("update_branch", False)),
        )


def publication_config_path(project: Path) -> Path:
    return resolve_planfile_subpath(project, ".koru", "ci-publication.yaml")


def load_publication_config(project: Path) -> PublicationConfig:
    path = publication_config_path(project)
    if not path.is_file():
        env_checkout = os.environ.get("KORU_VALIDATOR_CHECKOUT")
        default_checkout = Path(env_checkout).expanduser().resolve() if env_checkout else None
        return PublicationConfig(
            validator_checkout=default_checkout,
            validator_repo=DEFAULT_VALIDATOR_REPO,
            validator_ref="main",
            merge=False,
            wait_checks=True,
            watch=False,
            update_branch=False,
        )
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return PublicationConfig.from_mapping({})
    return PublicationConfig.from_mapping(raw.get("publication"))


def _resolve_validator_script(config: PublicationConfig) -> Path:
    if config.validator_checkout is None:
        raise GitHubCliError(
            "validator checkout not configured; set publication.validator_checkout in "
            f"{publication_config_path(Path.cwd()).name} or KORU_VALIDATOR_CHECKOUT",
        )
    script = config.validator_checkout / DEFAULT_VALIDATOR_SCRIPT
    if not script.is_file():
        raise GitHubCliError(f"validator dispatch script not found: {script}")
    return script


def dispatch_validator_merge(
    project: Path,
    *,
    ticket_id: str,
    pr_number: int | None = None,
    owner: str | None = None,
    name: str | None = None,
    config: PublicationConfig | None = None,
    dry_run: bool = False,
    merge: bool | None = None,
) -> dict[str, Any]:
    """Freeze PR head and dispatch validator-agent direct-pr."""
    if not gh_available():
        raise GitHubCliError("gh CLI is required for koru ci publish")

    project = project.resolve()
    cfg = config or load_publication_config(project)
    if merge is not None:
        cfg = replace(cfg, merge=merge)
    repo = resolve_github_repo(project)
    resolved_owner = owner or repo.owner
    resolved_name = name or repo.name
    resolved_pr = pr_number
    if resolved_pr is None:
        branch = current_branch(project)
        resolved_pr = find_open_pr_for_branch(repo, branch)
        if resolved_pr is None:
            raise GitHubCliError(f"no open PR found for branch {branch!r}")

    frozen_head = resolve_pr_head_sha(repo, resolved_pr)
    script = _resolve_validator_script(cfg)
    cmd = [
        str(script),
        "--owner",
        resolved_owner,
        "--name",
        resolved_name,
        "--pr",
        str(resolved_pr),
        "--ticket",
        ticket_id,
    ]
    if cfg.wait_checks:
        cmd.append("--wait-checks")
    if cfg.watch:
        cmd.append("--watch")
    if cfg.merge:
        cmd.append("--merge")
    if cfg.update_branch:
        cmd.append("--update-branch")
    if dry_run:
        cmd.append("--dry-run")

    if dry_run:
        return {
            "status": "dry_run",
            "frozen_head": frozen_head,
            "command": cmd,
            "repo": repo.slug,
            "pr": resolved_pr,
            "ticket": ticket_id,
        }

    proc = subprocess.run(
        cmd,
        cwd=str(cfg.validator_checkout),
        capture_output=True,
        text=True,
        check=False,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    status = "published" if proc.returncode == 0 else "failed"
    return {
        "status": status,
        "exit_code": proc.returncode,
        "frozen_head": frozen_head,
        "repo": repo.slug,
        "pr": resolved_pr,
        "ticket": ticket_id,
        "output_tail": output[-8000:],
    }
