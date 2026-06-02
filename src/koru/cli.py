"""Command-line entrypoint for koru."""


import argparse
import os
import shlex
import sys
from collections.abc import Callable
from pathlib import Path

import koru.cli_parser as _cli_parser
from koru.agents import detect_agent_options
from koru.autoloop_cli import autoloop_main
from koru.autonomous import autonomous_main
from koru.autonomous_processes import stop_prior_autonomous_for_auto_start
from koru.autonomous_runtime import project_venv_reexec_argv
from koru.autopilot.cli_command import autopilot_main
from koru.cli_loop import command_loop_main as _command_loop_main
from koru.cli_scan import scan_main as _scan_main
from koru.dev_sync import dev_main
from koru.git_cli import git_main

_build_parser = _cli_parser._build_parser
_command_value = _cli_parser._command_value


from koru.env_flags import env_truthy as _env_truthy



def _is_bare_invocation(args: argparse.Namespace) -> bool:
    """True when the user typed only ``koru`` (or ``koru --project P``).

    Bare = no action flag (init/bootstrap/context/queue/watch) and no
    ``--command``. We route this to the markdown brief — the friendliest
    starting point for both humans and LLM agents.
    """
    return not (
        args.init
        or args.init_agent_lane
        or args.doctor
        or args.bootstrap
        or args.context
        or args.queue
        or args.watch
        or args.command
    )








def _dsl_main(argv: list[str]) -> int:
    from korudsl.cli import main as dsl_main

    return dsl_main(argv)


def _api_main(argv: list[str]) -> int:
    from koruapi.cli import main as api_main

    return api_main(argv)


def _peek_project_from_argv(argv: list[str]) -> Path:
    for idx, part in enumerate(argv):
        if part == "--project" and idx + 1 < len(argv):
            return Path(argv[idx + 1]).expanduser().resolve()
        if part.startswith("--project="):
            return Path(part.split("=", 1)[1]).expanduser().resolve()
    return Path.cwd().resolve()


def _path_is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _project_cli_reexec_argv(project: Path) -> list[str] | None:
    """Return argv for re-execing generic CLI commands inside repo-local .venv."""
    if os.environ.get("KORU_CLI_REEXECED") or _env_truthy("KORU_CLI_NO_REEXEC"):
        return None
    local_venv = (project / ".venv").resolve()
    local_koru = local_venv / "bin" / "koru"
    if not (local_koru.is_file() and os.access(local_koru, os.X_OK)):
        return None

    executable = Path(sys.executable).expanduser()
    prefix = Path(sys.prefix).expanduser()
    if _path_is_relative_to(executable, local_venv) or _path_is_relative_to(prefix, local_venv):
        return None

    return [str(local_koru), *sys.argv[1:]]


def _maybe_print_project_venv_hint(raw_args: list[str]) -> None:
    """Print a deterministic hint to run the project-local CLI entrypoint."""
    if _env_truthy("KORU_SUPPRESS_VENV_HINT"):
        return
    project = _peek_project_from_argv(raw_args)
    local_koru = (project / ".venv" / "bin" / "koru").resolve()
    if not (local_koru.is_file() and os.access(local_koru, os.X_OK)):
        return
    command = " ".join(shlex.quote(part) for part in [str(local_koru), *raw_args])
    print(
        "koru: hint: project-local CLI detected; if you hit unrecognized args, rerun:",
        file=sys.stderr,
    )
    print(f"  {command}", file=sys.stderr)


def _should_suggest_wizard(argv: list[str], project: Path) -> bool:
    """Heuristic: only nudge brand-new users running ``koru auto`` with no args.

    We require: TTY stdin/stdout, no extra args, no ``.planfile`` in project,
    and no ``KORU_AUTO_SKIP_WIZARD`` env override.
    """
    if argv:
        return False
    if os.environ.get("KORU_AUTO_SKIP_WIZARD", "").strip().lower() in ("1", "true", "yes"):
        return False
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return False
    return not (project / ".planfile").exists() and not (project / ".koru").exists()


def _lazy_module_main(module_name: str, attr_name: str, argv: list[str]) -> int:
    return getattr(__import__(module_name, fromlist=[attr_name]), attr_name)(argv)




