"""Shared builders for delegated CLI parser/main shims."""

from __future__ import annotations

import argparse
from collections.abc import Callable


def build_parser_delegate(
    builder: Callable[[], argparse.ArgumentParser],
) -> Callable[[], argparse.ArgumentParser]:
    """Return a parser builder shim delegating to ``builder``."""

    def _delegate() -> argparse.ArgumentParser:
        return builder()

    return _delegate


def build_main_delegate(
    main_fn: Callable[[list[str]], int],
) -> Callable[[list[str]], int]:
    """Return an argv main shim delegating to ``main_fn``."""

    def _delegate(argv: list[str]) -> int:
        return main_fn(argv)

    return _delegate


__all__ = ["build_main_delegate", "build_parser_delegate"]
