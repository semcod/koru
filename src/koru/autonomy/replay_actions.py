"""Replay action DSL for Koru autonomous cycle.

Every operator-facing action is a ``ReplayAction`` — a structured record
that can be rendered as a single-line shell command::

    koru replay 'ide reload-window antigravity'
    koru replay 'trace show-decisions'
    koru replay 'ticket input PLF-013 --prompt "fix tests"'

The DSL grammar is intentionally simple::

    <domain> <verb> [positional...] [--key=value ...]

Actions carry an optional ``validate_cmd`` that checks whether the action
had the intended effect — this enables regression detection.
"""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReplayAction:
    """One actionable step the operator (or automation) can execute."""

    domain: str
    verb: str
    args: dict[str, str] = field(default_factory=dict)
    positional: tuple[str, ...] = ()
    label: str = ""
    replayable: bool = True
    validate_cmd: str | None = None
    safe: bool = True
    requires_active_window: bool = False

    @property
    def key(self) -> str:
        return f"{self.domain}.{self.verb}"

    def to_dsl(self) -> str:
        """Render the DSL token (without ``koru replay`` prefix)."""
        parts = [self.domain, self.verb, *self.positional]
        for key, value in sorted(self.args.items()):
            parts.append(f"--{key}={shlex.quote(value)}")
        return " ".join(parts)

    def to_shell(self) -> str:
        """Render the full shell command: ``koru replay '...'``."""
        return f"koru replay {shlex.quote(self.to_dsl())}"


@dataclass
class ReplayResult:
    """Outcome of executing a replay action."""

    ok: bool
    output: str = ""
    returncode: int = 0
    action: ReplayAction | None = None


@dataclass
class ValidationResult:
    """Outcome of validating a replay action's effect."""

    passed: bool
    reason: str = ""
    action: ReplayAction | None = None
    regression_point: str | None = None


# ---------------------------------------------------------------------------
# DSL parsing
# ---------------------------------------------------------------------------


def parse_replay_dsl(text: str) -> ReplayAction:
    """Parse a DSL string into a ``ReplayAction``.

    >>> parse_replay_dsl("ide reload-window antigravity")
    ReplayAction(domain='ide', verb='reload-window', positional=('antigravity',), ...)
    """
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


ReplayBuilder = Callable[[tuple[str, ...], dict[str, str]], ReplayAction]


def _replay_action_builder(domain: str, verb: str) -> ReplayBuilder | None:
    if domain == "wup" and verb in {"show-health", "show-track"}:
        return _build_wup_health_action
    return _KNOWN_REPLAY_BUILDERS.get((domain, verb))


def _first_positional_or_arg(positional: tuple[str, ...], args: dict[str, str], key: str, default: str) -> str:
    return positional[0] if positional else args.get(key, default)


def _build_ide_reload_action(positional: tuple[str, ...], args: dict[str, str]) -> ReplayAction:
    return ide_reload_window(_first_positional_or_arg(positional, args, "ide", "auto"))


def _build_ide_connect_action(positional: tuple[str, ...], args: dict[str, str]) -> ReplayAction:
    return ide_connect_plugin(_first_positional_or_arg(positional, args, "ide", "auto"))


def _build_trace_decisions_action(_positional: tuple[str, ...], args: dict[str, str]) -> ReplayAction:
    return trace_show_decisions(args.get("url", "http://127.0.0.1:8765"))


def _build_trace_interfaces_action(_positional: tuple[str, ...], args: dict[str, str]) -> ReplayAction:
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


def _build_autopilot_retry_action(positional: tuple[str, ...], args: dict[str, str]) -> ReplayAction:
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


# ---------------------------------------------------------------------------
# Action builders — factory functions for known actions
# ---------------------------------------------------------------------------


def ide_reload_window(ide: str) -> ReplayAction:
    """IDE: Developer → Reload Window."""
    return ReplayAction(
        domain="ide",
        verb="reload-window",
        positional=(ide,),
        label=f"Reload {ide} IDE window",
        replayable=False,  # requires manual IDE action
        validate_cmd=f"koru ide doctor --ide {shlex.quote(ide)}",
        safe=False,
        requires_active_window=True,
    )


def ide_connect_plugin(ide: str) -> ReplayAction:
    """IDE: koru → Connect autopilot daemon."""
    return ReplayAction(
        domain="ide",
        verb="connect-plugin",
        positional=(ide,),
        label=f"Connect autopilot plugin for {ide}",
        replayable=False,
        validate_cmd=f"koru autopilot status --ide {shlex.quote(ide)}",
        safe=False,
        requires_active_window=True,
    )


def trace_show_decisions(base_url: str = "http://127.0.0.1:8765") -> ReplayAction:
    """Show the autonomy decision trace via dashboard API."""
    cmd = f"curl -s {base_url}/api/autonomy/trace | jq .decisions"
    return ReplayAction(
        domain="trace",
        verb="show-decisions",
        label="Show autonomy decision trace",
        args={"url": base_url},
        validate_cmd=cmd,
    )


