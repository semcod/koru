"""CI contract for the dependency-boundary extraction DSL."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "docs/architecture/dependency-boundary-inventory.yaml"
SCHEMA_PATH = ROOT / "schemas/dependency-boundary-inventory.schema.json"


def _load_inventory() -> dict:
    return yaml.safe_load(INVENTORY_PATH.read_text(encoding="utf-8"))


class TestDependencyBoundaryInventory(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory = _load_inventory()
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_inventory_matches_json_schema(self) -> None:
        Draft202012Validator.check_schema(self.schema)
        errors = sorted(
            Draft202012Validator(self.schema).iter_errors(self.inventory),
            key=lambda error: tuple(str(part) for part in error.absolute_path),
        )
        self.assertEqual(
            errors,
            [],
            "\n".join(
                f"{list(error.absolute_path)}: {error.message}" for error in errors
            ),
        )

    def test_ids_and_reference_lists_are_canonical(self) -> None:
        for section in ("repositories", "contracts", "extractions"):
            ids = [item["id"] for item in self.inventory[section]]
            with self.subTest(section=section):
                self.assertEqual(len(ids), len(set(ids)), "duplicate id")
                self.assertEqual(ids, sorted(ids), "keep DSL diffs deterministic")

        for extraction in self.inventory["extractions"]:
            for field in ("source_modules", "target_repositories", "contract_ids", "blocked_by"):
                values = extraction[field]
                with self.subTest(extraction=extraction["id"], field=field):
                    self.assertEqual(values, sorted(values))

    def test_references_are_closed_and_sources_exist(self) -> None:
        repositories = {item["id"] for item in self.inventory["repositories"]}
        contracts = {item["id"] for item in self.inventory["contracts"]}
        extractions = {item["id"] for item in self.inventory["extractions"]}

        for contract in self.inventory["contracts"]:
            with self.subTest(contract=contract["id"]):
                self.assertIn(contract["mechanism_owner"], repositories)

        for extraction in self.inventory["extractions"]:
            with self.subTest(extraction=extraction["id"]):
                self.assertTrue(set(extraction["target_repositories"]) <= repositories)
                self.assertTrue(set(extraction["contract_ids"]) <= contracts)
                self.assertTrue(set(extraction["blocked_by"]) <= extractions)
                self.assertNotIn(extraction["id"], extraction["blocked_by"])
            for module in extraction["source_modules"]:
                with self.subTest(extraction=extraction["id"], module=module):
                    self.assertTrue((ROOT / module).exists(), module)

    def test_koru_keeps_authority_but_is_not_an_extraction_target(self) -> None:
        self.assertEqual(
            self.inventory["policy"]["authorization_owner"],
            "semcod/koru",
        )
        for contract in self.inventory["contracts"]:
            with self.subTest(contract=contract["id"]):
                self.assertEqual(contract["decision_owner"], "semcod/koru")
        for extraction in self.inventory["extractions"]:
            with self.subTest(extraction=extraction["id"]):
                self.assertNotIn("semcod/koru", extraction["target_repositories"])

    def test_migration_order_is_unique_and_blockers_run_first(self) -> None:
        orders = {
            item["id"]: item["order"] for item in self.inventory["extractions"]
        }
        self.assertEqual(len(orders.values()), len(set(orders.values())))
        for extraction in self.inventory["extractions"]:
            for blocker in extraction["blocked_by"]:
                with self.subTest(extraction=extraction["id"], blocker=blocker):
                    self.assertLess(orders[blocker], extraction["order"])


if __name__ == "__main__":
    unittest.main()
