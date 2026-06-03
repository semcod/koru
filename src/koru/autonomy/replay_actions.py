"""Replay action DSL for Koru autonomous cycle.

Every operator-facing action is a ``ReplayAction`` — a structured record
that can be rendered as a single-line shell command::

    koru replay 'ide reload-window antigravity'
    koru replay 'trace show-decisions'
    koru replay 'ticket input PLF-013 --prompt "fix tests"'

The implementation lives in focused modules; this module preserves the
original public import surface.
"""

from __future__ import annotations

from koru.autonomy.replay_builders import (
    autopilot_retry_drive,
    ide_connect_plugin,
    ide_reload_window,
    scan_force,
    ticket_input,
    ticket_open,
    trace_show_decisions,
    trace_show_interfaces,
    wup_show_health,
)
from koru.autonomy.replay_execution import execute_replay_action, validate_replay_action
from koru.autonomy.replay_handlers import ReplayCommandHandlers, ReplayQueryHandlers
from koru.autonomy.replay_parser import ReplayBuilder, parse_replay_dsl
from koru.autonomy.replay_quick_actions import quick_action_to_replay
from koru.autonomy.replay_types import ReplayAction, ReplayResult, ValidationResult

__all__ = [
    "ReplayAction",
    "ReplayBuilder",
    "ReplayCommandHandlers",
    "ReplayQueryHandlers",
    "ReplayResult",
    "ValidationResult",
    "autopilot_retry_drive",
    "execute_replay_action",
    "ide_connect_plugin",
    "ide_reload_window",
    "parse_replay_dsl",
    "quick_action_to_replay",
    "scan_force",
    "ticket_input",
    "ticket_open",
    "trace_show_decisions",
    "trace_show_interfaces",
    "validate_replay_action",
    "wup_show_health",
]
