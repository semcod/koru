"""Backward compatibility shim for koru.autonomy.operator.operator_processes module migration."""

import argparse
import sys
from pathlib import Path

from koru.autonomy.operator import operator_processes as _module_impl  # noqa: F401
from koru.autonomy.operator.operator_processes import *  # noqa: F401, F403

_current_module = sys.modules[__name__]
for attr in dir(_module_impl):
    if not attr.startswith("__"):
        if not hasattr(_current_module, attr):
            setattr(_current_module, attr, getattr(_module_impl, attr))

# Wrap functions so that test monkeypatching through the shim works properly
# The key is to look up helper functions from this module's globals() at runtime,
# so patches applied to this shim affect the behavior


def stop_prior_autonomous_for_auto_start(
    project: Path,
    *,
    stdio_format: str = "human",
) -> None:
    """Stop prior autonomous processes. Wrapper for test monkeypatching support."""
    # Look up functions from this module so test monkeypatches work
    project_resolved = project.resolve()
    find_fn = globals()['_find_existing_autonomous_processes']
    find_wup_fn = globals()['_find_existing_wup_processes']
    terminate_fn = globals()['_terminate_existing_processes']
    
    existing = [
        *(
            _module_impl._as_managed(proc)
            for proc in find_fn(project_resolved, any_project=True)
        ),
        *find_wup_fn(project_resolved),
    ]
    if not existing:
        return
    _module_impl._stdio_info(
        f"koru auto: stopping {len(existing)} prior managed process(es) "
        "(koru autonomous/auto, wup watch)",
        fmt=stdio_format,
    )
    terminate_fn(existing, stdio_format=stdio_format)


def guard_existing_autonomous_processes(args: argparse.Namespace, project: Path) -> int:
    """Guard against duplicate processes. Wrapper for test monkeypatching support."""
    if args.allow_duplicate:
        return 0
    find_fn = globals()['_find_existing_autonomous_processes']
    find_wup_fn = globals()['_find_existing_wup_processes']
    terminate_fn = globals()['_terminate_existing_processes']
    
    existing = [
        *(_module_impl._as_managed(proc) for proc in find_fn(project)),
        *find_wup_fn(project),
    ]
    if not existing:
        return 0
    if args.replace_existing:
        if getattr(args, "replace_existing_global", False):
            existing = [
                *(
                    _module_impl._as_managed(proc)
                    for proc in find_fn(project, any_project=True)
                ),
                *find_wup_fn(project),
            ]
        terminate_fn(existing, stdio_format=args.emit_events)
        return 0
    if args.emit_events == "human" and sys.stdin.isatty():
        if _module_impl._confirm_replace_existing(existing):
            terminate_fn(existing, stdio_format=args.emit_events)
            return 0
        _module_impl._stdio_info(
            "koru autonomous: keeping existing process(es); not starting a duplicate. "
            "Use --allow-duplicate to override.",
            fmt=args.emit_events,
        )
        return 2
    _module_impl._stdio_info(
        "koru autonomous: another managed process is already running for this project; "
        "use --replace-existing to stop it first or --allow-duplicate to run anyway.",
        fmt=args.emit_events,
    )
    for proc in existing:
        _module_impl._stdio_info(
            f"  existing {proc.kind} pid={proc.pid}: {proc.command}",
            fmt=args.emit_events,
        )
    return 2
