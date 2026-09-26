"""Terminal / IDE context detection helpers extracted from cli.py.

Contains backward-compatible shims to ``coru.ide_detection`` and
the higher-level ``_terminal_*`` helpers.
"""
from __future__ import annotations

import sys

from coru import ide_detection


def _ide_from_vscode_pid() -> str | None:
    """Backward-compatible shim; moved to ``coru.ide_detection``."""
    return ide_detection._ide_from_vscode_pid()


def _vscode_family_env_hint() -> str | None:
    """Backward-compatible shim; moved to ``coru.ide_detection``."""
    return ide_detection._vscode_family_env_hint()


def _windsurf_terminal_marker() -> bool:
    """Backward-compatible shim; moved to ``coru.ide_detection``."""
    return ide_detection._windsurf_terminal_marker()


def _terminal_ide_hint() -> str | None:
    """Best-effort IDE owning this shell."""
    ide, _source, _integrated = _terminal_shell_context()
    return ide


def _terminal_shell_context() -> tuple[str | None, str, bool]:
    """Return ``(ide, source, integrated)`` for the current shell context."""
    fallback = _terminal_shell_context_fallback()
    if fallback[2]:
        return fallback
    try:
        from koruide.ide import detect_terminal_host_context
        ctx = detect_terminal_host_context()
        return ctx.ide, ctx.source, ctx.integrated
    except Exception:
        return fallback


def _terminal_host_kind() -> str:
    return ide_detection.terminal_host_kind()


def _terminal_shell_context_fallback() -> tuple[str | None, str, bool]:
    """Provider-first shell context detection (brand name before generic vscode)."""
    return ide_detection._terminal_shell_context_fallback(
        ide_from_vscode_pid=_ide_from_vscode_pid,
        vscode_family_env_hint=_vscode_family_env_hint,
        windsurf_terminal_marker=_windsurf_terminal_marker,
    )



def _print_terminal_context(*, prefix: str = "[coru]") -> None:
    from koru.autonomy.ide_operator_guidance import terminal_kind_label

    ide, source, integrated = ide_detection.terminal_shell_context()
    kind = ide_detection.terminal_host_kind()
    if ide:
        print(
            f"{prefix} terminal: ide={ide} kind={kind} "
            f"({terminal_kind_label(kind)}) source={source}",
            file=sys.stderr,
        )
    else:
        print(f"{prefix} terminal: system shell (no IDE host detected)", file=sys.stderr)
    if integrated and ide:
        print(
            f"{prefix} lane hint: integrated {ide} terminal — "
            f"use `coru {ide} auto` unless another IDE lane is intentional",
            file=sys.stderr,
        )
