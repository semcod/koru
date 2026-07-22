"""What resolving a ticket's gate concluded, as data.

A resolution either names a runnable command or explains why one could not be
produced. The distinction matters at the policy layer: "this ticket has no
gate" falls through to weaker sources, while "this ticket named a profile that
does not exist" must refuse — falling through would let a typo disable
verification, which is exactly the silent downgrade profiles exist to prevent.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VerifyResolution:
    """The gate a patch must pass, or why none could be resolved.

    ``source`` records which rung of the precedence ladder produced the
    command — evidence needs to say *why* this gate ran, not just that it did.
    """

    command: str = ""
    profile: str | None = None
    source: str = "none"
    error: str | None = None

    @property
    def refused(self) -> bool:
        return self.error is not None
