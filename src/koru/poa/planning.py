"""Pure POA-P planning over evidence-only Subactor source snapshots.

Compatibility facade: the implementation is split by responsibility into the
focused :mod:`koru.poa` submodules (:mod:`errors`, :mod:`validation`,
:mod:`snapshots`, :mod:`policy_decisions`, :mod:`plan_compile`). This module
re-exports the previous public surface unchanged so existing
``koru.poa.planning`` consumers keep working.
"""

from __future__ import annotations

from .contracts import canonical_json
from .errors import (
    AmbiguousBinding,
    BindingNotFound,
    PlanningError,
    PolicyDenied,
)
from .plan_compile import compile_inert_plan, verify_planning_result
from .policy_decisions import policy_input_hash, validate_policy_decision
from .snapshots import build_source_snapshot, validate_source_registry_snapshot

__all__ = [
    "AmbiguousBinding",
    "BindingNotFound",
    "PlanningError",
    "PolicyDenied",
    "build_source_snapshot",
    "canonical_json",
    "compile_inert_plan",
    "policy_input_hash",
    "validate_policy_decision",
    "validate_source_registry_snapshot",
    "verify_planning_result",
]
