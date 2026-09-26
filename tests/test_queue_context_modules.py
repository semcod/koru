"""Focused tests for the split queue context responsibility modules.

PLF-029/PLF-039 split ``koru.queue.context`` into
``context_exclusions`` (security policy), ``context_files`` (selection +
safe reads) and ``context_slicing`` (focused slices) behind the stable
``context`` facade. These tests pin the moved behavior at its new homes
plus the facade re-export surface. End-to-end assembly behavior stays
covered by ``tests/test_llm_context.py``.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import koru.queue.context as context_facade
from koru.queue import context_exclusions, context_files, context_slicing


def _oversized(pad_lines: int = 400) -> str:
    """Return filler text safely above LARGE_FILE_SLICE_THRESHOLD_CHARS."""
    return "# padding line with plenty of characters to exceed the slice threshold\n" * pad_lines


class TestFacadeSurface(unittest.TestCase):
    """PLF-039: every pre-split import path keeps resolving on the facade."""

    def test_moved_callables_are_the_same_objects(self):
        self.assertIs(context_facade._is_excluded, context_exclusions._is_excluded)
        self.assertIs(
            context_facade._resolve_target_symbol_and_line,
            context_slicing._resolve_target_symbol_and_line,
        )
        self.assertIs(
            context_facade._focused_file_slice, context_slicing._focused_file_slice
        )
        self.assertIs(
            context_facade._extract_python_symbol_slice,
            context_slicing._extract_python_symbol_slice,
        )
        self.assertIs(
            context_facade._extract_line_slice, context_slicing._extract_line_slice
        )
        self.assertIs(
            context_facade._context_files_to_include,
            context_files._context_files_to_include,
        )
        self.assertIs(
            context_facade._context_nothing_requested,
            context_files._context_nothing_requested,
        )
        self.assertIs(
            context_facade._read_file_content, context_files._read_file_content
        )
        self.assertIs(context_facade._read_file_tree, context_files._read_file_tree)
        self.assertIs(
            context_facade._collect_auto_files, context_files._collect_auto_files
        )
        self.assertIs(
            context_facade._collect_glob_files, context_files._collect_glob_files
        )

    def test_constants_and_result_type_still_importable(self):
        self.assertEqual(context_facade.DEFAULT_MAX_CONTEXT_CHARS, 32_000)
        self.assertEqual(context_facade.LARGE_FILE_SLICE_THRESHOLD_CHARS, 12_000)
        self.assertTrue(callable(context_facade.build_project_context))
        result = context_facade.ContextResult(text="x")
        self.assertEqual(result.text, "x")
        self.assertEqual(result.included_files, [])
        self.assertFalse(result.truncated)

    def test_runner_import_binding_unchanged(self):
        from koru.queue import runner

        self.assertIs(runner.build_project_context, context_facade.build_project_context)


class TestIsExcludedRules(unittest.TestCase):
    """context_exclusions: policy edges pinned at the new home."""

    def test_suffix_check_is_case_insensitive(self):
        self.assertTrue(context_exclusions._is_excluded("certs/server.PEM"))
        self.assertTrue(context_exclusions._is_excluded("backup.Env"))

    def test_excluded_directory_component_anywhere(self):
        self.assertTrue(context_exclusions._is_excluded("deploy/secrets/api.yaml"))
        self.assertTrue(context_exclusions._is_excluded("a/b/node_modules/pkg.js"))

    def test_glob_only_patterns(self):
        self.assertTrue(context_exclusions._is_excluded("trace.log"))
        self.assertTrue(context_exclusions._is_excluded(".coverage"))
        self.assertTrue(context_exclusions._is_excluded("reports/coverage.xml"))
        self.assertTrue(context_exclusions._is_excluded("staging.env.local"))

    def test_normal_project_files_pass(self):
        for rel in ("src/app.py", "README.md", "docs/guide.txt", "pkg/lib.js"):
            self.assertFalse(context_exclusions._is_excluded(rel), rel)


class TestContextFilesSelection(unittest.TestCase):
    """context_files: request-driven selection ordering and filtering."""

    def test_nothing_requested_truth_table(self):
        self.assertTrue(context_files._context_nothing_requested({}))
        self.assertTrue(context_files._context_nothing_requested({"prompt": "hi"}))
        self.assertTrue(
            context_files._context_nothing_requested({"include_project_context": False})
        )
        self.assertFalse(
            context_files._context_nothing_requested({"include_project_context": True})
        )
        self.assertFalse(
            context_files._context_nothing_requested({"context_files": ["a.txt"]})
        )
        self.assertFalse(
            context_files._context_nothing_requested({"context_globs": ["*"]})
        )
        self.assertFalse(
            context_files._context_nothing_requested({"ticket_files": ["t.py"]})
        )

    def test_ticket_targets_precede_convenience_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "src").mkdir()
            for rel in ("ticket_target.py", "notes.txt", "src/mod.py", "README.md"):
                (project / rel).write_text("content\n", encoding="utf-8")
            request = {
                "include_project_context": True,
                "context_files": ["notes.txt", ".env", "ticket_target.py"],
                "context_globs": ["src/*.py"],
                "ticket_files": ["ticket_target.py"],
            }
            selected = context_files._context_files_to_include(project, request)
            self.assertEqual(
                selected,
                ["ticket_target.py", "notes.txt", "src/mod.py", "README.md"],
            )

    def test_glob_expansion_dedups_and_filters(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "src").mkdir()
            for rel in ("src/a.py", "src/b.py", "src/.env", "root.py"):
                (project / rel).write_text("x\n", encoding="utf-8")
            found = context_files._collect_glob_files(
                project, ["src/*", "src/a.py", "*.py"]
            )
            self.assertEqual(found, ["src/a.py", "src/b.py", "root.py"])


class TestReadFileContent(unittest.TestCase):
    """context_files: safe reads."""

    def test_roundtrip_missing_and_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "ok.txt").write_text("payload\n", encoding="utf-8")
            (project / ".env").write_text("SECRET=1\n", encoding="utf-8")
            self.assertEqual(
                context_files._read_file_content(project, "ok.txt"), "payload\n"
            )
            self.assertIsNone(
                context_files._read_file_content(project, "missing.txt")
            )
            self.assertIsNone(context_files._read_file_content(project, ".env"))

    def test_path_escape_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            outside = project.parent / "context_escape_probe.txt"
            try:
                outside.write_text("leaked\n", encoding="utf-8")
                self.assertIsNone(
                    context_files._read_file_content(project, "../context_escape_probe.txt")
                )
            finally:
                outside.unlink(missing_ok=True)


class TestReadFileTree(unittest.TestCase):
    """context_files: bounded, filtered directory listing."""

    def test_exclusions_and_truncation_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "src").mkdir()
            (project / ".git").mkdir()
            (project / "src").joinpath("a.py").write_text("x\n", encoding="utf-8")
            (project / ".git").joinpath("config").write_text("x\n", encoding="utf-8")
            (project / "root.txt").write_text("x\n", encoding="utf-8")
            tree = context_files._read_file_tree(project, max_entries=2)
            self.assertIn("root.txt", tree)
            self.assertIn("listing truncated at 2 entries", tree)
            self.assertNotIn(".git", tree)


class TestExtractPythonSymbolSlice(unittest.TestCase):
    """context_slicing: AST window extraction."""

    CODE = (
        "import os\n"
        "import sys\n"
        "\n"
        "\n"
        "def target():\n"
        "    return 1\n"
        "\n"
        "\n"
        "def other():\n"
        "    return 2\n"
    )

    def test_slice_contains_imports_marker_and_span(self):
        code_slice = context_slicing._extract_python_symbol_slice(self.CODE, "target")
        self.assertIsNotNone(code_slice)
        assert code_slice is not None
        self.assertEqual(code_slice.start_line, 1)  # clamped at file start
        self.assertEqual(code_slice.end_line, 10)
        self.assertIn("import os", code_slice.text)
        self.assertIn("focused AST slice for 'target'", code_slice.text)
        self.assertIn("def target():", code_slice.text)

    def test_unknown_symbol_returns_none(self):
        self.assertIsNone(
            context_slicing._extract_python_symbol_slice(self.CODE, "no_such")
        )

    def test_syntax_error_returns_none(self):
        self.assertIsNone(
            context_slicing._extract_python_symbol_slice("def (broken\n", "broken")
        )


class TestExtractLineSlice(unittest.TestCase):
    """context_slicing: line-window clamping."""

    def test_window_clamped_at_file_boundaries(self):
        content = "\n".join(f"line {i}" for i in range(1, 21))
        head = context_slicing._extract_line_slice(content, 2, window=5)
        self.assertEqual((head.start_line, head.end_line), (1, 7))
        tail = context_slicing._extract_line_slice(content, 19, window=5)
        self.assertEqual((tail.start_line, tail.end_line), (14, 20))
        self.assertIn("focused slice around line 19", tail.text)


class TestFocusedFileSlice(unittest.TestCase):
    """context_slicing: threshold routing in _focused_file_slice."""

    def test_small_file_returned_unchanged(self):
        focused = context_slicing._focused_file_slice(
            "small.py", "x = 1\n", "py", {"target_symbol": "x"}
        )
        self.assertEqual(focused.content, "x = 1\n")
        self.assertIsNone(focused.note)

    def test_oversized_without_request_returned_unchanged(self):
        big = _oversized()
        self.assertGreater(len(big), context_slicing.LARGE_FILE_SLICE_THRESHOLD_CHARS)
        focused = context_slicing._focused_file_slice("big.txt", big, "txt", None)
        self.assertEqual(focused.content, big)
        self.assertIsNone(focused.note)

    def test_oversized_with_symbol_unknown_falls_back_unchanged(self):
        big = _oversized()
        focused = context_slicing._focused_file_slice(
            "big.py", big, "py", {"target_symbol": "no_such_symbol"}
        )
        self.assertEqual(focused.content, big)
        self.assertIsNone(focused.note)

    def test_oversized_python_symbol_produces_slice_note(self):
        code = "import os\n\n" + _oversized(300) + "def target_heavy():\n    return 42\n"
        focused = context_slicing._focused_file_slice(
            "big.py", code, "py", {"target_symbol": "target_heavy"}
        )
        self.assertIn("focused slice for 'target_heavy'", focused.note or "")
        self.assertIn("def target_heavy():", focused.content)
        self.assertLess(len(focused.content), len(code))

    def test_oversized_line_target_produces_line_note(self):
        big = _oversized()
        focused = context_slicing._focused_file_slice(
            "big.txt", big, "txt", {"target_line": 100}
        )
        self.assertIn("focused slice around line 100", focused.note or "")

    def test_non_python_symbol_without_line_returns_unchanged(self):
        big = _oversized()
        focused = context_slicing._focused_file_slice(
            "big.rb", big, "rb", {"target_symbol": "some_method"}
        )
        self.assertEqual(focused.content, big)
        self.assertIsNone(focused.note)


class TestResolveTargetSymbolAndLine(unittest.TestCase):
    """context_slicing: target metadata resolution."""

    def test_explicit_metadata_passthrough(self):
        target = context_slicing._resolve_target_symbol_and_line(
            "src/app.py", {"target_symbol": "run_all", "target_line": 42}
        )
        self.assertEqual((target.symbol, target.line), ("run_all", 42))

    def test_prompt_path_line_marker_without_symbol(self):
        target = context_slicing._resolve_target_symbol_and_line(
            "src/koru/queue/context.py", {"prompt": "see src/koru/queue/context.py:581"}
        )
        self.assertIsNone(target.symbol)
        self.assertEqual(target.line, 581)

    def test_prompt_cc_pattern_resolves_symbol(self):
        target = context_slicing._resolve_target_symbol_and_line(
            "mod.py", {"prompt": "`heavy_worker` with CC=19 is too complex."}
        )
        self.assertEqual(target.symbol, "heavy_worker")

    def test_digit_and_single_char_candidates_rejected(self):
        target = context_slicing._resolve_target_symbol_and_line(
            "mod.py", {"prompt": "Function '999' and def 'a' are not symbols."}
        )
        self.assertIsNone(target.symbol)

    def test_empty_request_yields_empty_ref(self):
        target = context_slicing._resolve_target_symbol_and_line("mod.py", {})
        self.assertEqual((target.symbol, target.line), (None, None))


if __name__ == "__main__":
    unittest.main()
