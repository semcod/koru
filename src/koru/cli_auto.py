import os
import sys
from pathlib import Path

from koru.autonomous import (
    _parse_autonomous_args,
    autonomous_main,
    stop_prior_autonomous_for_auto_start,
)
from koru.autonomous_processes import try_acquire_autonomous_start_lock

_MAINTENANCE_ACTIONS = {"doctor", "self-heal", "status"}
_GLOBAL_OPTIONS_WITH_VALUE = {"--socket"}


def _legacy_attr(name: str, fallback):
    legacy = sys.modules.get("koru._legacy_cli_impl")
    return getattr(legacy, name, fallback) if legacy is not None else fallback


def _peek_project_from_argv(argv: list[str]) -> Path:
    for idx, part in enumerate(argv):
        if part == "--project" and idx + 1 < len(argv):
            return Path(argv[idx + 1]).expanduser().resolve()
        if part.startswith("--project="):
            return Path(part.split("=", 1)[1]).expanduser().resolve()
    return Path.cwd().resolve()


def _should_suggest_wizard(argv: list[str], project: Path) -> bool:
    if argv:
        return False
    if os.environ.get("KORU_AUTO_SKIP_WIZARD", "").strip().lower() in {"1", "true", "yes"}:
        return False
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return False
    return not (project / ".planfile").exists() and not (project / ".koru").exists()


def _first_action_token(argv: list[str]) -> str | None:
    idx = 0
    while idx < len(argv):
        token = argv[idx]
        if token in _GLOBAL_OPTIONS_WITH_VALUE:
            idx += 2
            continue
        if any(token.startswith(f"{option}=") for option in _GLOBAL_OPTIONS_WITH_VALUE):
            idx += 1
            continue
        return token
    return None


def _is_maintenance_action(argv: list[str]) -> bool:
    return _first_action_token(argv) in _MAINTENANCE_ACTIONS


def _auto_start_argv(argv: list[str]) -> list[str]:
    if "--replace-existing" in argv or "--allow-duplicate" in argv:
        return list(argv)
    return ["--replace-existing", *argv]


def _enable_auto_reload_reuse_window_for_auto() -> None:
    """Let ``koru auto`` recover a cold VSIX plugin without fresh windows.

    The lower-level reload module keeps ``--reuse-window`` off by default
    because library callers may not be running the target project in the
    target IDE. ``koru auto`` opts in only when Koru is **not** running from
    the target IDE integrated terminal — from there ``cursor -r`` tends to
    spawn duplicate windows and command-palette automation is refused (would
    type into the shell). Operators in an integrated terminal should reload
    manually or run ``koru: Connect autopilot daemon``.
    """
    from koruide.ide import detect_terminal_host_ide_id

    if detect_terminal_host_ide_id() is not None:
        return
    os.environ.setdefault("KORU_AUTOPILOT_REUSE_WINDOW_RELOAD", "1")


def _print_wizard_suggestion() -> None:
    print(
        "koru auto: no .planfile detected — recommended first step is "
        "`koru wizard` to pick a strategy and seed the first ticket.",
        file=sys.stderr,
    )
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        print(
            "  GUI: `koru wizard --gui` opens a browser wizard "
            "(requires pip install 'koru[api]').",
            file=sys.stderr,
        )
    print(
        "(skip with KORU_AUTO_SKIP_WIZARD=1 or run `koru auto --allow-duplicate`)",
        file=sys.stderr,
    )


def _ensure_strategy_config(project: Path) -> None:
    try:
        from koru.autonomy_strategy import ensure_autonomy_strategy_config

        strategy_result = ensure_autonomy_strategy_config(project)
        if strategy_result.created_koru_yaml or strategy_result.added_strategy:
            print(
                "koru auto: wrote default autonomy.strategy to "
                f"{strategy_result.path}; strategy={strategy_result.strategy_id}. "
                "Review/tune with `koru strategy --prompt`.",
                file=sys.stderr,
            )
    except Exception as exc:  # noqa: BLE001 - advisory setup must not block auto
        print(f"koru auto: autonomy.strategy ensure skipped: {exc}", file=sys.stderr)


def _stop_prior_and_acquire_start_lock(project: Path):
    """Stop prior loops and take the start lock; ``None`` means already running."""
    stdio = os.environ.get("KORU_STDIO_FORMAT", "human")
    stop_prior = _legacy_attr(
        "stop_prior_autonomous_for_auto_start",
        stop_prior_autonomous_for_auto_start,
    )
    stop_prior(project, stdio_format=stdio)
    acquire_lock = _legacy_attr(
        "try_acquire_autonomous_start_lock",
        try_acquire_autonomous_start_lock,
    )
    start_lock = acquire_lock(project)
    if start_lock is None:
        print(
            "koru auto: another autonomous loop is already starting/running for "
            f"{project}; use --allow-duplicate only if you intentionally want "
            "multiple IDE drivers.",
            file=sys.stderr,
        )
    return start_lock


def _auto_main(argv: list[str]) -> int:
    """``koru auto``: stop prior autonomous/auto loops, then start with ``--replace-existing``.

    On a brand-new project (no ``.planfile``, interactive TTY, no args) we
    suggest running ``koru wizard`` first so the user can pick a strategy
    instead of blindly entering the autonomous loop with an empty backlog.
    """
    from koru.cli import _peek_project_from_argv, _should_suggest_wizard
    help_requested = any(arg in {"-h", "--help"} for arg in argv)
    # ``koru auto up`` is equivalent to ``koru auto``; argv normalization injects
    # the ``up`` subcommand once — a redundant token here becomes a duplicate.
    # Preserve it for ``koru auto up --help`` so argparse shows the subcommand
    # options instead of the generic autonomous help.
    if argv and argv[0] == "up" and not help_requested:
        argv = argv[1:]
    if _is_maintenance_action(argv):
        run_autonomous = _legacy_attr("autonomous_main", autonomous_main)
        return run_autonomous(argv, invoked_as_auto=False)
    if help_requested:
        return autonomous_main(argv, invoked_as_auto=True)
    start_argv = _auto_start_argv(argv)
    _parse_autonomous_args(start_argv, invoked_as_auto=True)
    _enable_auto_reload_reuse_window_for_auto()
    project = _peek_project_from_argv(argv)
    if _should_suggest_wizard(argv, project):
        _print_wizard_suggestion()
    _ensure_strategy_config(project)
    start_lock = None
    if "--allow-duplicate" not in argv:
        start_lock = _stop_prior_and_acquire_start_lock(project)
        if start_lock is None:
            return 2
    run_autonomous = _legacy_attr("autonomous_main", autonomous_main)
    try:
        return run_autonomous(start_argv, invoked_as_auto=True)
    finally:
        if start_lock is not None:
            start_lock.release()