_SUBCOMMANDS: dict[str, Callable[[list[str]], int]] = {
    "events": lambda argv: _lazy_module_main("koru.cli_events", "events_main", argv),
    "doctor": lambda argv: _lazy_module_main(
        "koru.cli_doctor",
        "doctor_subcommand_main",
        argv,
    ),
    "configure": lambda argv: _lazy_module_main("koru.configurator", "configure_main", argv),
    "mesh": lambda argv: _lazy_module_main("korumesh.cli", "mesh_main", argv),
    "vision": lambda argv: _lazy_module_main("koruvision.cli", "vision_main", argv),
    "observe": lambda argv: _lazy_module_main("koruobserve.cli", "observe_main", argv),
    "init-ci": lambda argv: _lazy_module_main("koru.cli_init", "init_ci_main", argv),
    "init-ide": lambda argv: _lazy_module_main("koru.mcp_provision", "init_ide_main", argv),
    "agent-backends": lambda argv: _lazy_module_main(
        "koru.cli_agent_backends",
        "agent_backends_main",
        argv,
    ),
    "task": lambda argv: _lazy_module_main("koru.cli_task", "_task_main", argv),
    "agent": lambda argv: _lazy_module_main("koru.cli_agent", "_agent_main", argv),
    "local-serve": lambda argv: _lazy_module_main(
        "koru.cli_local_serve",
        "_local_serve_main",
        argv,
    ),
    "serve": lambda argv: _lazy_module_main("koru.cli_serve", "_serve_main", argv),
    "self": lambda argv: _lazy_module_main("koru.cli_self", "self_main", argv),
    "scan": _scan_main,
    "refactor-planfile-handoff": lambda argv: _lazy_module_main(
        "koru.cli_refactor_planfile_handoff",
        "_refactor_planfile_handoff_main",
        argv,
    ),
    "gate": lambda argv: _lazy_module_main("koru.cli_gate", "gate_main", argv),
    "queue": lambda argv: _lazy_module_main("koru.cli_queue", "queue_main", argv),
    "replay": lambda argv: _lazy_module_main("koru.cli_replay", "replay_main", argv),
    "gc": lambda argv: _lazy_module_main("koru.cli_gc", "gc_main", argv),
    "git": git_main,
    "tools": lambda argv: _lazy_module_main("koru.cli_tools", "_tools_main", argv),
    "mcp-serve": lambda argv: _lazy_module_main("koruapi.mcp", "mcp_main", argv),
    "ide-router": lambda argv: _lazy_module_main(
        "koru.cli_ide_router",
        "ide_router_main",
        argv,
    ),
    "ide": lambda argv: _lazy_module_main("koru.cli_ide", "ide_main", argv),
    "autopilot": autopilot_main,
    "autoloop": autoloop_main,
    "autonomous": autonomous_main,
    "auto": lambda argv: _lazy_module_main("koru.cli_auto", "_auto_main", argv),
    "wizard": lambda argv: _lazy_module_main("koru.wizard.cli", "wizard_main", argv),
    "dsl": _dsl_main,
    "api": _api_main,
    "topology": lambda argv: _lazy_module_main("koru.cli_topology", "topology_main", argv),
    "strategy": lambda argv: _lazy_module_main("koru.cli_strategy", "strategy_main", argv),
    "runtime-context": lambda argv: _lazy_module_main(
        "koru.cli_runtime_context",
        "_runtime_context_main",
        argv,
    ),
    "tagi": lambda argv: _lazy_module_main("koru.cli_tagi", "tagi_main", argv),
    "dev": dev_main,
}








def _maybe_reexec_for_project_venv(raw_args: list[str]) -> None:
    subcommand = raw_args[0] if raw_args else ""
    if not raw_args:
        return
    project = _peek_project_from_argv(raw_args)

    if subcommand in {"auto", "autonomous"}:
        if reexec_argv := project_venv_reexec_argv(project):
            env = dict(os.environ)
            env["KORU_AUTONOMOUS_REEXECED"] = "1"
            env["KORU_CLI_REEXECED"] = "1"
            print(f"koru: switching to project venv: {' '.join(reexec_argv)}", file=sys.stderr)
            os.execvpe(reexec_argv[0], reexec_argv, env)
        return

    if subcommand == "doctor" or "--doctor" in raw_args:
        if reexec_argv := _project_cli_reexec_argv(project):
            env = dict(os.environ)
            env["KORU_CLI_REEXECED"] = "1"
            print(f"koru: switching to project venv CLI: {' '.join(reexec_argv)}", file=sys.stderr)
            os.execvpe(reexec_argv[0], reexec_argv, env)


