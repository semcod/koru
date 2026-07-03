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


def _make_simple_builder(action_fn: Callable[[], ReplayAction]) -> ReplayBuilder:
    """Create a builder that ignores all arguments and calls action_fn()."""
    def builder(positional: tuple[str, ...], args: dict[str, str]) -> ReplayAction:
        return action_fn()
    return builder


def _make_url_builder(
    action_fn: Callable[[str], ReplayAction],
    default_url: str = "http://127.0.0.1:8765",
) -> ReplayBuilder:
    """Create a builder that extracts URL from args."""
    def builder(positional: tuple[str, ...], args: dict[str, str]) -> ReplayAction:
        url = args.get("url", default_url)
        return action_fn(url)
    return builder


def _make_ide_builder(action_fn: Callable[[str], ReplayAction]) -> ReplayBuilder:
    """Create a builder that extracts IDE from positional or args."""
    def builder(positional: tuple[str, ...], args: dict[str, str]) -> ReplayAction:
        ide = _first_positional_or_arg(positional, args, "ide", "auto")
        return action_fn(ide)
    return builder


def _make_ticket_builder(action_fn: Callable[[str], ReplayAction]) -> ReplayBuilder:
    """Create a builder that extracts ticket ID from positional or args."""
    def builder(positional: tuple[str, ...], args: dict[str, str]) -> ReplayAction:
        ticket_id = _first_positional_or_arg(positional, args, "ticket", "")
        return action_fn(ticket_id)
    return builder


def _make_ticket_input_builder() -> ReplayBuilder:
    """Create a builder for ticket input action."""
    def builder(positional: tuple[str, ...], args: dict[str, str]) -> ReplayAction:
        ticket_id = _first_positional_or_arg(positional, args, "ticket", "")
        return ticket_input(ticket_id, prompt=args.get("prompt", ""), note=args.get("note", ""))
    return builder


def _make_ticket_open_builder() -> ReplayBuilder:
    """Create a builder for ticket open action."""
    def builder(positional: tuple[str, ...], args: dict[str, str]) -> ReplayAction:
        ticket_id = _first_positional_or_arg(positional, args, "ticket", "")
        url = args.get("url", "http://127.0.0.1:8765")
        return ticket_open(ticket_id, url)
    return builder


def _make_autopilot_retry_builder() -> ReplayBuilder:
    """Create a builder for autopilot retry action."""
    def builder(positional: tuple[str, ...], args: dict[str, str]) -> ReplayAction:
        ticket_id = _first_positional_or_arg(positional, args, "ticket", "")
        ide = args.get("ide", "auto")
        return autopilot_retry_drive(ide, ticket_id)
    return builder


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
        return _make_simple_builder(wup_show_health)
    return _KNOWN_REPLAY_BUILDERS.get((domain, verb))


def _first_positional_or_arg(
    positional: tuple[str, ...],
    args: dict[str, str],
    key: str,
    default: str,
) -> str:
    return positional[0] if positional else args.get(key, default)


_KNOWN_REPLAY_BUILDERS: dict[tuple[str, str], ReplayBuilder] = {
    ("ide", "reload-window"): _make_ide_builder(ide_reload_window),
    ("ide", "connect-plugin"): _make_ide_builder(ide_connect_plugin),
    ("trace", "show-decisions"): _make_url_builder(trace_show_decisions),
    ("trace", "show-interfaces"): _make_url_builder(trace_show_interfaces),
    ("ticket", "input"): _make_ticket_input_builder(),
    ("ticket", "open"): _make_ticket_open_builder(),
    ("scan", "force"): _make_simple_builder(scan_force),
    ("autopilot", "retry-drive"): _make_autopilot_retry_builder(),
}


__all__ = ["ReplayBuilder", "parse_replay_dsl"]

