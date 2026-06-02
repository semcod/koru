"""Startup/session phase entry points for autonomous mode."""

from __future__ import annotations

from typing import Any


def prepare_startup_context(args: Any, *, prepare_up_context: Any) -> tuple[Any | None, int]:
    """Prepare the startup/session context through a narrow phase boundary."""
    return prepare_up_context(args)
