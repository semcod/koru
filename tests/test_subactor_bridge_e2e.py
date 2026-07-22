"""Cross-repo contract smoke: Subactor structural failure → Koru repair template.

Proves the bridge end-to-end without live LLM, Plesk, or ``subactor ask --apply``:

  plan_hash_mismatch / invalid_runner_response
    → development_defect upsert + blocked_by
    → ``subactor-development-repair`` render (files, verify_command, branch promotion)
  apply_grant_* operational codes
    → no development ticket

Resume after Koru closes SELFDEV-* (documented, not executed here):

  subactor-run --ticket <DISCOVERED_IN>           # dry-run preflight path
  subactor-run --ticket <DISCOVERED_IN> --execute # only after grant + Y/n
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

from koru.queue.ticket_templates import (
    SUBACTOR_DEVELOPMENT_REPAIR,
    load_ticket_template,
    render_repair_ticket_from_development_defect,
    validate_subactor_repair_template,
)

_BRIDGE_E2E_SCRIPT = """
import {
  buildDevelopmentDefectPayload,
  createMemoryDevelopmentTicketStore,
  classifyDevelopmentFailure,
} from "./orchestrator/src/development-defect.mjs";

const store = createMemoryDevelopmentTicketStore();

const manifestPayload = buildDevelopmentDefectPayload({
  ticketId: "PLF-409",
  component: "plesk-bridge",
  entry: {stage: "urirun", urirun: {error: "plan_hash_mismatch"}},
});
const structuralPayload = buildDevelopmentDefectPayload({
  ticketId: "PLF-364",
  component: "orchestrator",
  entry: {stage: "urirun", urirun: {error: "invalid_runner_response"}},
  affected_files: ["orchestrator/bin/subactor-run.mjs"],
});
const grantPayload = buildDevelopmentDefectPayload({
  ticketId: "PLF-1",
  component: "runtime",
  entry: {stage: "urirun", urirun: {error: "apply_grant_plan_hash_mismatch"}},
});

const manifestUpsert = store.upsert(manifestPayload);
const structuralUpsert = store.upsert(structuralPayload);
const grantUpsert = store.upsert(grantPayload);

console.log(JSON.stringify({
  manifest_payload: manifestPayload,
  structural_payload: structuralPayload,
  grant_payload: grantPayload,
  manifest_upsert: manifestUpsert,
  structural_upsert: structuralUpsert,
  grant_upsert: grantUpsert,
  manifest_blocked_by: store.getBlockedBy("PLF-409"),
  structural_blocked_by: store.getBlockedBy("PLF-364"),
  grant_blocked_by: store.getBlockedBy("PLF-1"),
  grant_classification: classifyDevelopmentFailure("apply_grant_plan_hash_mismatch"),
  manifest_classification: classifyDevelopmentFailure("plan_hash_mismatch"),
}));
"""


def _subactor_root() -> Path | None:
    env = (os.environ.get("SUBACTOR_ROOT") or "").strip()
    if env:
        candidate = Path(env).expanduser()
        if (candidate / "orchestrator/src/development-defect.mjs").is_file():
            return candidate
    default = Path("/home/tom/github/subactor")
    if (default / "orchestrator/src/development-defect.mjs").is_file():
        return default
    return None


def _run_subactor_bridge() -> dict:
    root = _subactor_root()
    if root is None or shutil.which("node") is None:
        raise unittest.SkipTest("subactor checkout or node unavailable")

    proc = subprocess.run(
        ["node", "--input-type=module", "-e", _BRIDGE_E2E_SCRIPT],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout or "node bridge script failed")
    return json.loads(proc.stdout.strip())


class TestSubactorKoruBridgeE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bridge = _run_subactor_bridge()

    def test_packaged_template_still_valid(self) -> None:
        errors = validate_subactor_repair_template(load_ticket_template(SUBACTOR_DEVELOPMENT_REPAIR))
        self.assertEqual(errors, [], msg="; ".join(errors))

    def test_plan_hash_mismatch_upsert_and_renders_repair_template(self) -> None:
        payload = self.bridge["manifest_payload"]
        upsert = self.bridge["manifest_upsert"]

        self.assertEqual(payload["type"], "development_defect")
        self.assertEqual(payload["queue"], "development")
        self.assertEqual(payload["error_code"], "plan_hash_mismatch")
        self.assertEqual(payload["fingerprint"], "plesk-bridge:plan_hash_mismatch")
        self.assertTrue(payload["affected_files"])
        self.assertTrue(payload["acceptance_tests"])
        self.assertEqual(upsert["recorded"], True)
        self.assertEqual(upsert["deduplicated"], False)
        self.assertEqual(self.bridge["manifest_blocked_by"], [upsert["ticket_id"]])

        ticket = render_repair_ticket_from_development_defect(payload)
        self.assertEqual((ticket.get("executor") or {}).get("kind"), "llm")
        self.assertEqual(ticket["inputs"]["promotion_mode"], "branch")
        self.assertTrue(ticket["inputs"]["patch_mode"])
        self.assertTrue(ticket["inputs"]["worktree"])
        self.assertIn("plesk-httpdocs-sync", ticket["files"][0])
        self.assertIn("plesk-httpdocs-sync", ticket["inputs"]["verify_command"])
        self.assertEqual(ticket["acceptance_criteria"][0], ticket["inputs"]["verify_command"])
        self.assertEqual(ticket["inputs"]["discovered_in"], "PLF-409")
        self.assertIn("PLF-409", ticket["inputs"]["prompt"])
        self.assertNotIn("__", ticket["name"])

    def test_invalid_runner_response_renders_with_declared_files(self) -> None:
        payload = self.bridge["structural_payload"]
        upsert = self.bridge["structural_upsert"]

        self.assertEqual(payload["fingerprint"], "orchestrator:invalid_runner_response")
        self.assertEqual(upsert["type"], "development_defect")
        self.assertEqual(self.bridge["structural_blocked_by"], [upsert["ticket_id"]])

        ticket = render_repair_ticket_from_development_defect(payload)
        self.assertEqual(ticket["files"][0], "orchestrator/bin/subactor-run.mjs")
        self.assertEqual(ticket["inputs"]["fingerprint"], "orchestrator:invalid_runner_response")
        self.assertEqual(ticket["inputs"]["promotion_mode"], "branch")

    def test_apply_grant_operational_failure_does_not_create_development_ticket(self) -> None:
        grant = self.bridge["grant_upsert"]
        classification = self.bridge["grant_classification"]

        self.assertEqual(classification["action"], "ignore")
        self.assertEqual(classification["category"], "operational_boundary")
        self.assertEqual(grant["recorded"], False)
        self.assertNotIn("ticket_id", grant)
        self.assertEqual(self.bridge["grant_blocked_by"], [])

        with self.assertRaises(ValueError, msg="operational payload must not render"):
            render_repair_ticket_from_development_defect(self.bridge["grant_payload"])

    def test_resume_dry_run_path_documented_on_source_ticket(self) -> None:
        """After Koru closes SELFDEV-*, resume uses subactor-run dry-run (no auto-apply)."""
        discovered = self.bridge["structural_payload"]["discovered_in"]
        blocked = self.bridge["structural_blocked_by"]
        self.assertTrue(discovered.startswith("PLF-"))
        self.assertEqual(len(blocked), 1)
        resume_cmd = f"subactor-run --ticket {discovered}"
        self.assertIn("subactor-run", resume_cmd)
        self.assertNotIn("--apply", resume_cmd)


if __name__ == "__main__":
    unittest.main()