def trace_show_interfaces(base_url: str = "http://127.0.0.1:8765") -> ReplayAction:
    """Show interface families and blockers via dashboard API."""
    cmd = f"curl -s {base_url}/api/interfaces | jq '.families, .blockers'"
    return ReplayAction(
        domain="trace",
        verb="show-interfaces",
        label="Show interface families and blockers",
        args={"url": base_url},
        validate_cmd=cmd,
    )


def ticket_input(ticket_id: str, prompt: str = "", note: str = "") -> ReplayAction:
    """Mark a planfile ticket as needing input."""
    args: dict[str, str] = {}
    if prompt:
        args["prompt"] = prompt
    if note:
        args["note"] = note
    return ReplayAction(
        domain="ticket",
        verb="input",
        positional=(ticket_id,),
        args=args,
        label=f"Mark {ticket_id} as needing input",
    )


def ticket_open(ticket_id: str, base_url: str = "http://127.0.0.1:8765") -> ReplayAction:
    """Open a ticket in the dashboard."""
    return ReplayAction(
        domain="ticket",
        verb="open",
        positional=(ticket_id,),
        args={"url": base_url},
        label=f"Open {ticket_id} in dashboard",
    )


def scan_force() -> ReplayAction:
    """Force a fresh koru scan (clear project cache first)."""
    return ReplayAction(
        domain="scan",
        verb="force",
        label="Force fresh project scan",
        validate_cmd="ls -d project/ 2>/dev/null && echo 'project dir exists' || echo 'clean'",
    )


def wup_show_health() -> ReplayAction:
    """Show WUP service health."""
    return ReplayAction(
        domain="wup",
        verb="show-health",
        label="Show WUP service health",
        validate_cmd="cat .wup/service-health.json 2>/dev/null | jq . || echo 'no health file'",
    )


def autopilot_retry_drive(ide: str, ticket_id: str) -> ReplayAction:
    """Retry an autopilot drive for a specific ticket."""
    return ReplayAction(
        domain="autopilot",
        verb="retry-drive",
        positional=(ticket_id,),
        args={"ide": ide},
        label=f"Retry autopilot drive for {ticket_id}",
        safe=False,
    )


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


_REPLAY_EXECUTORS: dict[str, Any] = {}


def _register_executor(domain: str, verb: str):
    """Decorator to register a replay action executor."""

    def decorator(func):
        _REPLAY_EXECUTORS[f"{domain}.{verb}"] = func
        return func

    return decorator


@_register_executor("trace", "show-decisions")
def _exec_trace_show_decisions(action: ReplayAction, *, project: Path) -> ReplayResult:
    url = action.args.get("url", "http://127.0.0.1:8765")
    result = subprocess.run(
        ["bash", "-lc", f"curl -s {url}/api/autonomy/trace | jq .decisions"],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )
    return ReplayResult(ok=result.returncode == 0, output=result.stdout, returncode=result.returncode, action=action)


@_register_executor("trace", "show-interfaces")
def _exec_trace_show_interfaces(action: ReplayAction, *, project: Path) -> ReplayResult:
    url = action.args.get("url", "http://127.0.0.1:8765")
    result = subprocess.run(
        ["bash", "-lc", f"curl -s {url}/api/interfaces | jq '.families, .blockers'"],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )
    return ReplayResult(ok=result.returncode == 0, output=result.stdout, returncode=result.returncode, action=action)


@_register_executor("ticket", "input")
def _exec_ticket_input(action: ReplayAction, *, project: Path) -> ReplayResult:
    ticket_id = action.positional[0] if action.positional else ""
    if not ticket_id:
        return ReplayResult(ok=False, output="ticket_id required", action=action)
    cmd_parts = ["planfile", "ticket", "input", ticket_id]
    prompt = action.args.get("prompt", "<input needed>")
    note = action.args.get("note", "<what was verified>")
    cmd_parts.extend(["--prompt", prompt, "--note", note])
    result = subprocess.run(cmd_parts, cwd=project, capture_output=True, text=True, check=False)
    return ReplayResult(ok=result.returncode == 0, output=result.stdout, returncode=result.returncode, action=action)


@_register_executor("ticket", "open")
def _exec_ticket_open(action: ReplayAction, *, project: Path) -> ReplayResult:
    ticket_id = action.positional[0] if action.positional else ""
    raw_url = action.args.get("url", "http://127.0.0.1:8765")
    if not ticket_id:
        return ReplayResult(ok=False, output=raw_url, returncode=2, action=action)
    if "tab=tickets" in raw_url:
        url = f"{raw_url.split('#', 1)[0]}#{ticket_id}"
    else:
        url = f"{raw_url.rstrip('/')}/?tab=tickets#{ticket_id}"
    return ReplayResult(ok=bool(ticket_id), output=url, returncode=0 if ticket_id else 2, action=action)