def _dispatch_flag_action(args: argparse.Namespace, raw_args: list[str]) -> int | None:
    if args.doctor:
        return __import__("koru.cli_doctor", fromlist=["doctor_main"]).doctor_main(
            args,
            raw_args,
        )
    if args.init_agent_lane:
        return __import__("koru.cli_init", fromlist=["init_agent_lane_main"]).init_agent_lane_main(
            args,
        )
    if args.init:
        return __import__("koru.cli_init", fromlist=["init_main"]).init_main(args)
    if args.context:
        return __import__("koru.cli_context", fromlist=["_context_main"])._context_main(
            args,
        )
    if args.bootstrap:
        return __import__("koru.cli_bootstrap", fromlist=["_bootstrap_main"])._bootstrap_main(args)
    if args.watch:
        return __import__("koru.cli_watch", fromlist=["watch_main"]).watch_main(args)
    if args.queue:
        return __import__("koru.cli_queue", fromlist=["queue_run_main"]).queue_run_main(args)
    return None


def _suggest_subcommand(token: str) -> str:
    """Return the closest known subcommand for typo-friendly hints."""
    import difflib

    if not token or token.startswith("-"):
        return ""
    if token == "auto" and "auto" not in _SUBCOMMANDS and "autonomous" in _SUBCOMMANDS:
        return "autonomous"
    matches = difflib.get_close_matches(token, list(_SUBCOMMANDS), n=1, cutoff=0.55)
    return matches[0] if matches else ""


def _dispatch_auto_alias(raw_args: list[str]) -> int | None:
    """Route ``koru auto`` on legacy installs that only expose ``autonomous``.

    PyPI/pyenv builds before the ``auto`` entry was added to ``_SUBCOMMANDS``
    reject ``koru auto`` with ``unrecognized arguments``. Prefer
    :func:`koru.cli_auto._auto_main` when present (wizard hint, stop prior loop,
    ``--replace-existing``); otherwise fall back to ``autonomous``.
    """
    if not raw_args or raw_args[0] != "auto" or "auto" in _SUBCOMMANDS:
        return None
    tail = raw_args[1:]
    try:
        from koru.cli_auto import _auto_main

        return _auto_main(tail)
    except (ImportError, AttributeError):
        pass
    if "autonomous" not in _SUBCOMMANDS:
        return None
    handler = _SUBCOMMANDS["autonomous"]
    try:
        return handler(tail, invoked_as_auto=True)
    except TypeError:
        return handler(tail)


def _print_unknown_subcommand_hint(subcommand: str) -> None:
    suggestion = _suggest_subcommand(subcommand)
    if suggestion:
        print(
            f"koru: '{subcommand}' is not a known subcommand. "
            f"Did you mean 'koru {suggestion}'?",
            file=sys.stderr,
        )
        return
    known = ", ".join(sorted(_SUBCOMMANDS))
    print(
        f"koru: '{subcommand}' is not a known subcommand. "
        f"Known subcommands: {known}",
        file=sys.stderr,
    )


def _handle_parser_exit(exc: SystemExit, raw_args: list[str], subcommand: str) -> int:
    code = exc.code if isinstance(exc.code, int) else 1
    if code == 2 and subcommand and not subcommand.startswith("-"):
        _print_unknown_subcommand_hint(subcommand)
        _maybe_print_project_venv_hint(raw_args)
    if code == 2 and ("doctor" in raw_args or "--doctor" in raw_args):
        _maybe_print_project_venv_hint(raw_args)
    return code


def main() -> int:
    raw_args = sys.argv[1:]
    _maybe_reexec_for_project_venv(raw_args)
    if (auto_rc := _dispatch_auto_alias(raw_args)) is not None:
        return auto_rc
    subcommand = raw_args[0] if raw_args else ""
    if subcommand in _SUBCOMMANDS:
        return _SUBCOMMANDS[subcommand](raw_args[1:])

    try:
        args = _build_parser().parse_args(raw_args)
    except SystemExit as exc:
        return _handle_parser_exit(exc, raw_args, subcommand)

    if _is_bare_invocation(args):
        args.context = True
        args.output_format = "markdown"

    if (rc := _dispatch_flag_action(args, raw_args)) is not None:
        return rc

    if not args.command:
        parser = _build_parser()
        parser.error("--command is required unless --queue is used")

    return _command_loop_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
