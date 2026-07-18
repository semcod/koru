"""Minimal bridge contract test: Subactor structural failure → development ticket.

Exercises the in-memory upsert store shipped with Subactor's orchestrator so Koru
operators can rely on the ``development_defect`` / ``blocked_by`` shape without
live LLM, Plesk, or planfile CLI.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path


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


_BRIDGE_SCRIPT = """
import {
  buildDevelopmentDefectPayload,
  createMemoryDevelopmentTicketStore,
  classifyDevelopmentFailure,
} from "./orchestrator/src/development-defect.mjs";

const store = createMemoryDevelopmentTicketStore();
const payload = buildDevelopmentDefectPayload({
  ticketId: "PLF-364",
  component: "orchestrator",
  entry: {stage: "urirun", urirun: {error: "invalid_runner_response"}},
  affected_files: ["orchestrator/bin/subactor-run.mjs"],
});
const structural = classifyDevelopmentFailure("invalid_runner_response");
const operational = classifyDevelopmentFailure("dns_mismatch");
const manifestBug = classifyDevelopmentFailure("plan_hash_mismatch");
const grantOps = classifyDevelopmentFailure("apply_grant_plan_hash_mismatch");
const manifestPayload = buildDevelopmentDefectPayload({
  ticketId: "PLF-409",
  component: "plesk-bridge",
  entry: {stage: "urirun", urirun: {error: "plan_hash_mismatch"}},
});
const first = store.upsert(payload);
const second = store.upsert(payload);
const manifestUpsert = store.upsert(manifestPayload);
console.log(JSON.stringify({
  structural_action: structural.action,
  operational_action: operational.action,
  manifest_bug_action: manifestBug.action,
  grant_ops_action: grantOps.action,
  payload_type: payload.type,
  payload_queue: payload.queue,
  fingerprint: payload.fingerprint,
  manifest_fingerprint: manifestPayload.fingerprint,
  manifest_affected_files: manifestPayload.affected_files,
  first_id: first.ticket_id,
  first_deduplicated: first.deduplicated,
  second_deduplicated: second.deduplicated,
  blocked_by: store.getBlockedBy("PLF-364"),
  manifest_ticket_id: manifestUpsert.ticket_id,
}));
"""


class TestSubactorDevelopmentBridge(unittest.TestCase):
    def test_structural_failure_upserts_development_ticket_with_blocked_by(self) -> None:
        root = _subactor_root()
        if root is None or shutil.which("node") is None:
            self.skipTest("subactor checkout or node unavailable")

        proc = subprocess.run(
            ["node", "--input-type=module", "-e", _BRIDGE_SCRIPT],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            proc.returncode,
            0,
            msg=(proc.stderr or proc.stdout or "node failed"),
        )
        data = json.loads(proc.stdout.strip())

        self.assertEqual(data["structural_action"], "ticket")
        self.assertEqual(data["operational_action"], "ignore")
        self.assertEqual(data["manifest_bug_action"], "ticket")
        self.assertEqual(data["grant_ops_action"], "ignore")
        self.assertEqual(data["payload_type"], "development_defect")
        self.assertEqual(data["payload_queue"], "development")
        self.assertEqual(data["fingerprint"], "orchestrator:invalid_runner_response")
        self.assertEqual(data["manifest_fingerprint"], "plesk-bridge:plan_hash_mismatch")
        self.assertTrue(any("plesk-httpdocs-sync" in f for f in data["manifest_affected_files"]))
        self.assertFalse(data["first_deduplicated"])
        self.assertTrue(data["second_deduplicated"])
        self.assertEqual(data["blocked_by"], [data["first_id"]])
        self.assertTrue(data["manifest_ticket_id"])


if __name__ == "__main__":
    unittest.main()
