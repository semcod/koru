"""Unit tests for the flat-pipeline bootstrap loader/validator/materialiser."""

from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

import yaml

from koru.bootstrap import (
    ImportReport,
    ValidationError,
    import_flat_pipeline,
    load_flat_pipeline,
    materialize_to_planfile,
    validate_flat_pipeline,
)


def _write_yaml(path: Path, content: str) -> None:
    path.write_text(textwrap.dedent(content), encoding="utf-8")


VALID_PIPELINE = """\
schema: '1.1'
project: bootstrap-test
description: Test pipeline
tasks:
  - id: T-001
    name: First task
    priority: high
    status: open
    executor:
      kind: shell
      mode: automatic
      handler: "echo hello"
    execution:
      state: ready
  - id: T-002
    name: Second task
    blocked_by: [T-001]
    executor:
      kind: human
      mode: interactive
    execution:
      state: pending
    inputs:
      prompt: "Need value"
"""


class TestLoadFlatPipeline(unittest.TestCase):
    def test_loads_header_and_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            yaml_path = Path(tmp) / "p.yaml"
            _write_yaml(yaml_path, VALID_PIPELINE)
            header, tasks = load_flat_pipeline(yaml_path)
            self.assertEqual(header["schema"], "1.1")
            self.assertEqual(header["project"], "bootstrap-test")
            self.assertEqual(len(tasks), 2)
            self.assertEqual(tasks[0]["id"], "T-001")

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_flat_pipeline("/nonexistent/path.yaml")

    def test_missing_tasks_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            yaml_path = Path(tmp) / "p.yaml"
            _write_yaml(yaml_path, "project: x\nversion: 0\n")
            with self.assertRaisesRegex(ValueError, "missing top-level 'tasks'"):
                load_flat_pipeline(yaml_path)


class TestValidateFlatPipeline(unittest.TestCase):
    def test_valid_pipeline_has_no_errors(self) -> None:
        _, tasks = self._load(VALID_PIPELINE)
        self.assertEqual(validate_flat_pipeline(tasks), [])

    def test_missing_id_reported(self) -> None:
        _, tasks = self._load("""\
            tasks:
              - name: No id
                executor: {kind: shell, handler: "true"}
        """)
        errors = validate_flat_pipeline(tasks)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].field, "id")

    def test_duplicate_id_reported(self) -> None:
        _, tasks = self._load("""\
            tasks:
              - id: T-1
                name: A
                executor: {kind: shell, handler: x}
              - id: T-1
                name: B
                executor: {kind: shell, handler: y}
        """)
        errors = validate_flat_pipeline(tasks)
        self.assertTrue(any(e.message == "duplicate" for e in errors))

    def test_invalid_executor_kind(self) -> None:
        _, tasks = self._load("""\
            tasks:
              - id: T-1
                name: x
                executor: {kind: martian, handler: x}
        """)
        errors = validate_flat_pipeline(tasks)
        self.assertTrue(any(e.field == "executor.kind" for e in errors))

    def test_invalid_priority_reported(self) -> None:
        _, tasks = self._load("""\
            tasks:
              - id: T-1
                name: x
                priority: urgent
                executor: {kind: shell, handler: x}
        """)
        errors = validate_flat_pipeline(tasks)
        self.assertTrue(any(e.field == "priority" for e in errors))

    def test_unknown_blocked_by_reference(self) -> None:
        _, tasks = self._load("""\
            tasks:
              - id: T-1
                name: x
                blocked_by: [T-DOES-NOT-EXIST]
                executor: {kind: shell, handler: x}
        """)
        errors = validate_flat_pipeline(tasks)
        self.assertTrue(any("unknown task id" in e.message for e in errors))

    def test_cycle_detected(self) -> None:
        _, tasks = self._load("""\
            tasks:
              - id: T-1
                name: A
                blocked_by: [T-2]
                executor: {kind: shell, handler: x}
              - id: T-2
                name: B
                blocked_by: [T-1]
                executor: {kind: shell, handler: y}
        """)
        errors = validate_flat_pipeline(tasks)
        self.assertTrue(any("cycle detected" in e.message for e in errors))

    def _load(self, src: str) -> tuple[dict, list[dict]]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.yaml"
            _write_yaml(path, src)
            return load_flat_pipeline(path)


