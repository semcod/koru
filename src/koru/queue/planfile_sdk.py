"""Typed Planfile lifecycle gateway with a bounded CLI compatibility path.

The SDK performs a mutation exactly once. During the compatibility release a
successful SDK transition can be verified with a read-only ``ticket show``
through the old CLI transport; Koru never executes the same mutation twice.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from koru.control_commands import control_command, emit_control_command
from koru.queue.ticket import planfile_command
from koru.queue.types import CommandResult

_logger = logging.getLogger(__name__)

LifecycleOperation = Literal[
    "claim",
    "start",
    "complete",
    "fail",
    "ready",
    "block",
    "note",
]
ParityStatus = Literal["disabled", "verified", "mismatch", "unavailable"]


@dataclass(frozen=True)
class LifecycleRequest:
    """A CLI-independent lifecycle request accepted by PlanfileClient."""

    operation: LifecycleOperation
    ticket_id: str
    kwargs: dict[str, Any]


@dataclass(frozen=True)
class PlanfileLifecycleCommandResult:
    """Subprocess-compatible result enriched with the typed SDK outcome."""

    returncode: int
    stdout: str
    stderr: str
    transition_code: str
    transition_attempts: int
    transport: Literal["sdk"] = "sdk"
    parity: ParityStatus = "disabled"


def _option_pairs(tokens: Sequence[str]) -> dict[str, str] | None:
    if len(tokens) % 2:
        return None
    result: dict[str, str] = {}
    for index in range(0, len(tokens), 2):
        flag = str(tokens[index])
        if not flag.startswith("-") or flag in result:
            return None
        result[flag] = str(tokens[index + 1])
    return result


# Commands whose kwargs are a plain flag→snake_case map once the option set is
# validated. `done` and `complete` are the same operation. Kept as data so the
# dispatcher stays flat instead of one if-branch per command.
_MAPPED_LIFECYCLE_COMMANDS: dict[str, tuple[str, frozenset[str]]] = {
    "start": ("start", frozenset({"--assigned-to", "--reason", "--actor"})),
    "done": ("complete", frozenset({"--note", "--reason", "--actor"})),
    "complete": ("complete", frozenset({"--note", "--reason", "--actor"})),
    "block": ("block", frozenset({"--reason", "--note", "--actor"})),
}


def _snake_kwargs(options: dict[str, str]) -> dict[str, Any]:
    """Map ``--assigned-to`` → ``assigned_to`` etc. for the plain commands."""
    return {key.removeprefix("--").replace("-", "_"): value for key, value in options.items()}


def _mapped_request(
    operation: str, ticket_id: str, options: dict[str, str], allowed: frozenset[str]
) -> LifecycleRequest | None:
    if set(options) - allowed:
        return None
    return LifecycleRequest(operation, ticket_id, _snake_kwargs(options))


def _parse_claim(ticket_id: str, options: dict[str, str]) -> LifecycleRequest | None:
    if set(options) - {"--assigned-to", "--lease-seconds"}:
        return None
    kwargs: dict[str, Any] = {}
    if assigned_to := options.get("--assigned-to"):
        kwargs["assigned_to"] = assigned_to
    if lease_raw := options.get("--lease-seconds"):
        try:
            kwargs["lease_seconds"] = int(lease_raw)
        except ValueError:
            return None
    return LifecycleRequest("claim", ticket_id, kwargs)


def _parse_fail(ticket_id: str, options: dict[str, str]) -> LifecycleRequest | None:
    if set(options) - {"--error", "-e", "--reason", "--actor"}:
        return None
    error = options.get("--error") or options.get("-e")
    if not error or ("--error" in options and "-e" in options):
        return None
    kwargs: dict[str, Any] = {"error": error}
    for flag in ("--reason", "--actor"):
        if flag in options:
            kwargs[flag.removeprefix("--")] = options[flag]
    return LifecycleRequest("fail", ticket_id, kwargs)


def _parse_ready(ticket_id: str, options: dict[str, str]) -> LifecycleRequest | None:
    if set(options) - {"--note", "-n", "--reason", "--actor"}:
        return None
    if "--note" in options and "-n" in options:
        return None
    kwargs: dict[str, Any] = {}
    if note := options.get("--note") or options.get("-n"):
        kwargs["note"] = note
    for flag in ("--reason", "--actor"):
        if flag in options:
            kwargs[flag.removeprefix("--")] = options[flag]
    return LifecycleRequest("ready", ticket_id, kwargs)


def parse_lifecycle_request(args: Sequence[str]) -> LifecycleRequest | None:
    """Parse the supported lifecycle subset; return ``None`` for CLI-only commands.

    The per-command validators live in ``_parse_*`` helpers and
    ``_MAPPED_LIFECYCLE_COMMANDS``; this stays a flat dispatcher.
    """

    tokens = [str(token) for token in args]
    if len(tokens) < 3 or tokens[0] != "ticket":
        return None
    command, ticket_id = tokens[1], tokens[2].strip()
    if not ticket_id:
        return None
    options = _option_pairs(tokens[3:])
    if options is None:
        return None

    if command == "claim":
        return _parse_claim(ticket_id, options)
    if mapped := _MAPPED_LIFECYCLE_COMMANDS.get(command):
        operation, allowed = mapped
        return _mapped_request(operation, ticket_id, options, allowed)
    if command == "fail":
        return _parse_fail(ticket_id, options)
    if command == "ready":
        return _parse_ready(ticket_id, options)
    if command == "update" and set(options) in ({"--note"}, {"-n"}):
        return LifecycleRequest("note", ticket_id, {"note": next(iter(options.values()))})
    return None


def _explicit_sdk_preference() -> bool | None:
    value = os.environ.get("KORU_PLANFILE_SDK", "").strip().lower()
    if value in {"1", "true", "yes", "on", "sdk"}:
        return True
    if value in {"0", "false", "no", "off", "cli"}:
        return False
    return None


def _default_sdk_preference(runner: Callable[..., CommandResult]) -> bool:
    explicit = _explicit_sdk_preference()
    if explicit is not None:
        return explicit
    # Custom runners are a deliberate test/embedding seam. Keep their CLI
    # semantics unless the caller explicitly opts in to SDK mode.
    from koru.queue.runners import run_process

    return runner is run_process


def _verify_enabled() -> bool:
    value = os.environ.get("KORU_PLANFILE_SDK_VERIFY", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def _load_client_factory() -> Callable[..., Any] | None:
    try:
        from planfile.client import PlanfileClient
    except (ImportError, ModuleNotFoundError):
        return None
    return PlanfileClient


def _dispatch(client: Any, request: LifecycleRequest) -> Any:
    method = getattr(client, request.operation)
    if request.operation == "note":
        return method(request.ticket_id, request.kwargs["note"])
    return method(request.ticket_id, **request.kwargs)


def _emit_sdk_control(project: Path, request: LifecycleRequest) -> None:
    """Preserve the control-command audit previously emitted by the CLI runner."""

    actor = str(request.kwargs.get("actor") or request.kwargs.get("assigned_to") or "koru")
    emit_control_command(
        project,
        control_command(
            corr=f"planfile-sdk-{time.monotonic_ns():x}",
            surface="local_sdk",
            interface_id="planfile_client_lifecycle",
            transport="python_sdk",
            operation=f"ticket.{request.operation}",
            args={
                "ticket_id": request.ticket_id,
                # Do not put note/reason content into the replay log. The
                # ticket event contains the authoritative transition result.
                "argument_names": sorted(request.kwargs),
            },
            actor=actor,
            target=request.ticket_id,
            replayable=False,
            authority="high",
            verification="typed_result_and_cli_readback",
        ),
    )


def _transition_result(result: Any, *, parity: ParityStatus) -> PlanfileLifecycleCommandResult:
    code = str(getattr(result, "code", "store_error"))
    ticket = getattr(result, "ticket", None)
    error = str(getattr(result, "error", "") or "")
    attempts = int(getattr(result, "attempts", 1) or 1)
    return PlanfileLifecycleCommandResult(
        returncode=0 if code == "ok" else 1,
        stdout=json.dumps(ticket, ensure_ascii=False, sort_keys=True) if ticket is not None else "",
        stderr=error,
        transition_code=code,
        transition_attempts=attempts,
        parity=parity,
    )


def _projection(operation: LifecycleOperation, ticket: dict[str, Any]) -> dict[str, Any]:
    execution = ticket.get("execution") if isinstance(ticket.get("execution"), dict) else {}
    outputs = ticket.get("outputs") if isinstance(ticket.get("outputs"), dict) else {}
    base: dict[str, Any] = {"id": ticket.get("id"), "status": ticket.get("status")}
    if operation == "claim":
        base["execution"] = {
            "assigned_to": execution.get("assigned_to"),
            "state": execution.get("state"),
        }
    elif operation == "start":
        base["execution"] = {
            "assigned_to": execution.get("assigned_to"),
            "state": execution.get("state"),
        }
    elif operation == "fail":
        base["execution"] = {
            "state": execution.get("state"),
            "attempt": execution.get("attempt"),
            "last_error": execution.get("last_error"),
        }
    elif operation == "ready":
        base["execution"] = {
            "state": execution.get("state"),
            "attempt": execution.get("attempt"),
            "assigned_to": execution.get("assigned_to"),
        }
    elif operation in {"complete", "block"}:
        base["execution"] = {"state": execution.get("state")}
    elif operation == "note":
        base["notes"] = list(outputs.get("notes") or [])
    return base


def _readback_parity(
    project: Path,
    request: LifecycleRequest,
    sdk_ticket: dict[str, Any] | None,
    runner: Callable[[Sequence[str], Path], CommandResult],
) -> ParityStatus:
    if sdk_ticket is None:
        return "unavailable"
    readback = planfile_command(
        project,
        ["ticket", "show", request.ticket_id, "--format", "json"],
        runner=runner,
    )
    if readback.returncode != 0:
        return "unavailable"
    try:
        payload = json.loads((readback.stdout or "").strip())
    except (json.JSONDecodeError, TypeError):
        return "unavailable"
    if not isinstance(payload, dict):
        return "unavailable"
    if _projection(request.operation, sdk_ticket) == _projection(request.operation, payload):
        return "verified"
    _logger.warning(
        "planfile lifecycle parity mismatch operation=%s ticket=%s sdk=%s cli=%s",
        request.operation,
        request.ticket_id,
        _projection(request.operation, sdk_ticket),
        _projection(request.operation, payload),
    )
    return "mismatch"


def planfile_lifecycle_command(
    project: Path,
    args: Sequence[str],
    runner: Callable[[Sequence[str], Path], CommandResult],
    *,
    prefer_sdk: bool | None = None,
    verify: bool | None = None,
    client_factory: Callable[..., Any] | None = None,
) -> CommandResult:
    """Execute a supported lifecycle mutation through PlanfileClient.

    Unsupported commands, unavailable SDKs and custom runners retain the old
    CLI path. A typed SDK failure is returned directly and is never retried as
    another CLI mutation.
    """

    request = parse_lifecycle_request(args)
    should_use_sdk = _default_sdk_preference(runner) if prefer_sdk is None else prefer_sdk
    if request is None or not should_use_sdk:
        return planfile_command(project, args, runner=runner)

    factory = client_factory or _load_client_factory()
    if factory is None:
        return planfile_command(project, args, runner=runner)
    try:
        client = factory(str(project.resolve()))
        # Planfile <0.1.118 has the CLI lifecycle commands but its typed client
        # does not expose fail/ready yet. Fall back before emitting an SDK
        # control event so the mutation still happens exactly once.
        if not callable(getattr(client, request.operation, None)):
            return planfile_command(project, args, runner=runner)
        _emit_sdk_control(project.resolve(), request)
        transition = _dispatch(client, request)
    except (ImportError, ModuleNotFoundError):
        return planfile_command(project, args, runner=runner)
    except (OSError, ValueError) as exc:
        return PlanfileLifecycleCommandResult(
            returncode=1,
            stdout="",
            stderr=str(exc),
            transition_code="store_error",
            transition_attempts=1,
        )

    parity: ParityStatus = "disabled"
    if bool(_verify_enabled() if verify is None else verify) and str(getattr(transition, "code", "")) == "ok":
        parity = _readback_parity(
            project.resolve(),
            request,
            getattr(transition, "ticket", None),
            runner,
        )
    return _transition_result(transition, parity=parity)


__all__ = [
    "LifecycleRequest",
    "PlanfileLifecycleCommandResult",
    "parse_lifecycle_request",
    "planfile_lifecycle_command",
]
