"""Regression: Subactor development_defect repair ticket template schema."""

from __future__ import annotations

import unittest

from koru.queue.ticket_templates import (
    SUBACTOR_DEVELOPMENT_REPAIR,
    load_ticket_template,
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
        self.assertIn("PLF-364", rendered["inputs"]["prompt"])
        self.assertNotIn("__", rendered["name"])

    def test_max_patch_attempts_overrides_env_default(self) -> None:
        from koru.queue.patch_retry import patch_retry_budget

        ticket = {"inputs": {"max_patch_attempts": 2}}
        self.assertEqual(patch_retry_budget(ticket), 2)
        self.assertEqual(patch_retry_budget({"inputs": {}}), 1)


if __name__ == "__main__":
    unittest.main()
