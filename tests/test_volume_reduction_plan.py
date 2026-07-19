"""CI contract for the map-driven Koru volume-reduction plan."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "docs/architecture/volume-reduction-plan.yaml"
SCHEMA_PATH = ROOT / "schemas/volume-reduction-plan.schema.json"
BOUNDARY_INVENTORY_PATH = ROOT / "docs/architecture/dependency-boundary-inventory.yaml"


class TestVolumeReductionPlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan = yaml.safe_load(PLAN_PATH.read_text(encoding="utf-8"))
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_plan_matches_json_schema(self) -> None:
        Draft202012Validator.check_schema(self.schema)
        errors = sorted(
            Draft202012Validator(self.schema).iter_errors(self.plan),
            key=lambda error: tuple(str(part) for part in error.absolute_path),
        )
        self.assertEqual(
            errors,
            [],
            "\n".join(f"{list(error.absolute_path)}: {error.message}" for error in errors),
        )

    def test_baseline_matches_index_header(self) -> None:
        baseline = self.plan["baseline"]
        header = (ROOT / baseline["map_path"]).read_text(encoding="utf-8").splitlines()[:6]
        summary = re.search(r"\| (\d+)f (\d+)L .*python:(\d+)", header[0])
        stats = re.search(r"critical:(\d+) \| cycles:(\d+)", header[2])
        self.assertIsNotNone(summary)
        self.assertIsNotNone(stats)
        self.assertEqual(
            (baseline["indexed_files"], baseline["indexed_lines"], baseline["python_modules"]),
            tuple(map(int, summary.groups())),
        )
        self.assertEqual(
            (baseline["critical_functions"], baseline["dependency_cycles"]),
            tuple(map(int, stats.groups())),
        )

    def test_sources_exist_and_stage_references_are_closed(self) -> None:
        stages = {stage["id"]: stage for stage in self.plan["stages"]}
        self.assertEqual(len(stages), len(self.plan["stages"]), "duplicate stage id")
        orders = [stage["order"] for stage in self.plan["stages"]]
        self.assertEqual(len(orders), len(set(orders)), "duplicate stage order")
        for stage in self.plan["stages"]:
            self.assertTrue(stage["target_available"], stage["id"])
            self.assertLessEqual(stage["minimum_production_lines_removed"], stage["candidate_lines"])
            self.assertLessEqual(stage["minimum_checkout_lines_removed"], stage["candidate_lines"])
            for source in stage["source_paths"]:
                with self.subTest(stage=stage["id"], source=source):
                    source_path = ROOT / source
                    if stage["status"] == "complete" and stage["action"] == "move_to_test_support":
                        self.assertFalse(source_path.exists(), source)
                        self.assertTrue((ROOT / "tests/fakes" / source_path.name).is_dir(), source)
                    else:
                        self.assertTrue(source_path.exists(), source)
            for blocker in stage["blocked_by"]:
                with self.subTest(stage=stage["id"], blocker=blocker):
                    self.assertIn(blocker, stages)
                    self.assertLess(stages[blocker]["order"], stage["order"])

    def test_moves_do_not_claim_ecosystem_deletion(self) -> None:
        for stage in self.plan["stages"]:
            with self.subTest(stage=stage["id"]):
                if stage["action"] == "move_to_dependency":
                    self.assertEqual(stage["ecosystem_lines_deleted"], 0)
                    self.assertNotIn("semcod/koru", stage["target_owners"])
                if stage["action"] == "delete_duplicate":
                    self.assertGreater(stage["ecosystem_lines_deleted"], 0)

    def test_target_owners_are_closed_against_boundary_inventory(self) -> None:
        boundary = yaml.safe_load(BOUNDARY_INVENTORY_PATH.read_text(encoding="utf-8"))
        known = {repository["id"] for repository in boundary["repositories"]}
        known.update({"ci/artifact-store", "tests/fakes"})
        for stage in self.plan["stages"]:
            with self.subTest(stage=stage["id"]):
                self.assertLessEqual(set(stage["target_owners"]), known)

    def test_targets_are_real_reductions(self) -> None:
        baseline = self.plan["baseline"]
        targets = self.plan["targets"]
        self.assertLess(targets["indexed_lines_max"], baseline["indexed_lines"])
        self.assertLess(targets["python_modules_max"], baseline["python_modules"])
        self.assertLess(targets["tracked_repository_bytes_max"], baseline["tracked_repository_bytes"])

    def test_test_doubles_are_explicitly_test_only(self) -> None:
        import tomllib

        config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        pythonpath = config["tool"]["pytest"]["ini_options"]["pythonpath"]
        self.assertLess(pythonpath.index("tests/fakes"), pythonpath.index("src"))


if __name__ == "__main__":
    unittest.main()
