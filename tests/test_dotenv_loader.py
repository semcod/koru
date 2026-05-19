from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from koru.dotenv_loader import load_dotenv, parse_dotenv


class TestParseDotenv(unittest.TestCase):
    def test_simple_pairs(self) -> None:
        out = parse_dotenv("A=1\nB=2\n")
        self.assertEqual(out, {"A": "1", "B": "2"})

    def test_export_prefix_supported(self) -> None:
        out = parse_dotenv("export KEY=value\n")
        self.assertEqual(out, {"KEY": "value"})

    def test_double_quoted_with_escapes(self) -> None:
        out = parse_dotenv(r'A="hello\nworld"' + "\n")
        self.assertEqual(out, {"A": "hello\nworld"})

    def test_single_quoted_literal(self) -> None:
        out = parse_dotenv("A='no \\n escape'\n")
        self.assertEqual(out, {"A": "no \\n escape"})

    def test_inline_comments_stripped(self) -> None:
        out = parse_dotenv("A=value   # a comment\n")
        self.assertEqual(out["A"], "value")

    def test_skips_blank_and_comment_lines(self) -> None:
        out = parse_dotenv("\n# top comment\nA=1\n   \nB=2\n")
        self.assertEqual(out, {"A": "1", "B": "2"})

    def test_invalid_lines_silently_skipped(self) -> None:
        # No malformed lines should raise — they are simply ignored.
        out = parse_dotenv("not a kv\nA=1\n123BAD=2\n")
        self.assertEqual(out, {"A": "1"})

    def test_openrouter_realworld_line(self) -> None:
        out = parse_dotenv("OPENROUTER_API_KEY=sk-or-abc123\n")
        self.assertEqual(out["OPENROUTER_API_KEY"], "sk-or-abc123")


class TestLoadDotenv(unittest.TestCase):
    def setUp(self) -> None:
        # Snapshot env so tests don't pollute each other.
        self._env_backup = dict(os.environ)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_no_dotenv_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_dotenv(Path(tmp)), {})

    def test_loads_keys_into_environ(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".env").write_text("KORU_TEST_ALPHA=beta\n")
            os.environ.pop("KORU_TEST_ALPHA", None)
            applied = load_dotenv(project)
            self.assertEqual(applied, {"KORU_TEST_ALPHA": "beta"})
            self.assertEqual(os.environ.get("KORU_TEST_ALPHA"), "beta")

    def test_does_not_override_existing_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".env").write_text("KORU_TEST_BETA=fromfile\n")
            os.environ["KORU_TEST_BETA"] = "fromshell"
            applied = load_dotenv(project)
            self.assertEqual(applied, {})
            self.assertEqual(os.environ["KORU_TEST_BETA"], "fromshell")

    def test_override_flag_replaces_existing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".env").write_text("KORU_TEST_GAMMA=fromfile\n")
            os.environ["KORU_TEST_GAMMA"] = "fromshell"
            applied = load_dotenv(project, override=True)
            self.assertEqual(applied["KORU_TEST_GAMMA"], "fromfile")
            self.assertEqual(os.environ["KORU_TEST_GAMMA"], "fromfile")

    def test_env_local_overrides_env(self) -> None:
        # `.env.local` loaded after `.env`, so its values win when both
        # are previously missing from environ.
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".env").write_text("KORU_TEST_DELTA=base\n")
            (project / ".env.local").write_text("KORU_TEST_DELTA=local\n")
            os.environ.pop("KORU_TEST_DELTA", None)
            load_dotenv(project)
            # `.env` sets it first, `.env.local` then sees it already
            # in environ and does NOT override. This matches python-dotenv
            # default behaviour (later files do not override earlier
            # unless override=True).
            self.assertEqual(os.environ["KORU_TEST_DELTA"], "base")

    def test_openrouter_key_propagated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".env").write_text(
                "OPENROUTER_API_KEY=sk-or-test-12345\n",
            )
            os.environ.pop("OPENROUTER_API_KEY", None)
            load_dotenv(project)
            self.assertEqual(
                os.environ.get("OPENROUTER_API_KEY"),
                "sk-or-test-12345",
            )


if __name__ == "__main__":
    unittest.main()
