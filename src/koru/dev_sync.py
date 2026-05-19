"""Developer environment synchronisation helpers for local semcod checkouts."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PACKAGES: tuple[str, ...] = (
    "koru",
    "redup",
    "wup",
    "regix",
    "testql",
    "planfile",
)

Runner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class SyncItem:
    name: str
    path: Path
    status: str
    detail: str = ""


def _default_semcod_root() -> Path:
    return Path.home() / "github" / "semcod"


def _run(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _is_dirty(repo: Path, runner: Runner) -> bool:
    result = runner(["git", "status", "--porcelain"], repo)
    return result.returncode == 0 and bool(result.stdout.strip())


def _pull_repo(repo: Path, runner: Runner, *, allow_dirty: bool) -> tuple[bool, str]:
    if _is_dirty(repo, runner) and not allow_dirty:
        return False, "dirty worktree; skip pull"
    result = runner(["git", "pull", "--ff-only"], repo)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or "git pull failed"
        return False, detail
    return True, (result.stdout or "").strip()


def sync_developer_packages(
    *,
    root: Path | None = None,
    packages: Sequence[str] = DEFAULT_PACKAGES,
    pull: bool = False,
    allow_dirty_pull: bool = False,
    runner: Runner = _run,
) -> list[SyncItem]:
    """Install local semcod repositories in editable mode.

    The default is intentionally offline/local: it does not pull from git and
    only refreshes editable installs for checkouts that already exist.
    """
    base = (root or _default_semcod_root()).expanduser().resolve()
    results: list[SyncItem] = []

    for name in packages:
        repo = base / name
        if not (repo / "pyproject.toml").is_file():
            results.append(SyncItem(name=name, path=repo, status="missing", detail="no pyproject.toml"))
            continue

        if pull:
            pulled, detail = _pull_repo(repo, runner, allow_dirty=allow_dirty_pull)
            if not pulled:
                results.append(SyncItem(name=name, path=repo, status="pull-skipped", detail=detail))
                continue

        command = [sys.executable, "-m", "pip", "install", "-e", str(repo)]
        install = runner(command, repo)
        if install.returncode == 0:
            results.append(SyncItem(name=name, path=repo, status="synced", detail="editable install"))
        else:
            detail = (install.stderr or install.stdout).strip() or "pip install -e failed"
            results.append(SyncItem(name=name, path=repo, status="failed", detail=detail))

    return results


def dev_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Developer helpers for local semcod packages.")
    sub = parser.add_subparsers(dest="command", required=True)
    sync = sub.add_parser("sync", help="Install local semcod packages in editable mode.")
    sync.add_argument("--root", type=Path, default=_default_semcod_root())
    sync.add_argument(
        "--packages",
        default=",".join(DEFAULT_PACKAGES),
        help="Comma-separated package directories under --root.",
    )
    sync.add_argument("--pull", action="store_true", help="Run git pull --ff-only before install.")
    sync.add_argument(
        "--allow-dirty-pull",
        action="store_true",
        help="Allow --pull even when a package worktree has local changes.",
    )

    args = parser.parse_args(argv)
    if args.command != "sync":
        parser.error(f"unknown command: {args.command}")

    packages = tuple(item.strip() for item in args.packages.split(",") if item.strip())
    results = sync_developer_packages(
        root=args.root,
        packages=packages,
        pull=args.pull,
        allow_dirty_pull=args.allow_dirty_pull,
    )

    failed = False
    for item in results:
        print(f"{item.status:12} {item.name:12} {item.path} {item.detail}".rstrip())
        failed = failed or item.status in {"failed", "pull-skipped"}
    return 1 if failed else 0
