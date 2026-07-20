"""CI contract for the autonomy namespace/capability inventory DSL."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from koru.queue.contracts import (
    CAP_PROMOTE_BRANCH,
    CAP_PROMOTE_MAIN,
    CAP_PROPOSE,
    CAP_STAGE,
)

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "docs/architecture/autonomy-mutation-inventory.yaml"
SCHEMA_PATH = ROOT / "schemas/autonomy-mutation-inventory.schema.json"


def _load_inventory() -> dict:
    return yaml.safe_load(INVENTORY_PATH.read_text(encoding="utf-8"))


def _declared_source_roots(inventory: dict) -> set[str]:
    return {
        root
        for namespace in inventory["namespaces"]
        for root in namespace["roots"]
    }


def _actual_source_roots(declared: set[str]) -> set[str]:
    def is_owned_source_root(path: Path) -> bool:
        relative = path.relative_to(ROOT).as_posix()
        # Editable installs may create empty namespace directories alongside
        # real package roots. They are not source ownership until they contain
        # Python sources; keep explicitly declared compatibility roots visible.
        return relative in declared or any(path.glob("*.py"))

    roots = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "src").iterdir()
        if path.is_dir()
        and not path.name.startswith(".")
        and not path.name.endswith(".egg-info")
        and path.name != "__pycache__"
        and is_owned_source_root(path)
    }
    for source_dir in (ROOT / "packages").glob("*/src"):
        roots.update(
            path.relative_to(ROOT).as_posix()
            for path in source_dir.iterdir()
            if path.is_dir()
            and not path.name.startswith(".")
            and not path.name.endswith(".egg-info")
            and path.name != "__pycache__"
            and is_owned_source_root(path)
        )
    return roots


class TestAutonomyMutationInventory(unittest.TestCase):
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

    def test_ids_are_unique_and_canonically_ordered(self) -> None:
        for section in ("namespaces", "capabilities", "mutation_entrypoints"):
            ids = [item["id"] for item in self.inventory[section]]
            with self.subTest(section=section):
                self.assertEqual(len(ids), len(set(ids)), "duplicate id")
                self.assertEqual(ids, sorted(ids), "keep the DSL diff deterministic")

    def test_every_import_root_has_one_declared_owner(self) -> None:
        declared = _declared_source_roots(self.inventory)
        occurrences = [
            root
            for namespace in self.inventory["namespaces"]
            for root in namespace["roots"]
        ]

        self.assertEqual(len(occurrences), len(declared), "source root has two owners")
        self.assertEqual(declared, _actual_source_roots(declared))
        for root in declared:
            self.assertTrue((ROOT / root).is_dir(), root)

    def test_capability_references_are_closed_and_entrypoints_are_real(self) -> None:
        namespace_ids = {item["id"] for item in self.inventory["namespaces"]}
        capability_ids = {item["id"] for item in self.inventory["capabilities"]}
        referenced_capabilities = {
            item["capability"] for item in self.inventory["mutation_entrypoints"]
        }

        self.assertTrue(
            all(item["owner"] in namespace_ids for item in self.inventory["capabilities"]),
        )
        self.assertEqual(referenced_capabilities, capability_ids)
        for entrypoint in self.inventory["mutation_entrypoints"]:
            for module in entrypoint["modules"]:
                with self.subTest(entrypoint=entrypoint["id"], module=module):
                    self.assertTrue((ROOT / module).is_file(), module)

    def test_queue_contract_constants_use_registered_contracted_capabilities(self) -> None:
        capabilities = {
            item["id"]: item for item in self.inventory["capabilities"]
        }
        queue_capabilities = {
            CAP_PROPOSE,
            CAP_STAGE,
            CAP_PROMOTE_BRANCH,
            CAP_PROMOTE_MAIN,
        }

        self.assertTrue(queue_capabilities <= capabilities.keys())
        for capability in queue_capabilities:
            with self.subTest(capability=capability):
                self.assertEqual(capabilities[capability]["enforcement"], "contracted")

    def test_entrypoint_enforcement_cannot_exceed_capability_enforcement(self) -> None:
        enforcement = {
            item["id"]: item["enforcement"]
            for item in self.inventory["capabilities"]
        }
        for entrypoint in self.inventory["mutation_entrypoints"]:
            with self.subTest(entrypoint=entrypoint["id"]):
                if entrypoint["enforcement"] == "contracted":
                    self.assertEqual(
                        enforcement[entrypoint["capability"]],
                        "contracted",
                    )


if __name__ == "__main__":
    unittest.main()
