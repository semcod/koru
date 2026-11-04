from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from koru.expectation_audit import DEFAULT_REPORT, audit, main
from koru.scan import scan_semcod_quality_artifacts

CONSUMER = """
const SCAN_URI = "demo://registry/query/manifests";
const manifest = {definitions: {
  eql: [{id: "cycle-recorded", expected: {observation_persisted: true}, verifier: "demo", verified_by: ["scan"]}],
  uri: [{id: "scan", name: "Scan", uri: SCAN_URI}],
}};
"""

SILENT_PRODUCER = """
@handler("registry/query/manifests")
def manifests():
    return {"ok": True, "keys": []}
"""

COMPLETE_PRODUCER = """
@handler("registry/query/manifests")
def manifests():
    return {"ok": True, "observation_persisted": True}
"""


def _tree(root: Path, producer: str, consumer: str = CONSUMER) -> tuple[Path, Path]:
    (root / "consumer").mkdir()
    (root / "producer").mkdir()
    (root / "consumer" / "process.mjs").write_text(consumer, encoding="utf-8")
    (root / "producer" / "core.py").write_text(producer, encoding="utf-8")
    return root / "consumer", root / "producer"


def _rules(report: dict, key: str = "findings") -> list[str]:
    return sorted(item["rule"] for item in report[key])


class ExpectationAuditTests(unittest.TestCase):
    def test_producer_that_never_emits_the_key_is_flagged_by_s3_and_s4(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            consumer, producer = _tree(Path(tmp), SILENT_PRODUCER)
            report = audit([], [consumer], [producer])
        self.assertEqual(_rules(report), ["S3", "S4"])
        s4 = next(item for item in report["findings"] if item["rule"] == "S4")
        self.assertEqual(s4["missing_keys"], ["observation_persisted"])
        self.assertEqual(s4["id"], "cycle-recorded")
        self.assertTrue(s4["closest_producer"].endswith("core.py"))

    def test_producer_that_emits_every_key_is_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            consumer, producer = _tree(Path(tmp), COMPLETE_PRODUCER)
            report = audit([], [consumer], [producer])
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["informational"], [])

    def test_camel_case_producer_satisfies_a_snake_case_expectation(self) -> None:
        consumer_text = CONSUMER.replace("observation_persisted", "expected_scheme").replace("true", '"Basic"')
        producer_text = SILENT_PRODUCER.replace('"keys": []', '"expectedScheme": "Basic"')
        with tempfile.TemporaryDirectory() as tmp:
            consumer, producer = _tree(Path(tmp), producer_text, consumer_text)
            report = audit([], [consumer], [producer])
        self.assertEqual(report["findings"], [])

    def test_unresolvable_verifying_uri_is_informational_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dynamic = CONSUMER.replace("uri: SCAN_URI", "uri: dynamicUri()")
            consumer, producer = _tree(Path(tmp), COMPLETE_PRODUCER, dynamic)
            report = audit([], [consumer], [producer])
        self.assertEqual(report["findings"], [])
        self.assertEqual(_rules(report, "informational"), ["S4-unresolved"])

    def test_ticket_manifests_are_classified_by_rule(self) -> None:
        def ticket(ticket_id: str, expectation: dict) -> dict:
            return {"id": ticket_id, "inputs": {"process_manifest": {"definitions": {"eql": [expectation]}}}}

        tickets = [
            ticket("PLF-1", {"id": "a", "expected": {}, "verified_by": ["x"]}),
            ticket("PLF-2", {"id": "b", "expected": True}),
            ticket("PLF-3", {"id": "c", "expected": "ready", "verified_by_control": ["process-envelope.v2"]}),
            ticket("PLF-4", {"id": "d", "expected": {"ok": True}, "verified_by": ["x"]}),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp)
            report = audit(tickets, [empty], [empty])
        self.assertEqual(_rules(report), ["S1", "S2"])
        self.assertEqual(_rules(report, "informational"), ["S5"])
        self.assertEqual(report["summary"]["tickets_scanned"], 4)


class ExpectationAuditReportTests(unittest.TestCase):
    def test_cli_writes_a_report_that_scan_turns_into_one_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            consumer, producer = _tree(root, SILENT_PRODUCER)
            project = root / "project"
            project.mkdir()
            code = main(["--project", str(project), "--consumer", str(consumer), "--producer", str(producer)])
            report = json.loads((project / DEFAULT_REPORT).read_text(encoding="utf-8"))
            suggestions = [s for s in scan_semcod_quality_artifacts(project) if s.signal == "expectation_contract"]
        self.assertEqual(code, 1)
        self.assertEqual(report["schema"], "koru.expectation-audit/v1")
        self.assertEqual(len(suggestions), 1)
        self.assertIn(DEFAULT_REPORT, suggestions[0].description)
        self.assertIn("2 actionable", suggestions[0].description)

    def test_informational_entries_do_not_open_a_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".expectation-audit").mkdir()
            (project / DEFAULT_REPORT).write_text(
                json.dumps({"findings": [], "informational": [{"rule": "S5"}, {"rule": "S4-unresolved"}]}),
                encoding="utf-8",
            )
            suggestions = [s for s in scan_semcod_quality_artifacts(project) if s.signal == "expectation_contract"]
        self.assertEqual(suggestions, [])


if __name__ == "__main__":
    unittest.main()
