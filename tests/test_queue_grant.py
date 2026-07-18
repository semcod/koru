"""Signed execution grants and replay protection.

The property under test: a mutation happens only inside the intersection of a
valid signature, a live expiry, bindings that match what is actually about to
run, and a ``jti`` nobody has spent. Remove any one of them and the answer is
no — and the tests remove them one at a time.
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from koru.queue.grant import (
    GrantBindings,
    generate_keypair,
    issue_grant,
    mutations_enabled,
    verify_grant,
)
from koru.queue.grant_store import (
    claim_jti,
    complete_jti,
    fail_jti,
    jti_state,
)

_NOW = datetime(2026, 7, 18, 12, 0, 0, tzinfo=UTC)


class _GrantLab(unittest.TestCase):
    def setUp(self) -> None:
        self.private, self.public = generate_keypair()
        self.workspace = Path(tempfile.mkdtemp())

    def _issue(self, **overrides) -> str:
        fields = {
            "run_id": "run-1",
            "ticket_id": "T-1",
            "actor": "bot:koru-refactor",
            "workspace": self.workspace,
            "base_head": "abc123",
            "manifest_hash": "mh-1",
            "patch_sha256": "ps-1",
            "capabilities": ("code.patch.stage", "test.profile.run"),
            "promotion_mode": "branch",
            "now": _NOW,
        }
        fields.update(overrides)
        return issue_grant(self.private, **fields)

    def _bindings(self, **overrides) -> GrantBindings:
        fields = {
            "run_id": "run-1",
            "workspace": self.workspace,
            "manifest_hash": "mh-1",
            "patch_sha256": "ps-1",
            "actor": "bot:koru-refactor",
            "capability": "code.patch.stage",
            "promotion_mode": "branch",
            "base_head": "abc123",
        }
        fields.update(overrides)
        return GrantBindings(**fields)

    def _verify(self, token: str, bindings: GrantBindings | None = None, *, at=None):
        return verify_grant(
            self.public, token, bindings or self._bindings(), now=at or _NOW,
        )


class TestGrantVerification(_GrantLab):
    def test_a_well_bound_grant_is_allowed(self) -> None:
        decision = self._verify(self._issue())

        self.assertTrue(decision.allowed, decision.reason)
        self.assertTrue(decision.jti)

    def test_a_forged_signature_is_refused_before_the_payload_is_read(self) -> None:
        other_private, _other_public = generate_keypair()
        forged = issue_grant(
            other_private,
            run_id="run-1",
            ticket_id="T-1",
            actor="bot:koru-refactor",
            workspace=self.workspace,
            base_head="abc123",
            manifest_hash="mh-1",
            patch_sha256="ps-1",
            capabilities=("code.patch.stage",),
            promotion_mode="branch",
            now=_NOW,
        )

        decision = self._verify(forged)

        self.assertFalse(decision.allowed)
        self.assertIn("signature", decision.reason)
        self.assertEqual(decision.payload, {}, "a forged payload gets no influence")

    def test_a_tampered_payload_is_refused(self) -> None:
        body_b64, sig_b64 = self._issue().split(".")
        import base64
        import json

        payload = json.loads(base64.urlsafe_b64decode(body_b64 + "=="))
        payload["capabilities"] = ["code.patch.promote_main"]  # escalation attempt
        doctored = (
            base64.urlsafe_b64encode(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(),
            ).decode().rstrip("=")
            + "."
            + sig_b64
        )

        self.assertFalse(self._verify(doctored).allowed)

    def test_no_grant_at_all_is_refused(self) -> None:
        self.assertFalse(self._verify("").allowed)
        self.assertFalse(self._verify("not-a-token").allowed)

    def test_an_expired_grant_is_refused(self) -> None:
        token = self._issue(ttl_s=60)

        late = self._verify(token, at=_NOW + timedelta(seconds=61))

        self.assertFalse(late.allowed)
        self.assertIn("expired", late.reason)

    def test_every_binding_mismatch_refuses(self) -> None:
        """Wrong actor, workspace, HEAD, manifest, patch SHA — one at a time."""
        token = self._issue()
        for name, overrides in (
            ("actor", {"actor": "bot:someone-else"}),
            ("workspace", {"workspace": Path(tempfile.mkdtemp())}),
            ("base_head", {"base_head": "fff999"}),
            ("manifest_hash", {"manifest_hash": "mh-OTHER"}),
            ("patch_sha256", {"patch_sha256": "ps-OTHER"}),
            ("run_id", {"run_id": "run-OTHER"}),
            ("promotion_mode", {"promotion_mode": "commit"}),
        ):
            with self.subTest(binding=name):
                decision = self._verify(token, self._bindings(**overrides))
                self.assertFalse(decision.allowed, name)

    def test_a_capability_the_grant_does_not_carry_is_refused(self) -> None:
        decision = self._verify(
            self._issue(), self._bindings(capability="code.patch.promote_main"),
        )

        self.assertFalse(decision.allowed)
        self.assertIn("capability", decision.reason)

    def test_a_staging_grant_dies_in_production(self) -> None:
        token = self._issue(audience="koru-staging-executor")

        decision = self._verify(token)  # bindings expect the default (production) audience

        self.assertFalse(decision.allowed)
        self.assertIn("audience", decision.reason)

    def test_the_kill_switch_defaults_to_off(self) -> None:
        """Nothing overrides an absent yes."""
        from unittest import mock

        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertFalse(mutations_enabled())
        with mock.patch.dict("os.environ", {"KORU_MUTATIONS_ENABLED": "1"}):
            self.assertTrue(mutations_enabled())


class TestReplayProtection(unittest.TestCase):
    def setUp(self) -> None:
        self.project = Path(tempfile.mkdtemp())

    def _claim(self, jti="jti-1", run_id="run-1", manifest_hash="mh-1", **kw):
        return claim_jti(
            self.project, jti, run_id=run_id, manifest_hash=manifest_hash,
            now=kw.pop("now", _NOW), **kw,
        )

    def test_first_claim_wins_and_is_durable(self) -> None:
        self.assertTrue(self._claim().ok)
        self.assertEqual(jti_state(self.project, "jti-1"), "processing")

    def test_replay_after_success_is_refused(self) -> None:
        self._claim()
        complete_jti(self.project, "jti-1")

        replay = self._claim()

        self.assertFalse(replay.ok)
        self.assertIn("already spent", replay.reason)

    def test_replay_after_failure_is_also_refused(self) -> None:
        """Failure spends the grant too — a failed run cannot be re-authorized."""
        self._claim()
        fail_jti(self.project, "jti-1")

        self.assertFalse(self._claim().ok)

    def test_replay_during_processing_is_refused(self) -> None:
        self._claim()

        concurrent = self._claim(now=_NOW + timedelta(seconds=1))

        self.assertFalse(concurrent.ok)
        self.assertIn("lease has not expired", concurrent.reason)

    def test_the_same_run_recovers_its_claim_after_the_lease_expires(self) -> None:
        self._claim(lease_s=60)

        recovered = self._claim(now=_NOW + timedelta(seconds=61))

        self.assertTrue(recovered.ok)
        self.assertIn("reclaimed", recovered.reason)

    def test_a_different_manifest_cannot_resume_the_old_transaction(self) -> None:
        """A stale permission must not authorize work it never described."""
        self._claim(lease_s=60)

        hijack = self._claim(
            manifest_hash="mh-DIFFERENT", now=_NOW + timedelta(seconds=61),
        )

        self.assertFalse(hijack.ok)
        self.assertIn("different run or manifest", hijack.reason)

    def test_a_different_run_cannot_resume_either(self) -> None:
        self._claim(lease_s=60)

        self.assertFalse(
            self._claim(run_id="run-OTHER", now=_NOW + timedelta(seconds=61)).ok,
        )

    def test_terminal_states_never_reopen(self) -> None:
        self._claim()
        complete_jti(self.project, "jti-1")
        fail_jti(self.project, "jti-1")  # must not flip completed → failed

        self.assertEqual(jti_state(self.project, "jti-1"), "completed")

    def test_a_malformed_jti_cannot_escape_the_store_directory(self) -> None:
        for jti in ("", "../evil", "a/b", "x.json"):
            with self.subTest(jti=jti):
                self.assertFalse(self._claim(jti=jti).ok)


if __name__ == "__main__":
    unittest.main()
