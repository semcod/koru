"""POA-P planning failure hierarchy.

Every deterministic planning failure derives from :class:`PlanningError`,
which itself derives from the shared :class:`~koru.poa.contracts.ContractError`
boundary.
"""

from __future__ import annotations

from .contracts import ContractError


class PlanningError(ContractError):
    """A deterministic planning failure."""


class BindingNotFound(PlanningError):
    """No exact candidate exists for a required capability."""


class AmbiguousBinding(PlanningError):
    """More than one candidate has the highest priority."""


class PolicyDenied(PlanningError):
    """The separate policy boundary did not admit inert planning."""


__all__ = [
    "AmbiguousBinding",
    "BindingNotFound",
    "PlanningError",
    "PolicyDenied",
]
