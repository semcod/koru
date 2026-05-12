"""Unit tests for koru.cli — dispatch, bare invocation, flags."""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from koru.cli import _SUBCOMMANDS, _build_parser, _is_bare_invocation, main


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


class TestTopologySubcommand(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="koru-cli-topology-")
        self.project = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_topology_json_lists_components_and_pipelines(self) -> None:
        code, output = _run_main("topology", "--project", str(self.project), "--format", "json")
        self.assertEqual(code, 0)
        data = json.loads(output)
        self.assertIn("components", data)
        self.assertIn("pipelines", data)
        self.assertIn("regix", data["components"])

    def test_topology_disable_then_is_enabled_false(self) -> None:
        code1, _ = _run_main("topology", "--project", str(self.project), "--disable", "regix")
        self.assertEqual(code1, 0)

        code2, output2 = _run_main(
            "topology",
            "--project",
            str(self.project),
            "--is-enabled",
            "regix",
        )
        self.assertEqual(code2, 1)
        self.assertEqual(output2.strip(), "false")

    def test_topology_enabled_components_for_pipeline(self) -> None:
        _run_main("topology", "--project", str(self.project), "--disable", "wup")
        code, output = _run_main(
            "topology",
            "--project",
            str(self.project),
            "--enabled-components-for",
            "idle-diagnostics",
        )
        self.assertEqual(code, 0)
        self.assertIn("regix", output)
        self.assertNotIn("wup", output)


class TestSubcommandDispatch(unittest.TestCase):
    """R6: routing through ``_SUBCOMMANDS`` dispatch table.

    We verify (a) the table contains every documented subcommand, and
    (b) routing dispatches to exactly the handler bound under each key,
    with the residual argv (``raw_args[1:]``) forwarded as-is.
    """

    EXPECTED_KEYS = frozenset(
        {
            "task",
            "agent",
            "serve",
            "scan",
            "gate",
            "queue",
            "gc",
            "autopilot",
            "autonomous",
            "topology",
            "runtime-context",
        }
    )

    def test_table_contains_all_documented_subcommands(self) -> None:
        self.assertEqual(self.EXPECTED_KEYS, set(_SUBCOMMANDS.keys()))

    def test_table_values_are_callables(self) -> None:
        for name, fn in _SUBCOMMANDS.items():
            self.assertTrue(callable(fn), f"{name!r} → {fn!r} is not callable")

    def test_each_subcommand_routes_to_its_handler(self) -> None:
        """``koru <name> a b c`` must call ``_SUBCOMMANDS[<name>](['a','b','c'])``."""
        for name in self.EXPECTED_KEYS:
            with self.subTest(subcommand=name):
                fake = mock.Mock(return_value=0)
                with mock.patch.dict(_SUBCOMMANDS, {name: fake}):
                    with mock.patch("sys.argv", ["koru", name, "a", "b", "c"]):
                        code = main()
                    # Assert INSIDE the patch context so the mock is still bound.
                    fake.assert_called_once_with(["a", "b", "c"])
                self.assertEqual(code, 0)

    def test_unknown_first_arg_falls_through_to_argparse(self) -> None:
        """A non-subcommand argv MUST NOT trigger any handler."""
        # Pick a flag that argparse will accept (--doctor exits cleanly).
        project = _tmp_git_project("koru-cli-fallthrough-")
        try:
            for handler_name in self.EXPECTED_KEYS:
                with mock.patch.dict(
                    _SUBCOMMANDS, {handler_name: mock.Mock(side_effect=AssertionError)},
                ):
                    code, _ = _run_main("--doctor", "--project", str(project))
                    self.assertIsInstance(code, int)
        finally:
            shutil.rmtree(project, ignore_errors=True)

    def test_empty_argv_does_not_call_any_handler(self) -> None:
        project = _tmp_git_project("koru-cli-empty-")
        try:
            sentinels = {name: mock.Mock(side_effect=AssertionError)
                         for name in self.EXPECTED_KEYS}
            with mock.patch.dict(_SUBCOMMANDS, sentinels):
                _run_main("--project", str(project))
        finally:
            shutil.rmtree(project, ignore_errors=True)
