"""Core replay action data structures."""

from __future__ import annotations

import shlex
from dataclasses import dataclass, field


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


__all__ = ["ReplayAction", "ReplayResult", "ValidationResult"]
