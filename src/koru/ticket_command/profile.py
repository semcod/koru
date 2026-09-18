from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
from pathlib import Path

ISSUE = re.compile(r"https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/([1-9][0-9]*)")
ISSUE_LIST = re.compile(r"https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues(?:/?|\*|/\*)?")


def command(root: Path, argv: list[str], *, stdin: str | None = None, env: dict | None = None) -> str:
    result = subprocess.run(argv, cwd=root, input=stdin, text=True, capture_output=True, timeout=1800, env=env)
    if result.returncode:
        # Raw stderr may include credentials, issue content or private logs.
        raise RuntimeError(
            f"{Path(argv[0]).name} failed (exit {result.returncode}); inspect the private execution state"
        )
    return result.stdout.strip()


def git(root: Path, *argv: str) -> str:
    return command(root, ["git", *argv])


def no_symlinks(path: Path) -> None:
    if any(item.is_symlink() for item in (path, *path.parents)):
        raise ValueError("symlinked repository or working-data path")


def parse_issue(url: str) -> tuple[str, int]:
    match = ISSUE.fullmatch(url)
    if not match:
        raise ValueError("expected an exact GitHub issue URL")
    return match[1], int(match[2])


def parse_target(url: str) -> tuple[str, int | None]:
    match = ISSUE_LIST.fullmatch(url)
    if match:
        return match[1], None
    return parse_issue(url)


def validator_environment(adapter: dict, root: Path) -> dict:
    """Load only the operator-pinned environment; never evaluate shell syntax."""
    environment = dict(os.environ)
    if not adapter.get("environment_file"):
        return environment
    path = Path(adapter["environment_file"])
    no_symlinks(path.absolute())
    if not path.is_absolute() or path.is_relative_to(root):
        raise ValueError("Validator environment must be outside the repository")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != adapter.get("environment_sha256"):
        raise ValueError("Validator environment no longer matches the operator pin")
    for line in raw.decode().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, separator, value = line.partition("=")
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise ValueError("unsupported Validator environment entry")
        environment[name] = " ".join(shlex.split(value))
    return environment


def load_profile(url: str, path: Path) -> dict:
    repository, number = parse_target(url)
    no_symlinks(path.absolute())
    raw = path.read_bytes()
    config = json.loads(raw)
    if config.get("schema") != "koru.ticket-profiles/v1":
        raise ValueError("unsupported local ticket profile schema")
    spec = config.get("repositories", {}).get(repository)
    if not isinstance(spec, dict):
        raise ValueError(f"no local execution profile for {repository}")
    spec = dict(spec)
    root = _profile_root(spec, path, repository)
    _validate_profile_delivery(spec, repository, root)
    return {
        **spec,
        "primary": root,
        "repository": repository,
        "number": number,
        "url": url,
        "profile_sha256": hashlib.sha256(raw).hexdigest(),
    }


def _profile_root(spec: dict, path: Path, repository: str) -> Path:
    root = Path(spec["primary"]).expanduser().absolute()
    no_symlinks(root)
    if path.absolute().is_relative_to(root):
        raise ValueError("execution authority profile must be outside the target repository")
    entries = git(root, "worktree", "list", "--porcelain").splitlines()
    primary = Path(entries[0].removeprefix("worktree "))
    if root != primary or not root.is_dir():
        raise ValueError("profile must name the Git-registered primary checkout")
    remote = git(root, "remote", "get-url", "origin")
    if remote not in {
        f"git@github.com:{repository}.git",
        f"https://github.com/{repository}.git",
        f"https://github.com/{repository}",
    }:
        raise ValueError("origin does not match the requested repository")
    return root


def _validate_profile_delivery(spec: dict, repository: str, root: Path) -> None:
    mode = spec.get("delivery")
    if mode not in {"main-only", "validator"}:
        raise ValueError("profile must declare main-only or validator delivery")
    if repository == "maskservice/c2004" and mode != "main-only":
        raise ValueError("C2004 retains its explicit main-only exception")
    if not spec.get("allowed_paths") or not spec.get("context_files") or not spec.get("verify"):
        raise ValueError("local profile needs bounded paths, context files and verification commands")
    for argv in spec["verify"]:
        if not isinstance(argv, list) or not argv or any(not isinstance(v, str) or not v for v in argv):
            raise ValueError("verification commands must be nonempty argv arrays")
    if mode == "validator":
        _validate_validator_pin(spec, root)


def _validate_validator_pin(spec: dict, root: Path) -> None:
    validator = spec.get("validator", {})
    launcher = Path(validator.get("launcher", ""))
    no_symlinks(launcher.absolute())
    if (
        launcher.name != "run-local-direct-pr.sh"
        or not launcher.is_absolute()
        or not launcher.is_file()
        or launcher.is_relative_to(root)
        or hashlib.sha256(launcher.read_bytes()).hexdigest() != validator.get("sha256")
        or not validator.get("key_file")
    ):
        raise ValueError("protected local OneDev/Validator adapter is not pinned outside the repository")
    validator_environment(validator, root)
