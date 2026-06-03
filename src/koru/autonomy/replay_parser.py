"""Replay DSL parsing."""

from __future__ import annotations

import shlex
from collections.abc import Callable

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
from koru.autonomy.replay_types import ReplayAction

ReplayBuilder = Callable[[tuple[str, ...], dict[str, str]], ReplayAction]


def parse_replay_dsl(text: str) -> ReplayAction:
    """Parse a DSL string into a ``ReplayAction``."""
    tokens = shlex.split(text.strip())
    if len(tokens) < 2:
        raise ValueError(f"replay DSL requires at least <domain> <verb>: {text!r}")

    domain = tokens[0]
    verb = tokens[1]
    positional: list[str] = []
    args: dict[str, str] = {}

    for token in tokens[2:]:
        if token.startswith("--") and "=" in token:
            key, _, value = token[2:].partition("=")
            args[key] = value
        else:
            positional.append(token)

    return _known_replay_action(domain, verb, tuple(positional), args)


def _known_replay_action(
    domain: str,
    verb: str,
    positional: tuple[str, ...],
    args: dict[str, str],
) -> ReplayAction:
    builder = _replay_action_builder(domain, verb)
    if builder is not None:
        return builder(positional, args)
    return ReplayAction(
        domain=domain,
        verb=verb,
        positional=positional,
        args=args,
    )


def _replay_action_builder(domain: str, verb: str) -> ReplayBuilder | None:
    if domain == "wup" and verb in {"show-health", "show-track"}:
        return _build_wup_health_action
    return _KNOWN_REPLAY_BUILDERS.get((domain, verb))


def _first_positional_or_arg(
    positional: tuple[str, ...],
    args: dict[str, str],
    key: str,
    default: str,
) -> str:
    return positional[0] if positional else args.get(key, default)


def _build_ide_reload_action(positional: tuple[str, ...], args: dict[str, str]) -> ReplayAction:
    return ide_reload_window(_first_positional_or_arg(positional, args, "ide", "auto"))


def _build_ide_connect_action(positional: tuple[str, ...], args: dict[str, str]) -> ReplayAction:
    return ide_connect_plugin(_first_positional_or_arg(positional, args, "ide", "auto"))


def _build_trace_decisions_action(
    _positional: tuple[str, ...],
    args: dict[str, str],
) -> ReplayAction:
    return trace_show_decisions(args.get("url", "http://127.0.0.1:8765"))


def _build_trace_interfaces_action(
    _positional: tuple[str, ...],
    args: dict[str, str],
) -> ReplayAction:
    return trace_show_interfaces(args.get("url", "http://127.0.0.1:8765"))


def _build_ticket_input_action(positional: tuple[str, ...], args: dict[str, str]) -> ReplayAction:
    ticket_id = _first_positional_or_arg(positional, args, "ticket", "")
    return ticket_input(ticket_id, prompt=args.get("prompt", ""), note=args.get("note", ""))


def _build_ticket_open_action(positional: tuple[str, ...], args: dict[str, str]) -> ReplayAction:
    ticket_id = _first_positional_or_arg(positional, args, "ticket", "")
    return ticket_open(ticket_id, args.get("url", "http://127.0.0.1:8765"))


def _build_scan_force_action(_positional: tuple[str, ...], _args: dict[str, str]) -> ReplayAction:
    return scan_force()


def _build_wup_health_action(_positional: tuple[str, ...], _args: dict[str, str]) -> ReplayAction:
    return wup_show_health()


def _build_autopilot_retry_action(
    positional: tuple[str, ...],
    args: dict[str, str],
) -> ReplayAction:
    ticket_id = _first_positional_or_arg(positional, args, "ticket", "")
    return autopilot_retry_drive(args.get("ide", "auto"), ticket_id)


_KNOWN_REPLAY_BUILDERS: dict[tuple[str, str], ReplayBuilder] = {
    ("ide", "reload-window"): _build_ide_reload_action,
    ("ide", "connect-plugin"): _build_ide_connect_action,
    ("trace", "show-decisions"): _build_trace_decisions_action,
    ("trace", "show-interfaces"): _build_trace_interfaces_action,
    ("ticket", "input"): _build_ticket_input_action,
    ("ticket", "open"): _build_ticket_open_action,
    ("scan", "force"): _build_scan_force_action,
    ("autopilot", "retry-drive"): _build_autopilot_retry_action,
}


__all__ = ["ReplayBuilder", "parse_replay_dsl"]
