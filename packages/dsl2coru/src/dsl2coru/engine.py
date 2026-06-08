"""Backward-compatible shim — prefer dsl2coru.bus."""

from dsl2coru.bus import dispatch, dispatch_text, execute_dsl, execute_dsl_line
from dsl2coru.result import DslResult

__all__ = ["DslResult", "dispatch", "dispatch_text", "execute_dsl", "execute_dsl_line"]
