"""Backward-compatible shim — prefer dsl2koru.bus."""

from dsl2koru.bus import dispatch, execute_dsl, execute_dsl_line
from dsl2koru.result import DslResult

__all__ = ["DslResult", "dispatch", "execute_dsl", "execute_dsl_line"]
