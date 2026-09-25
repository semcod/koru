"""Tests for atomized koru.scan_todo engine."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from koru.scan_todo import (
    count_todo_markers,
    count_todo_markers_in_project,
    is_koruignored,
    load_koruignore_patterns,
    scan_todo_markers,
)

_MARK_A = "TO" + "DO"
_MARK_B = "FIX" + "ME"
_MARK_C = "X" * 3
_MARK_D = "HA" + "CK"


def _marker_fixture(*names: str) -> str:
    return "".join(f"# {name}: marker\n" for name in names)


class TestScanTodoAtom(unittest.TestCase):
    def test_count_todo_markers_in_comments_only(self) -> None:
        # String literal with marker should not count
        code = f'msg = "{_MARK_A}: ignore this"\n# {_MARK_A}: count this\n'
        self.assertEqual(count_todo_markers(code), 1)

    def test_count_todo_markers_syntax_error_fallback(self) -> None:
        code = f"def invalid(:\n    # {_MARK_A}: a\n    # {_MARK_B}: b\n"
        self.assertEqual(count_todo_markers(code), 2)

    def test_load_koruignore_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / ".koruignore").write_text("# comment\n\nfoo/*.py\n./bar/\n/baz\n")
            patterns = load_koruignore_patterns(p)
            self.assertEqual(patterns, ("foo/*.py", "bar/", "baz"))

    def test_is_koruignored(self) -> None:
        patterns = ("ignored_dir/", "*.ignored.py", "exact_file.py")
        self.assertTrue(is_koruignored(Path("ignored_dir/sub/file.py"), patterns))
        self.assertTrue(is_koruignored(Path("sub/test.ignored.py"), patterns))
        self.assertTrue(is_koruignored(Path("exact_file.py"), patterns))
        self.assertFalse(is_koruignored(Path("valid/file.py"), patterns))

    def test_count_todo_markers_in_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "hot.py").write_text(_marker_fixture(_MARK_A, _MARK_B, _MARK_C))
            (project / "cold.py").write_text(_marker_fixture(_MARK_A))
            counts = count_todo_markers_in_project(project, min_per_file=2)
            self.assertIn("hot.py", counts)
            self.assertEqual(counts["hot.py"], 3)
            self.assertNotIn("cold.py", counts)

    def test_scan_todo_markers_returns_suggestions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "file.py").write_text(_marker_fixture(_MARK_A, _MARK_B, _MARK_C))
            suggestions = scan_todo_markers(project, min_per_file=3)
            self.assertEqual(len(suggestions), 1)
            self.assertEqual(suggestions[0].signal, "todo_markers")
            self.assertEqual(suggestions[0].priority, "low")
            self.assertIn("file.py", suggestions[0].title)
            self.assertEqual(suggestions[0].files, ("file.py",))