@_register_executor("scan", "force")
def _exec_scan_force(action: ReplayAction, *, project: Path) -> ReplayResult:
    result = subprocess.run(
        ["bash", "-lc", "rm -rf project/ && KORU_SCAN_FORCE_RESCAN=1 koru auto --max-cycles 1"],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )
    return ReplayResult(ok=result.returncode == 0, output=result.stdout, returncode=result.returncode, action=action)


@_register_executor("autopilot", "retry-drive")
def _exec_autopilot_retry_drive(action: ReplayAction, *, project: Path) -> ReplayResult:
    ticket_id = action.positional[0] if action.positional else ""
    if not ticket_id:
        return ReplayResult(ok=False, output="ticket_id required", returncode=2, action=action)
    ide = action.args.get("ide", "auto")
    result = subprocess.run(
        ["koru", "autopilot", "drive", "--ide", ide, "--require-plugin", "-p", f"continue with {ticket_id}"],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )
    return ReplayResult(ok=result.returncode == 0, output=result.stdout, returncode=result.returncode, action=action)


def execute_replay_action(action: ReplayAction, *, project: Path) -> ReplayResult:
    """Execute a replay action. Returns result with ok/output/returncode."""
    executor = _REPLAY_EXECUTORS.get(action.key)
    if executor is None:
        if not action.replayable:
            return ReplayResult(
                ok=False,
                output=f"action {action.key} requires manual intervention: {action.label}",
                action=action,
            )
        return ReplayResult(
            ok=False,
            output=f"no executor registered for {action.key}",
            action=action,
        )
    return executor(action, project=project)


def validate_replay_action(action: ReplayAction, *, project: Path) -> ValidationResult:
    """Check if a replay action's effect was achieved.

    Uses the action's ``validate_cmd`` to verify the outcome.
    Returns a ``ValidationResult`` with pass/fail and reason.
    """
    if not action.validate_cmd:
        return ValidationResult(
            passed=True,
            reason="no validation command defined",
            action=action,
        )
    result = subprocess.run(
        ["bash", "-lc", action.validate_cmd],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return ValidationResult(
            passed=True,
            reason=result.stdout.strip()[:200],
            action=action,
        )
    return ValidationResult(
        passed=False,
        reason=result.stderr.strip()[:200] or result.stdout.strip()[:200] or "validation failed",
        action=action,
        regression_point=action.key,
    )


# ---------------------------------------------------------------------------
# Quick-action conversion: bridge from legacy format
# ---------------------------------------------------------------------------


def quick_action_to_replay(
    action_text: str,
    *,
    autopilot_ide: str = "",
    waiting_ticket: str = "",
    base_url: str = "http://127.0.0.1:8765",
) -> ReplayAction | None:
    """Convert a legacy ``[label] `cmd``` quick action to a ReplayAction.

    Returns ``None`` if the text doesn't map to a known replay action.
    """
    label, body = _split_quick_action_text(action_text)
    label_lower = label.lower()
    action = _quick_static_action(label_lower, base_url=base_url, autopilot_ide=autopilot_ide)
    if action is not None:
        return action
    return _quick_ticket_action(
        label_lower,
        body,
        autopilot_ide=autopilot_ide,
        waiting_ticket=waiting_ticket,
        base_url=base_url,
    )


def _quick_static_action(
    label_lower: str,
    *,
    base_url: str,
    autopilot_ide: str,
) -> ReplayAction | None:
    if label_lower == "show decision trace":
        return trace_show_decisions(base_url)
    if label_lower == "show interfaces":
        return trace_show_interfaces(base_url)
    if label_lower == "reconnect plugin":
        ide = autopilot_ide or "auto"
        return ide_connect_plugin(ide)
    if label_lower in ("force fresh scan", "force scan"):
        return scan_force()
    if label_lower == "show wup track":
        return wup_show_health()
    return None


def _quick_ticket_action(
    label_lower: str,
    body: str,
    *,
    autopilot_ide: str,
    waiting_ticket: str,
    base_url: str,
) -> ReplayAction | None:
    if not waiting_ticket:
        return None
    if label_lower == "mark ticket input":
        return ticket_input(waiting_ticket)
    if label_lower == "open ticket":
        url = body.split("#", 1)[0].strip() if body.startswith(("http://", "https://")) else base_url
        return ticket_open(waiting_ticket, url)
    if label_lower == "retry submit" and waiting_ticket:
        return autopilot_retry_drive(autopilot_ide or "auto", waiting_ticket)
    return None


def _split_quick_action_text(text: str) -> tuple[str, str]:
    """Split ``[label] body`` into (label, body)."""
    text = text.strip()
    if text.startswith("[") and "]" in text:
        label, body = text[1:].split("]", 1)
        return label.strip(), body.strip()
    return "", text


__all__ = [
    "ReplayAction",
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
