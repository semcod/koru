"""ProposalEnvelope is the strict DSL boundary between a model and executors."""

from __future__ import annotations

import json
import unittest
from copy import deepcopy
from types import SimpleNamespace

from koru.proposal_envelope import (
    NO_VALID_ARTIFACT,
    ProposalValidationError,
    build_proposal_envelope,
    parse_proposal_envelope,
    validate_proposal_envelope,
)
from koru.queue.transaction.preflight import extract_patch

_DIFF = (
    "diff --git a/src/a.py b/src/a.py\n"
    "--- a/src/a.py\n"
    "+++ b/src/a.py\n"
    "@@ -1 +1 @@\n"
    "-old\n"
    "+new\n"
)


def _envelope(**overrides):
    fields = {
        "intent_pack_id": "development.propose_patch",
        "intent_pack_version": "1.0",
        "slots": {"ticket_id": "DEV-1"},
        "artifact_kind": "unified_diff",
        "artifact_content": _DIFF,
        "input_hash": "a" * 64,
        "prompt_schema_hash": "b" * 64,
        "provider": "z.ai",
        "model": "glm-4.7",
    }
    fields.update(overrides)
    return build_proposal_envelope(**fields)


class TestProposalEnvelope(unittest.TestCase):
    def test_round_trip_validates_hashes_and_provenance(self) -> None:
        parsed = parse_proposal_envelope(json.dumps(_envelope()))

        self.assertEqual(parsed.artifact_kind, "unified_diff")
        self.assertEqual(parsed.artifact_content, _DIFF)
        self.assertEqual(parsed.provider, "z.ai")
        self.assertEqual(parsed.model, "glm-4.7")
        self.assertEqual(len(parsed.proposal_sha256), 64)

    def test_canonical_hash_ignores_mapping_key_order(self) -> None:
        first = _envelope(slots={"ticket_id": "DEV-1", "scope": {"b": 2, "a": 1}})
        second = _envelope(slots={"scope": {"a": 1, "b": 2}, "ticket_id": "DEV-1"})

        self.assertEqual(first["hashes"], second["hashes"])

    def test_tampered_artifact_is_rejected(self) -> None:
        payload = _envelope()
        payload["artifact"]["content"] += "# injected after hashing\n"

        with self.assertRaisesRegex(ProposalValidationError, "artifact_sha256"):
            validate_proposal_envelope(payload)

    def test_extra_or_authority_fields_are_rejected(self) -> None:
        extra = _envelope()
        extra["transport"] = "subprocess"
        with self.assertRaises(ProposalValidationError):
            validate_proposal_envelope(extra)

        forbidden_slot = _envelope()
        forbidden_slot["slots"] = {"nested": {"capability": "root.shell"}}
        with self.assertRaisesRegex(ProposalValidationError, "slots.nested.capability"):
            validate_proposal_envelope(forbidden_slot)

    def test_markdown_or_prose_around_json_is_rejected(self) -> None:
        content = "```json\n" + json.dumps(_envelope()) + "\n```"

        with self.assertRaisesRegex(ProposalValidationError, "exact JSON"):
            parse_proposal_envelope(content)

    def test_patch_preflight_accepts_only_the_bound_diff_artifact(self) -> None:
        reply = SimpleNamespace(
            returncode=0,
            stdout=json.dumps(_envelope()),
            stderr="",
        )

        diff, bindings, refusal = extract_patch(reply)

        self.assertIsNone(refusal)
        self.assertEqual(diff, _DIFF.replace("@@ -1 +1 @@", "@@ -1,1 +1,1 @@"))

    def test_patch_preflight_rejects_invalid_or_wrong_kind_envelope(self) -> None:
        tampered = deepcopy(_envelope())
        tampered["provenance"]["provider"] = "other"
        invalid = SimpleNamespace(returncode=0, stdout=json.dumps(tampered), stderr="")

        _diff, _bindings, refusal = extract_patch(invalid)

        assert refusal is not None
        self.assertEqual(refusal.code, NO_VALID_ARTIFACT)
        self.assertTrue(refusal.retryable)

        wrong_kind = SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                _envelope(
                    artifact_kind="semantic_patch",
                    artifact_content={"summary": "not code"},
                ),
            ),
            stderr="",
        )
        _diff, _bindings, refusal = extract_patch(wrong_kind)
        assert refusal is not None
        self.assertEqual(refusal.code, NO_VALID_ARTIFACT)


if __name__ == "__main__":
    unittest.main()


class TestExtractPatchBindings:
    """The envelope's verified hashes travel out of extract_patch."""

    def test_valid_envelope_yields_bindings(self):
        import json
        from types import SimpleNamespace

        from koru.proposal_envelope import build_proposal_envelope
        from koru.queue.transaction.preflight import extract_patch

        diff = (
            "diff --git a/a.txt b/a.txt\n"
            "--- a/a.txt\n"
            "+++ b/a.txt\n"
            "@@ -1 +1 @@\n"
            "-old\n"
            "+new\n"
        )
        payload = build_proposal_envelope(
            intent_pack_id="koru.patch",
            intent_pack_version="1.0",
            slots={},
            artifact_kind="unified_diff",
            artifact_content=diff,
            input_hash="a" * 64,
            prompt_schema_hash="b" * 64,
            provider="z.ai",
            model="glm-5.2",
        )
        reply = SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")
        extracted_diff, bindings, refusal = extract_patch(reply)
        assert refusal is None and extracted_diff is not None
        assert bindings["proposal_sha256"] == payload["hashes"]["proposal_sha256"]
        assert bindings["artifact_sha256"] == payload["hashes"]["artifact_sha256"]
        assert bindings["intent_pack"] == {"id": "koru.patch", "version": "1.0"}

    def test_legacy_bare_diff_yields_no_bindings(self):
        from types import SimpleNamespace

        from koru.queue.transaction.preflight import extract_patch

        diff = (
            "diff --git a/a.txt b/a.txt\n"
            "--- a/a.txt\n"
            "+++ b/a.txt\n"
            "@@ -1 +1 @@\n"
            "-old\n"
            "+new\n"
        )
        reply = SimpleNamespace(returncode=0, stdout=diff, stderr="")
        extracted_diff, bindings, refusal = extract_patch(reply)
        assert refusal is None and extracted_diff is not None
        assert bindings is None