class TestMaterializeToPlanfile(unittest.TestCase):
    def test_creates_planfile_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            yaml_path = project / "pipeline.yaml"
            _write_yaml(yaml_path, VALID_PIPELINE)
            _, tasks = load_flat_pipeline(yaml_path)

            report = materialize_to_planfile(tasks, project)

            self.assertIsInstance(report, ImportReport)
            self.assertEqual(report.tickets_imported, ["T-001", "T-002"])
            self.assertTrue(report.config_created)
            self.assertTrue(report.sprint_file_created)

            config_path = project / ".planfile" / "config.yaml"
            sprint_path = project / ".planfile" / "sprints" / "current.yaml"
            self.assertTrue(config_path.exists())
            self.assertTrue(sprint_path.exists())

            sprint_data = yaml.safe_load(sprint_path.read_text())
            tickets = sprint_data["sprint"]["tickets"]
            self.assertIn("T-001", tickets)
            self.assertIn("T-002", tickets)

    def test_default_execution_state_ready_for_unblocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            yaml_path = project / "p.yaml"
            _write_yaml(
                yaml_path,
                """\
                tasks:
                  - id: T-1
                    name: solo
                    executor: {kind: shell, handler: x}
                """,
            )
            _, tasks = load_flat_pipeline(yaml_path)
            materialize_to_planfile(tasks, project)
            sprint = yaml.safe_load(
                (project / ".planfile" / "sprints" / "current.yaml").read_text(),
            )
            self.assertEqual(sprint["sprint"]["tickets"]["T-1"]["execution"]["state"], "ready")

    def test_default_execution_state_pending_for_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            yaml_path = project / "p.yaml"
            _write_yaml(
                yaml_path,
                """\
                tasks:
                  - id: T-1
                    name: blocker
                    executor: {kind: shell, handler: x}
                  - id: T-2
                    name: blocked
                    blocked_by: [T-1]
                    executor: {kind: shell, handler: y}
                """,
            )
            _, tasks = load_flat_pipeline(yaml_path)
            materialize_to_planfile(tasks, project)
            sprint = yaml.safe_load(
                (project / ".planfile" / "sprints" / "current.yaml").read_text(),
            )
            self.assertEqual(sprint["sprint"]["tickets"]["T-1"]["execution"]["state"], "ready")
            self.assertEqual(
                sprint["sprint"]["tickets"]["T-2"]["execution"]["state"],
                "pending",
            )

    def test_overwrite_protection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            yaml_path = project / "p.yaml"
            _write_yaml(yaml_path, VALID_PIPELINE)
            _, tasks = load_flat_pipeline(yaml_path)
            materialize_to_planfile(tasks, project)
            with self.assertRaises(FileExistsError):
                materialize_to_planfile(tasks, project)
            # With overwrite=True it succeeds.
            report2 = materialize_to_planfile(tasks, project, overwrite=True)
            self.assertTrue(report2.sprint_file_overwritten)


class TestImportFlatPipeline(unittest.TestCase):
    def test_full_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            yaml_path = Path(tmp) / "pipeline.yaml"
            _write_yaml(yaml_path, VALID_PIPELINE)

            report = import_flat_pipeline(yaml_path, project)
            self.assertEqual(len(report.tickets_imported), 2)

    def test_invalid_pipeline_raises_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            yaml_path = Path(tmp) / "pipeline.yaml"
            _write_yaml(
                yaml_path,
                """\
                tasks:
                  - id: T-1
                    name: bad
                    executor: {kind: martian, handler: x}
                """,
            )
            with self.assertRaisesRegex(ValueError, "validation failed"):
                import_flat_pipeline(yaml_path, project)


class TestImportReport(unittest.TestCase):
    def test_summary_includes_key_facts(self) -> None:
        report = ImportReport(
            project_dir=Path("/tmp/x"),
            sprint="current",
            tickets_imported=["T-1", "T-2"],
            config_created=True,
            sprint_file_created=True,
        )
        summary = report.summary()
        self.assertIn("tickets: 2", summary)
        self.assertIn("config", summary)
        self.assertIn("sprint", summary)


class TestValidationError(unittest.TestCase):
    def test_str_format(self) -> None:
        err = ValidationError("T-1", "executor.kind", "missing")
        self.assertEqual(str(err), "T-1: executor.kind: missing")


if __name__ == "__main__":
    unittest.main()
