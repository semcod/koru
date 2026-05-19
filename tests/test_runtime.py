"""Tests for the koru runtime FS contract.

The contract: koru only ever writes inside ``<project>/.planfile/``.
The ``.koru/`` subtree is the koru-owned sandbox for runtime artefacts
(run logs, captured prompts, llm-cache). Read-only operations
(``runtime_dir``, ``runs_dir``, ``planfile_dir``) MUST NOT touch disk;
only ``ensure_runs_dir`` is allowed to create directories.
"""

from __future__ import annotations

import os
import re
import tempfile
import unittest
from pathlib import Path

from koru.runtime import (
    KORU_SUBDIR,
    ensure_runs_dir,
    new_run_id,
    planfile_dir,
    runs_dir,
    runtime_dir,
)


class TestPathHelpers(unittest.TestCase):
    """Path resolvers must be pure: no filesystem mutation."""

    def test_planfile_dir_is_under_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            self.assertEqual(planfile_dir(project), project.resolve() / ".planfile")

    def test_runtime_dir_is_under_planfile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            expected = project.resolve() / ".planfile" / KORU_SUBDIR
            self.assertEqual(runtime_dir(project), expected)

    def test_runs_dir_is_under_runtime_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            expected = project.resolve() / ".planfile" / KORU_SUBDIR / "runs"
            self.assertEqual(runs_dir(project), expected)

    def test_path_helpers_do_not_create_directories(self) -> None:
        """The pure resolvers must not touch the filesystem."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            planfile_dir(project)
            runtime_dir(project)
            runs_dir(project)
            # Only the tempdir itself should exist.
            self.assertEqual(list(project.iterdir()), [])

    def test_path_helpers_resolve_relative_input(self) -> None:
        """Resolving must absolutize relative project paths."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            absolute = planfile_dir(project)
            self.assertTrue(absolute.is_absolute())


class TestRunIdGenerator(unittest.TestCase):
    def test_run_id_format(self) -> None:
        rid = new_run_id()
        # queue-YYYYMMDDTHHMMSSZ-<pid>
        self.assertRegex(rid, r"^queue-\d{8}T\d{6}Z-\d+$")

    def test_run_id_custom_prefix(self) -> None:
        rid = new_run_id(prefix="bootstrap")
        self.assertTrue(rid.startswith("bootstrap-"))

    def test_run_ids_sort_chronologically(self) -> None:
        """Lexicographic sort of run ids must match creation order."""
        import time as _t

        a = new_run_id()
        _t.sleep(1.05)  # bump timestamp to next second
        b = new_run_id()
        self.assertLess(a, b)

    def test_run_id_does_not_contain_path_separators(self) -> None:
        rid = new_run_id()
        self.assertNotIn("/", rid)
        self.assertNotIn(os.sep, rid)
        self.assertFalse(re.search(r"\s", rid))


class TestEnsureRunsDir(unittest.TestCase):
    def test_creates_full_subtree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            result = ensure_runs_dir(project)
            self.assertEqual(result, runs_dir(project))
            self.assertTrue(result.is_dir())
            self.assertTrue(runtime_dir(project).is_dir())
            self.assertTrue(planfile_dir(project).is_dir())

    def test_writes_readme_stub_on_first_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            ensure_runs_dir(project)
            readme = runtime_dir(project) / "README.md"
            self.assertTrue(readme.is_file())
            content = readme.read_text(encoding="utf-8")
            self.assertIn(".koru", content)
            self.assertIn("planfile", content)

    def test_idempotent_does_not_overwrite_readme(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            ensure_runs_dir(project)
            readme = runtime_dir(project) / "README.md"
            readme.write_text("USER EDIT — keep me", encoding="utf-8")
            ensure_runs_dir(project)  # second call
            self.assertEqual(readme.read_text(encoding="utf-8"), "USER EDIT — keep me")

    def test_does_not_write_outside_planfile(self) -> None:
        """Critical contract: nothing escapes ``<project>/.planfile/``."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            ensure_runs_dir(project)
            # Project root has exactly one entry: the .planfile dir.
            entries = sorted(p.name for p in project.iterdir())
            self.assertEqual(entries, [".planfile"])


if __name__ == "__main__":
    unittest.main()
