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
    "gillm",
    "nfo",
    "planfile",
    "code2llm",
    "redup",
    "wup",
    "regix",
    "testql",
    "prefact",
    "redsl",
    "vallm",
    "pyqual",
    "pfix",
    "goal",
    "costs",
    "llx",
    "doql",
    "protogate",
    "op3",
    "mdflow",
    "metrun",
    "pretest",
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


def _venv_python(root: Path, package: str) -> Path | None:
    package_root = root / package
    for venv_name in (".venv", "venv"):
        candidate = package_root / venv_name / "bin" / "python"
        if candidate.is_file():
            return candidate
    return None


def _target_python(root: Path, *, python: Path | None, target_venv: str | None) -> Path | None:
    if python is not None:
        return python.expanduser()
    if target_venv:
        return _venv_python(root, target_venv)
    return Path(sys.executable)


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


def _sync_single_package(
    name: str,
    repo: Path,
    *,
    python_executable: Path,
    pull: bool,
    allow_dirty_pull: bool,
    upgrade: bool,
    eager: bool,
    runner: Runner,
) -> SyncItem:
    if not (repo / "pyproject.toml").is_file():
        return SyncItem(name=name, path=repo, status="missing", detail="no pyproject.toml")

    pull_detail = ""
    if pull:
        pulled, detail = _pull_repo(repo, runner, allow_dirty=allow_dirty_pull)
        if not pulled:
            pull_detail = detail

    command = [str(python_executable), "-m", "pip", "install"]
    if upgrade:
        command.append("--upgrade")
    if eager:
        command.extend(["--upgrade-strategy", "eager"])
    command.extend(["-e", str(repo)])
    install = runner(command, repo)
    if install.returncode == 0:
        detail = f"editable install via {python_executable}"
        status = "synced-stale" if pull_detail else "synced"
        if pull_detail:
            detail = f"{pull_detail}; {detail}"
        return SyncItem(name=name, path=repo, status=status, detail=detail)
    detail = (install.stderr or install.stdout).strip() or "pip install -e failed"
    return SyncItem(name=name, path=repo, status="failed", detail=detail)


def sync_developer_packages(
    *,
    root: Path | None = None,
    packages: Sequence[str] = DEFAULT_PACKAGES,
    python: Path | None = None,
    target_venv: str | None = None,
    pull: bool = False,
    allow_dirty_pull: bool = False,
    upgrade: bool = False,
    eager: bool = False,
    runner: Runner = _run,
) -> list[SyncItem]:
    """Install local semcod repositories in editable mode.

    The default is intentionally offline/local: it does not pull from git and
    only refreshes editable installs for checkouts that already exist.
    """
    base = (root or _default_semcod_root()).expanduser().resolve()
    python_executable = _target_python(base, python=python, target_venv=target_venv)
    if python_executable is None:
        detail = f"target venv python not found: {base / str(target_venv or '')}"
        return [SyncItem(name=name, path=base / name, status="failed", detail=detail) for name in packages]

    return [
        _sync_single_package(
            name,
            base / name,
            python_executable=python_executable,
            pull=pull,
            allow_dirty_pull=allow_dirty_pull,
            upgrade=upgrade,
            eager=eager,
            runner=runner,
        )
        for name in packages
    ]


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
    sync.add_argument(
        "--python",
        type=Path,
        default=None,
        help="Python executable that receives the editable installs.",
    )
    sync.add_argument(
        "--target-venv",
        default=None,
        help="Install into --root/<package>/.venv or venv, for example --target-venv koru.",
    )
    sync.add_argument("--pull", action="store_true", help="Run git pull --ff-only before install.")
    sync.add_argument(
        "--latest",
        action="store_true",
        help="Shortcut for --pull --upgrade: fast-forward clean repos and upgrade editable installs.",
    )
    sync.add_argument("--upgrade", action="store_true", help="Pass --upgrade to pip install.")
    sync.add_argument(
        "--eager",
        action="store_true",
        help="With --upgrade, pass --upgrade-strategy eager to pip.",
    )
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
        python=args.python,
        target_venv=args.target_venv,
        pull=args.pull or args.latest,
        allow_dirty_pull=args.allow_dirty_pull,
        upgrade=args.upgrade or args.latest,
        eager=args.eager,
    )

    failed = False
    for item in results:
        print(f"{item.status:12} {item.name:12} {item.path} {item.detail}".rstrip())
        failed = failed or item.status == "failed"
    return 1 if failed else 0
