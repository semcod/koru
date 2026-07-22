"""Where profile names are looked up, and what a project may add to them.

Built-ins ship with koru; a project extends them in ``koru.yaml``:

.. code-block:: yaml

    queue:
      verify_profiles:
        node-syntax:
          command: "node --check ${changed_files}"
          timeout_s: 30
          allowed_extensions: [".js", ".mjs", ".cjs"]
      verify_allowlist:
        - "task quality:regix:local"

Project entries may shadow built-ins — the checkout's own config outranks
shipped defaults, same as the rest of koru.yaml. The allowlist is the escape
hatch for gates that fit no profile: a ticket may run a raw command only when
that exact string appears here (the ``custom-readonly`` path).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from koru.queue.verify.profiles import BUILTIN_PROFILES, VerifyProfile


@dataclass(frozen=True)
class VerifyRegistry:
    """The gates this workspace is allowed to run."""

    profiles: dict[str, VerifyProfile] = field(default_factory=dict)
    allowlist: tuple[str, ...] = ()

    def get(self, name: str) -> VerifyProfile | None:
        return self.profiles.get(name)

    def allows_raw(self, command: str) -> bool:
        """Whether this exact raw command has been allowlisted by the project."""
        return command.strip() in self.allowlist

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self.profiles))


def load_registry(project: Path) -> VerifyRegistry:
    """Built-ins merged with the project's koru.yaml additions.

    A malformed or missing koru.yaml degrades to built-ins only: the registry
    is a policy surface, and "could not read the policy" must never mean
    "policy relaxed".
    """
    profiles = dict(BUILTIN_PROFILES)
    queue_config = _queue_section(project)

    for name, spec in (queue_config.get("verify_profiles") or {}).items():
        profile = _parse_profile(str(name), spec)
        if profile is not None:
            profiles[profile.name] = profile

    allowlist = tuple(
        str(entry).strip()
        for entry in (queue_config.get("verify_allowlist") or [])
        if str(entry).strip()
    )
    return VerifyRegistry(profiles=profiles, allowlist=allowlist)


def _queue_section(project: Path) -> dict:
    try:
        import yaml
    except ImportError:
        return {}
    try:
        config = yaml.safe_load((project / "koru.yaml").read_text(encoding="utf-8"))
        section = (config or {}).get("queue") or {}
    except (OSError, AttributeError, yaml.YAMLError):
        return {}
    return section if isinstance(section, dict) else {}


def _parse_profile(name: str, spec: object) -> VerifyProfile | None:
    """One registry entry, or ``None`` when it cannot be trusted.

    An entry without a command is dropped rather than defaulted — inventing a
    command for a half-written profile would run something its author never
    reviewed.
    """
    if not isinstance(spec, dict):
        return None
    command = str(spec.get("command") or "").strip()
    if not command:
        return None
    try:
        timeout_s = max(1, int(spec.get("timeout_s") or 300))
    except (TypeError, ValueError):
        timeout_s = 300
    extensions = tuple(
        str(ext) for ext in (spec.get("allowed_extensions") or []) if str(ext).startswith(".")
    )
    return VerifyProfile(
        name=name,
        command=command,
        timeout_s=timeout_s,
        allowed_extensions=extensions,
        description=str(spec.get("description") or ""),
    )
