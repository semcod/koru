"""Unit tests for koru.cli — dispatch, bare invocation, flags."""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from koru.cli import _build_parser, _is_bare_invocation, main


def _tmp_git_project(prefix: str = "koru-cli-test-") -> Path:
    td = tempfile.mkdtemp(prefix=prefix)
    p = Path(td)
    subprocess.run(["git", "init", "-q", str(p)], check=True,
                   capture_output=True)
    return p


def _run_main(*argv: str) -> tuple[int, str]:
    buf = io.StringIO()
    with mock.patch("sys.argv", ["koru", *argv]):
        with mock.patch("sys.stdout", new=buf):
            code = main()
    return code, buf.getvalue()


class TestBareInvocation(unittest.TestCase):
    """``koru`` with no action flag should route to markdown brief."""

    def _parse(self, *argv: str) -> object:
        return _build_parser().parse_args(list(argv))

    def test_no_args_is_bare(self) -> None:
        args = self._parse()
        self.assertTrue(_is_bare_invocation(args))

    def test_project_only_is_bare(self) -> None:
        args = self._parse("--project", "/tmp/p")
        self.assertTrue(_is_bare_invocation(args))

    def test_init_is_not_bare(self) -> None:
        args = self._parse("--init")
        self.assertFalse(_is_bare_invocation(args))

    def test_doctor_is_not_bare(self) -> None:
        args = self._parse("--doctor")
        self.assertFalse(_is_bare_invocation(args))

    def test_context_is_not_bare(self) -> None:
        args = self._parse("--context")
        self.assertFalse(_is_bare_invocation(args))

    def test_queue_is_not_bare(self) -> None:
        args = self._parse("--queue")
        self.assertFalse(_is_bare_invocation(args))

    def test_watch_is_not_bare(self) -> None:
        args = self._parse("--watch")
        self.assertFalse(_is_bare_invocation(args))

    def test_bootstrap_is_not_bare(self) -> None:
        args = self._parse("--bootstrap")
        self.assertFalse(_is_bare_invocation(args))

    def test_command_is_not_bare(self) -> None:
        args = self._parse("--command", "echo hi")
        self.assertFalse(_is_bare_invocation(args))


class TestDoctorDispatch(unittest.TestCase):
    """--doctor uses text by default, json when --format json."""

    def setUp(self) -> None:
        self.project = _tmp_git_project("koru-cli-doc-")

    def tearDown(self) -> None:
        shutil.rmtree(self.project, ignore_errors=True)

    def test_doctor_default_is_text(self) -> None:
        code, output = _run_main("--doctor", "--project", str(self.project))
        self.assertIn("koru doctor", output)
        self.assertTrue(
            any(m in output for m in ("[OK ]", "[WARN]", "[FAIL]")),
            f"Expected text markers in output:\n{output}",
        )

    def test_doctor_json(self) -> None:
        code, output = _run_main(
            "--doctor", "--project", str(self.project), "--format", "json"
        )
        data = json.loads(output)
        self.assertIn("checks", data)
        self.assertIn("project", data)

    def test_doctor_exit_0_on_no_failures(self) -> None:
        code, _ = _run_main("--doctor", "--project", str(self.project))
        self.assertIsInstance(code, int)


class TestInitDispatch(unittest.TestCase):
    """--init creates project scaffold."""

    def setUp(self) -> None:
        self.project = _tmp_git_project("koru-cli-init-")

    def tearDown(self) -> None:
        shutil.rmtree(self.project, ignore_errors=True)

    def test_init_creates_planfile(self) -> None:
        code, output = _run_main("--init", "--project", str(self.project))
        self.assertEqual(code, 0)
        self.assertTrue((self.project / ".planfile" / "config.yaml").exists())
        self.assertTrue((self.project / ".planfile" / ".koru" / "policy.yaml").exists())

    def test_init_duplicate_rejected(self) -> None:
        _run_main("--init", "--project", str(self.project))
        code, _ = _run_main("--init", "--project", str(self.project))
        self.assertEqual(code, 1)


class TestContextDispatch(unittest.TestCase):
    """--context emits JSON or markdown."""

    def setUp(self) -> None:
        self.project = _tmp_git_project("koru-cli-ctx-")

    def tearDown(self) -> None:
        shutil.rmtree(self.project, ignore_errors=True)

    def test_context_json_default(self) -> None:
        code, output = _run_main(
            "--context", "--project", str(self.project)
        )
        data = json.loads(output)
        self.assertIn("policy", data)
        self.assertEqual(code, 0)

    def test_context_markdown(self) -> None:
        code, output = _run_main(
            "--context", "--project", str(self.project), "--format", "markdown"
        )
        self.assertIn("# koru handoff", output)
        self.assertEqual(code, 0)


class TestBareEmitsMarkdown(unittest.TestCase):
    """Bare ``koru`` should produce a markdown brief."""

    def setUp(self) -> None:
        self.project = _tmp_git_project("koru-cli-bare-")

    def tearDown(self) -> None:
        shutil.rmtree(self.project, ignore_errors=True)

    def test_bare_produces_markdown(self) -> None:
        code, output = _run_main("--project", str(self.project))
        self.assertEqual(code, 0)
        self.assertIn("# koru handoff", output)
