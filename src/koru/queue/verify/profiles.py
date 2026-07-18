"""Named verify profiles: the closed set of gates a ticket may ask for.

A ticket that says ``verify_profile: node-check`` is asking for a *kind* of
verification, not a shell command. What actually runs is decided here and in
the project's own registry entries — never by the ticket author, and never by
the LLM that wrote the ticket. That inversion is the point: tickets travel
through queues, files and model output, all places where an arbitrary command
string is an injection surface.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Placeholder a profile command may carry; replaced with the patch's changed
#: files (shell-quoted, filtered by ``allowed_extensions``) at render time.
CHANGED_FILES = "${changed_files}"

#: The profile name reserved for allowlisted raw commands. It has no command of
#: its own: the ticket supplies one, and the registry only honours it when the
#: project's koru.yaml lists that exact string.
CUSTOM_READONLY = "custom-readonly"


@dataclass(frozen=True)
class VerifyProfile:
    """A named, bounded gate.

    ``timeout_s`` is enforced by prefixing the rendered command — the queue's
    shell runner deliberately knows nothing about profiles. ``allowed_extensions``
    empty means the command takes no file arguments.
    """

    name: str
    command: str
    timeout_s: int = 300
    allowed_extensions: tuple[str, ...] = field(default=())
    description: str = ""


BUILTIN_PROFILES: dict[str, VerifyProfile] = {
    profile.name: profile
    for profile in (
        VerifyProfile(
            name="python-pytest",
            command="python -m pytest -q",
            timeout_s=600,
            description="run the project's pytest suite",
        ),
        VerifyProfile(
            name="python-ruff",
            command="python -m ruff check .",
            timeout_s=120,
            description="lint the project with ruff",
        ),
        VerifyProfile(
            name="node-test",
            command="npm test --silent",
            timeout_s=600,
            description="run the project's npm test script",
        ),
        VerifyProfile(
            name="node-check",
            command=f"node --check {CHANGED_FILES}",
            timeout_s=60,
            allowed_extensions=(".js", ".mjs", ".cjs"),
            description="syntax-check the JavaScript files the patch touched",
        ),
        VerifyProfile(
            name="typescript-check",
            command="npx tsc --noEmit",
            timeout_s=300,
            description="type-check the project without emitting",
        ),
        VerifyProfile(
            name="shellcheck",
            command=f"shellcheck {CHANGED_FILES}",
            timeout_s=60,
            allowed_extensions=(".sh", ".bash"),
            description="lint the shell scripts the patch touched",
        ),
    )
}
