"""Regression: Subactor development_defect repair ticket template schema."""

from __future__ import annotations

import unittest

from koru.queue.ticket_templates import (
    SUBACTOR_DEVELOPMENT_REPAIR,
    hydrate_subactor_repair_ticket,
    load_ticket_template,
    render_repair_ticket_from_development_defect,
    render_subactor_repair_ticket,
    template_path,
    validate_subactor_repair_template,
)


class TestSubactorRepairTicketTemplate(unittest.TestCase):
    def test_packaged_template_exists(self) -> None:
        path = template_path(SUBACTOR_DEVELOPMENT_REPAIR)
        self.assertTrue(path.is_file(), msg=str(path))

    def test_template_schema_and_policy_fields(self) -> None:
        data = load_ticket_template(SUBACTOR_DEVELOPMENT_REPAIR)
        errors = validate_subactor_repair_template(data)
        self.assertEqual(errors, [], msg="; ".join(errors))

        ticket = data["ticket"]
        inputs = ticket["inputs"]
        self.assertEqual((ticket.get("executor") or {}).get("kind"), "llm")
        self.assertEqual((ticket.get("executor") or {}).get("mode"), "automatic")
        self.assertTrue(str(inputs.get("llm_model") or "").strip())
        self.assertTrue(inputs["patch_mode"])
        self.assertEqual(inputs["promotion_mode"], "branch")
        self.assertTrue(inputs["worktree"])
        self.assertEqual(inputs["max_patch_attempts"], 2)
        self.assertEqual(len(ticket["files"]), 2)
        self.assertIn("intent-packs.test.mjs", inputs["verify_command"])
        self.assertNotIn("--apply", inputs["verify_command"].lower())
        self.assertNotIn("plesk", inputs["verify_command"].lower())

    def test_render_substitutes_bridge_metadata(self) -> None:
        rendered = render_subactor_repair_ticket(
            {
                "COMPONENT": "orchestrator",
                "ERROR_CODE": "invalid_runner_response",
                "FINGERPRINT": "orchestrator:invalid_runner_response",
                "DISCOVERED_IN": "PLF-364",
                "FILE_1": "orchestrator/bin/subactor-run.mjs",
                "FILE_2": "orchestrator/tests/development-defect.test.mjs",
                "PROMPT_BODY": "Keep JSON valid for large stdout.",
            },
        )
        self.assertEqual(rendered["files"][0], "orchestrator/bin/subactor-run.mjs")
        self.assertEqual((rendered.get("executor") or {}).get("kind"), "llm")
        self.assertTrue(str(rendered["inputs"].get("llm_model") or "").strip())
        self.assertIn("PLF-364", rendered["inputs"]["prompt"])
        self.assertNotIn("__", rendered["name"])

    def test_hydrate_restores_planfile_stripped_patch_policy(self) -> None:
        rendered = render_subactor_repair_ticket(
            {
                "COMPONENT": "orchestrator",
                "ERROR_CODE": "invalid_runner_response",
                "FINGERPRINT": "orchestrator:invalid_runner_response",
                "DISCOVERED_IN": "PLF-364",
                "FILE_1": "orchestrator/bin/subactor-run.mjs",
                "FILE_2": "orchestrator/tests/development-defect.test.mjs",
                "PROMPT_BODY": "Keep JSON valid.",
            },
        )
        stripped = {
            "id": "PLF-900",
            "labels": rendered["labels"],
            "inputs": {
                "prompt": rendered["inputs"]["prompt"],
                "llm_model": rendered["inputs"]["llm_model"],
            },
            "executor": rendered["executor"],
            "acceptance_criteria": rendered["acceptance_criteria"],
        }
        hydrated = hydrate_subactor_repair_ticket(stripped)
        self.assertTrue(hydrated["inputs"]["patch_mode"])
        self.assertEqual(hydrated["inputs"]["promotion_mode"], "branch")
        self.assertEqual(
            hydrated["inputs"]["verify_command"],
            rendered["acceptance_criteria"][0],
        )

    def test_max_patch_attempts_overrides_env_default(self) -> None:
        from koru.queue.patch_retry import patch_retry_budget

        ticket = {"inputs": {"max_patch_attempts": 2}}
        self.assertEqual(patch_retry_budget(ticket), 2)
        self.assertEqual(patch_retry_budget({"execution": {"max_attempts": 2}}), 2)
        self.assertEqual(patch_retry_budget({"inputs": {}}), 1)

    def test_render_from_development_defect_payload(self) -> None:
        payload = {
            "type": "development_defect",
            "component": "plesk-bridge",
            "error_code": "plan_hash_mismatch",
            "fingerprint": "plesk-bridge:plan_hash_mismatch",
            "discovered_in": "PLF-409",
            "affected_files": [
                "platform/components/connectors/services/bridge/src/plesk-httpdocs-sync.mjs",
                "platform/components/runtime/src/apply-grant.mjs",
            ],
            "acceptance_tests": [
                "node --test platform/components/testkit/tests/plesk-httpdocs-sync.test.mjs",
            ],
            "classification": {"action": "ticket", "category": "development_defect"},
        }
        ticket = render_repair_ticket_from_development_defect(payload)
        self.assertEqual((ticket.get("executor") or {}).get("kind"), "llm")
        self.assertEqual(ticket["inputs"]["promotion_mode"], "branch")
        self.assertIn("plesk-httpdocs-sync", ticket["inputs"]["verify_command"])
        self.assertEqual(ticket["inputs"]["discovered_in"], "PLF-409")

        with self.assertRaises(ValueError):
            render_repair_ticket_from_development_defect(
                {**payload, "classification": {"action": "ignore", "category": "operational_boundary"}},
            )


if __name__ == "__main__":
    unittest.main()
