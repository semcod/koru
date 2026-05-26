"""Safe Git porcelain commands exposed through koru."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from koru.git_attribution import install_koru_agent_coauthor_hook


def _run_git(
    project: Path,
    args: list[str],
    *,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(project), *args],
        check=check,
        capture_output=True,
        text=True,
    )


def _print_result(result: subprocess.CompletedProcess[str]) -> None:
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")


def _current_branch(project: Path) -> str | None:
    result = _run_git(project, ["branch", "--show-current"])
    branch = result.stdout.strip()
    return branch or None


def _ensure_git_repo(project: Path) -> bool:
    return _run_git(project, ["rev-parse", "--is-inside-work-tree"]).returncode == 0


def _load_gh2mcp_service_class() -> tuple[Any | None, str]:
    try:
        from gh2mcp.sync import GitHubTokenSyncService
    except Exception as exc:
        return None, str(exc)
    return GitHubTokenSyncService, ""


def _gh2mcp_service(env_file: str) -> tuple[Any | None, str]:
    service_class, error = _load_gh2mcp_service_class()
    if service_class is None:
        return None, error or "gh2mcp is not installed"
    return service_class(env_file), ""


def _sync_gh2mcp_token(args: argparse.Namespace) -> bool:
    service, error = _gh2mcp_service(args.env_file)
    if service is None:
        print(f"koru git: gh2mcp unavailable: {error}", file=sys.stderr)
        return False
    data = service.sync_token(force_gh_cli=args.force_gh_cli)
    if not data.get("success"):
        print(f"koru git: gh2mcp token sync failed: {data.get('error')}", file=sys.stderr)
        return False
    print(
        "koru git: gh2mcp token sync ok "
        f"(source={data.get('source')}, user={data.get('user')})",
        file=sys.stderr,
    )
    return True


def _stage_commit_changes(project: Path, args: argparse.Namespace) -> int | None:
    if args.add:
        add_result = _run_git(project, ["add", "--", *args.add])
        if add_result.returncode != 0:
            _print_result(add_result)
            return add_result.returncode
    if args.all:
        add_result = _run_git(project, ["add", "-A"])
        if add_result.returncode != 0:
            _print_result(add_result)
            return add_result.returncode
    return None


def _commit_command(args: argparse.Namespace) -> list[str]:
    command = ["commit", "-m", args.message]
    if args.allow_empty:
        command.append("--allow-empty")
    if args.no_verify:
        command.append("--no-verify")
    if args.dry_run:
        command.append("--dry-run")
    return command


def _push_args_after_commit(project: Path, args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        project=project,
        remote=args.remote,
        branch=args.branch,
        set_upstream=args.set_upstream,
        dry_run=False,
        gh2mcp=args.gh2mcp,
        env_file=args.env_file,
        force_gh_cli=args.force_gh_cli,
    )


def _action_commit(args: argparse.Namespace) -> int:
    project = args.project.resolve()
    if not _ensure_git_repo(project):
        print(f"koru git commit: not a git repository: {project}", file=sys.stderr)
        return 2

    install_koru_agent_coauthor_hook(project)

    stage_error = _stage_commit_changes(project, args)
    if stage_error is not None:
        return stage_error

    result = _run_git(project, _commit_command(args))
    _print_result(result)
    if result.returncode != 0:
        return result.returncode

    if args.push:
        return _action_push(_push_args_after_commit(project, args))
    return 0


def _action_push(args: argparse.Namespace) -> int:
    project = args.project.resolve()
    if not _ensure_git_repo(project):
        print(f"koru git push: not a git repository: {project}", file=sys.stderr)
        return 2

    if getattr(args, "gh2mcp", False) and not _sync_gh2mcp_token(args):
        return 2

    remote = args.remote
    branch = args.branch or _current_branch(project)
    command = ["push"]
    if args.dry_run:
        command.append("--dry-run")
    if args.set_upstream:
        command.append("--set-upstream")
    if remote:
        command.append(remote)
    if branch:
        command.append(branch)

    result = _run_git(project, command)
    _print_result(result)
    return result.returncode


def _action_github_status(args: argparse.Namespace) -> int:
    service, error = _gh2mcp_service(args.env_file)
    if service is None:
        print(f"koru git github-status: gh2mcp unavailable: {error}", file=sys.stderr)
        return 2
    data = service.get_status(include_token=args.include_token)
    print(json.dumps(data, indent=2, sort_keys=True))
    return 0 if data.get("configured") or data.get("gh_available") else 1


def _action_last_repo(args: argparse.Namespace) -> int:
    service, error = _gh2mcp_service(args.env_file)
    if service is None:
        print(f"koru git last-repo: gh2mcp unavailable: {error}", file=sys.stderr)
        return 2
    data = service.get_last_pushed_repo(owner=args.owner, limit=args.limit)
    print(json.dumps(data, indent=2, sort_keys=True))
    return 0 if data.get("success") else 1


def _add_commit_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    commit = sub.add_parser("commit", help="Create a Git commit with koru co-author attribution.")
    commit.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    commit.add_argument("-m", "--message", required=True, help="Commit message subject/body.")
    commit.add_argument("-a", "--all", action="store_true", help="Stage all changes before commit.")
    commit.add_argument("--add", nargs="+", help="Stage only these paths before commit.")
    commit.add_argument("--allow-empty", action="store_true", help="Allow an empty commit.")
    commit.add_argument("--no-verify", action="store_true", help="Pass --no-verify to git commit.")
    commit.add_argument("--dry-run", action="store_true", help="Ask git commit to dry-run.")
    commit.add_argument("--push", action="store_true", help="Push after a successful commit.")
    commit.add_argument("--remote", default="origin", help="Remote for --push.")
    commit.add_argument(
        "--branch",
        default=None,
        help="Branch for --push; defaults to current branch.",
    )
    commit.add_argument("--set-upstream", action="store_true", help="Set upstream when pushing.")
    commit.add_argument(
        "--gh2mcp",
        action="store_true",
        help="Sync GitHub token via gh2mcp before --push.",
    )
    commit.add_argument("--env-file", default=".env", help="gh2mcp .env path.")
    commit.add_argument(
        "--force-gh-cli",
        action="store_true",
        help="Force gh2mcp token source to `gh auth token`.",
    )
    commit.set_defaults(func=_action_commit)


def _add_push_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    push = sub.add_parser("push", help="Push the current branch via koru.")
    push.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    push.add_argument("remote", nargs="?", default="origin", help="Remote name.")
    push.add_argument("branch", nargs="?", default=None, help="Branch; defaults to current branch.")
    push.add_argument("--set-upstream", action="store_true", help="Set upstream for the branch.")
    push.add_argument("--dry-run", action="store_true", help="Ask git push to dry-run.")
    push.add_argument(
        "--gh2mcp",
        action="store_true",
        help="Sync GitHub token via gh2mcp before push.",
    )
    push.add_argument("--env-file", default=".env", help="gh2mcp .env path.")
    push.add_argument(
        "--force-gh-cli",
        action="store_true",
        help="Force gh2mcp token source to `gh auth token`.",
    )
    push.set_defaults(func=_action_push)


def _add_github_status_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    github_status = sub.add_parser("github-status", help="Show GitHub auth status through gh2mcp.")
    github_status.add_argument("--env-file", default=".env", help="gh2mcp .env path.")
    github_status.add_argument(
        "--include-token",
        action="store_true",
        help="Include token in JSON output.",
    )
    github_status.set_defaults(func=_action_github_status)


def _add_last_repo_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    last_repo = sub.add_parser(
        "last-repo",
        help="Resolve the last pushed GitHub repo through gh2mcp.",
    )
    last_repo.add_argument("--env-file", default=".env", help="gh2mcp .env path.")
    last_repo.add_argument("--owner", default=None, help="GitHub user/org; defaults via gh2mcp.")
    last_repo.add_argument("--limit", type=int, default=100, help="Repository scan limit.")
    last_repo.set_defaults(func=_action_last_repo)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="koru git", description="Commit and push via koru.")
    sub = parser.add_subparsers(dest="action", required=True)
    _add_commit_parser(sub)
    _add_push_parser(sub)
    _add_github_status_parser(sub)
    _add_last_repo_parser(sub)
    return parser


def git_main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    func: Any = args.func
    return int(func(args))


__all__ = ["git_main", "build_parser"]
