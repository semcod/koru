"""CORU query and command handlers."""

from dsl2coru.handlers.command import run_command
from dsl2coru.handlers.query import run_query
from dsl2coru.handlers.ui import run_ui_command

__all__ = ["run_command", "run_query", "run_ui_command"]
