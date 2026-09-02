"""Compatibility read-only handlers delegated to ``coru.cli``."""

from dsl2koru.handlers.command import run_command as run_query

__all__ = ["run_query"]
