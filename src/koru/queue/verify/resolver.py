"""Deciding which gate a ticket gets, in one place and one order.

Precedence, strongest claim first:

1. ``inputs.verify_profile`` — a named profile. Errors here refuse; they never
   fall through, because a typo'd profile falling back to "no gate" is the
   silent downgrade this package exists to prevent.
2. The legacy chain, unchanged from before profiles existed: raw
   ``inputs.verify_command``, a command-shaped acceptance criterion,
   ``KORU_QUEUE_VERIFY_COMMAND``, then koru.yaml's before-complete gate.

When the project sets ``queue.verify_require_profile: true``, rung 2 tightens:
a raw command is honoured only if allowlisted (the ``custom-readonly`` path),
and anything else refuses. That flag is the migration lever — flip it once
every live ticket names a profile.
"""

from __future__ import annotations

from pathlib import Path

from koru.queue.verify.executor import render_profile_command
from koru.queue.verify.profiles import CUSTOM_READONLY
from koru.queue.verify.registry import VerifyRegistry, load_registry
from koru.queue.verify.result import VerifyResolution


def resolve_verify(
    project: Path,
    ticket: dict,
    targets: tuple[str, ...] = (),
    registry: VerifyRegistry | None = None,
) -> VerifyResolution:
    """The gate this ticket's patch must pass, or why none could be resolved."""
    registry = registry if registry is not None else load_registry(project)

    name = str((ticket.get("inputs") or {}).get("verify_profile") or "").strip()
    if name:
        return _resolve_profile(registry, name, ticket, targets)

    from koru.queue.verify.legacy import resolve_legacy_verify_command

    command = resolve_legacy_verify_command(project, ticket)
    if not _profiles_required(project):
        if not command:
            return VerifyResolution(source="none")
        return VerifyResolution(command=command, source="legacy")

    # Profiles are mandatory here. A raw command survives only via the
    # allowlist, and "no gate at all" is refused too: a project that turned
    # this on wants every code change judged, and silence is not a judgement.
    if command and registry.allows_raw(command):
        return VerifyResolution(command=command, profile=CUSTOM_READONLY, source="allowlist")
    if command:
        return VerifyResolution(
            error=(
                f"this project requires named verify profiles, and `{command}` is "
                "not on the koru.yaml verify_allowlist. Set inputs.verify_profile "
                f"to one of: {', '.join(registry.names)}; or allowlist the command."
            ),
        )
    return VerifyResolution(
        error=(
            "this project requires a named verify profile and the ticket names "
            "no gate at all. Set inputs.verify_profile to one of: "
            f"{', '.join(registry.names)}."
        ),
    )


def _resolve_profile(
    registry: VerifyRegistry,
    name: str,
    ticket: dict,
    targets: tuple[str, ...],
) -> VerifyResolution:
    if name == CUSTOM_READONLY:
        raw = str((ticket.get("inputs") or {}).get("verify_command") or "").strip()
        if not raw:
            return VerifyResolution(
                error=(
                    f"verify_profile={CUSTOM_READONLY} needs inputs.verify_command "
                    "to say which allowlisted command to run, and the ticket has none."
                ),
            )
        if not registry.allows_raw(raw):
            return VerifyResolution(
                error=(
                    f"`{raw}` is not on this project's koru.yaml verify_allowlist, "
                    f"which {CUSTOM_READONLY} requires. Add it there, or use a "
                    f"named profile: {', '.join(registry.names)}."
                ),
            )
        return VerifyResolution(command=raw, profile=CUSTOM_READONLY, source="allowlist")

    profile = registry.get(name)
    if profile is None:
        return VerifyResolution(
            error=(
                f"verify_profile `{name}` is not defined — known profiles: "
                f"{', '.join(registry.names)}. A misspelt profile refuses rather "
                "than running without a gate."
            ),
        )
    command, render_error = render_profile_command(profile, targets)
    if render_error:
        return VerifyResolution(error=render_error)
    return VerifyResolution(command=command, profile=profile.name, source="profile")


def _profiles_required(project: Path) -> bool:
    from koru.queue.verify.registry import _queue_section

    return bool(_queue_section(project).get("verify_require_profile"))
