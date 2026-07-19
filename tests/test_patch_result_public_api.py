"""P0-3: the patch-transaction result is a public, structured contract.

External consumers (the Subactor development bridge, ticket-note writers)
must be able to import the result type and stable failure codes from
``koru.queue`` and branch on ``code`` — never on message wording.
"""

from __future__ import annotations

from types import SimpleNamespace

from koru.queue import (
    NO_VALID_ARTIFACT,
    PATCH_DOES_NOT_APPLY,
    POLICY_DENIED,
    PROMOTION_CONFLICT,
    UNSAFE_DIRTY_WORKSPACE,
    VERIFY_BASELINE_FAILED,
    VERIFY_FAILED_ISOLATED,
    VERIFY_FAILED_ROLLED_BACK,
    VERIFY_PROFILE_INVALID,
    PatchOutcome,
    PatchTransactionResult,
)
from koru.queue.patch_transaction import (
    PatchTransactionResult as FacadeResult,
)


def _cmd() -> SimpleNamespace:
    # CommandResult is a structural Protocol; any reply-shaped object works.
    return SimpleNamespace(returncode=0, stdout="", stderr="")


class TestPublicSurface:
    def test_facade_and_package_expose_the_same_type(self):
        assert FacadeResult is PatchTransactionResult

    def test_stable_codes_are_distinct_strings(self):
        codes = {
            NO_VALID_ARTIFACT,
            PATCH_DOES_NOT_APPLY,
            UNSAFE_DIRTY_WORKSPACE,
            PROMOTION_CONFLICT,
            VERIFY_BASELINE_FAILED,
            VERIFY_FAILED_ISOLATED,
            VERIFY_FAILED_ROLLED_BACK,
            VERIFY_PROFILE_INVALID,
            POLICY_DENIED,
        }
        assert len(codes) == 9
        assert all(isinstance(code, str) and code for code in codes)


class TestResultAccessors:
    def test_landed_patch_is_ok_with_no_code(self):
        landed = PatchTransactionResult(result=_cmd(), outcome=None)
        assert landed.ok is True
        assert landed.code is None

    def test_refusal_exposes_the_structural_code(self):
        refused = PatchTransactionResult(
            result=_cmd(),
            outcome=PatchOutcome(
                code=PATCH_DOES_NOT_APPLY,
                message="human wording that may change at any time",
                retryable=True,
            ),
        )
        assert refused.ok is False
        assert refused.code == PATCH_DOES_NOT_APPLY
        # the tuple adapter stays intact for legacy callers
        result, outcome = refused.as_tuple()
        assert result is refused.result and outcome is refused.outcome
