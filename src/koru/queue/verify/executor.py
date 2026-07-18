"""Turning a profile into the one string the shell runner will execute.

Rendering is the last moment before a profile becomes a command, so the two
guarantees profiles make are enforced here: file arguments are limited to the
extensions the profile declared, and the timeout travels *inside* the command
(a ``timeout <s>`` prefix) because the queue's shell-runner contract —
``(command, cwd) -> result`` — is injected in too many places to grow a
timeout parameter quietly.
"""

from __future__ import annotations

import os
import shlex

from koru.queue.verify.profiles import CHANGED_FILES, VerifyProfile


def render_profile_command(
    profile: VerifyProfile,
    targets: tuple[str, ...],
) -> tuple[str, str | None]:
    """The runnable command, or why this profile cannot judge this patch.

    A file-scoped profile whose patch touched no matching file is an error,
    not an empty gate: ``node --check`` with no arguments would exit 0 and
    "verify" a patch it never looked at.
    """
    command = profile.command
    if CHANGED_FILES in command:
        matching = _matching_targets(profile, targets)
        if not matching:
            extensions = ", ".join(profile.allowed_extensions) or "its declared extensions"
            return "", (
                f"profile {profile.name} checks files matching {extensions}, but the "
                "patch touches none — the gate would pass without judging the patch. "
                "Pick a profile that covers what this patch changes."
            )
        command = command.replace(
            CHANGED_FILES, " ".join(shlex.quote(rel) for rel in matching),
        )
    return _with_timeout(command, profile.timeout_s), None


def _matching_targets(profile: VerifyProfile, targets: tuple[str, ...]) -> tuple[str, ...]:
    if not profile.allowed_extensions:
        return targets
    return tuple(
        rel for rel in targets if rel.endswith(tuple(profile.allowed_extensions))
    )


def _with_timeout(command: str, timeout_s: int) -> str:
    """Bound the gate's runtime where the platform lets us.

    coreutils ``timeout`` exists on POSIX, which is where the queue runs; on
    anything else the command runs unbounded rather than not at all.
    """
    if os.name != "posix":
        return command
    return f"timeout {int(timeout_s)}s sh -c {shlex.quote(command)}"
