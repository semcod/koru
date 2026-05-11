"""Tests for ``koru.context.build_context`` and the markdown handoff.

The brief is the LLM's only source of truth for what is allowed —
its schema and content must be deterministic and contain the
mandatory rules verbatim.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from koru.context import build_context, render_markdown_handoff
from koru.policy import Policy


def _ok(stdout: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=0, stdout=stdout, stderr="")


def _fail(stderr: str = "boom") -> SimpleNamespace:
    return SimpleNamespace(returncode=1, stdout="", stderr=stderr)


def _no_git(_project: Path) -> dict:
    return {"branch": None, "head": None, "dirty": False, "remote": None}


def _init_planfile(project: Path) -> None:
    """Create marker files so build_context sees the project as initialised.

    The pre-flight check requires BOTH ``.planfile/config.yaml`` AND
    at least one sprint YAML, so the helper creates both.
    """
    pf = project / ".planfile"
    (pf / "sprints").mkdir(parents=True, exist_ok=True)
    (pf / "config.yaml").write_text("project: test\n", encoding="utf-8")
    (pf / "sprints" / "current.yaml").write_text(
        "sprint:\n  id: current\n  tickets: {}\n", encoding="utf-8"
    )


class TestBuildContext(unittest.TestCase):
    def test_brief_with_runnable_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _init_planfile(Path(tmp))
            ticket = {
                "id": "PLF-074",
                "name": "Verify OPENROUTER_API_KEY",
                "status": "open",
                "executor": {"kind": "shell"},
                "files": ["README.md"],
                "inputs": {"prompt": "Check key presence"},
            }

            def planfile_runner(_command, _project):
                return _ok(json.dumps(ticket))

            ctx = build_context(
                project=Path(tmp),
                planfile_runner=planfile_runner,
                git_probe=_no_git,
            )

            self.assertEqual(ctx["schema_version"], "1")
            self.assertEqual(ctx["ticket"]["id"], "PLF-074")
            self.assertIsNone(ctx["ticket_error"])
            self.assertEqual(ctx["policy"]["allow_commit"], False)
            self.assertEqual(ctx["policy"]["allow_push"], False)

    def test_brief_when_queue_idle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _init_planfile(Path(tmp))
            def planfile_runner(_c, _p):
                return _ok("No runnable ticket found.\n")

            ctx = build_context(
                project=Path(tmp),
                planfile_runner=planfile_runner,
                git_probe=_no_git,
            )
            self.assertIsNone(ctx["ticket"])
            self.assertEqual(ctx["ticket_error"], "queue is idle")

    def test_brief_when_planfile_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _init_planfile(Path(tmp))
            def planfile_runner(_c, _p):
                return _fail("planfile config not found")

            ctx = build_context(
                project=Path(tmp),
                planfile_runner=planfile_runner,
                git_probe=_no_git,
            )
            self.assertIsNone(ctx["ticket"])
            self.assertIn("planfile", ctx["ticket_error"].lower())

    def test_specific_ticket_uses_show(self) -> None:
        captured: dict[str, list[str]] = {}

        def planfile_runner(command, _project):
            captured["cmd"] = list(command)
            return _ok(json.dumps({"id": "PLF-074", "executor": {"kind": "shell"}}))

        with tempfile.TemporaryDirectory() as tmp:
            _init_planfile(Path(tmp))
            build_context(
                project=Path(tmp),
                ticket_id="PLF-074",
                planfile_runner=planfile_runner,
                git_probe=_no_git,
            )

        self.assertIn("show", captured["cmd"])
        self.assertIn("PLF-074", captured["cmd"])

    def test_instructions_include_no_commit_rule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _init_planfile(Path(tmp))
            ctx = build_context(
                project=Path(tmp),
                planfile_runner=lambda _c, _p: _ok(json.dumps(
                    {"id": "X", "executor": {"kind": "shell"}}
                )),
                git_probe=_no_git,
            )
            joined = " ".join(ctx["instructions"]).lower()
            self.assertIn("git commit", joined)
            self.assertIn("git push", joined)

    def test_instructions_include_ci_command_when_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _init_planfile(Path(tmp))
            ctx = build_context(
                project=Path(tmp),
                policy=Policy(ci_command="pytest -q"),
                planfile_runner=lambda _c, _p: _ok(json.dumps(
                    {"id": "X", "executor": {"kind": "shell"}}
                )),
                git_probe=_no_git,
            )
            joined = " ".join(ctx["instructions"])
            self.assertIn("pytest -q", joined)

    def test_self_service_includes_concrete_ticket_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _init_planfile(Path(tmp))
            ctx = build_context(
                project=Path(tmp),
                planfile_runner=lambda _c, _p: _ok(json.dumps(
                    {"id": "PLF-100", "executor": {"kind": "shell"}}
                )),
                git_probe=_no_git,
            )
            ss = ctx["self_service"]
            # Real planfile verbs only: start / done / block.
            self.assertIn("PLF-100", ss["start_this"])
            self.assertIn("PLF-100", ss["done_this"])
            self.assertIn("PLF-100", ss["block_this"])
            self.assertIn("ticket done", ss["done_this"])
            self.assertIn("ticket block", ss["block_this"])
            self.assertNotIn("complete", " ".join(ss.values()))
            self.assertNotIn("claim", " ".join(ss.values()))

    def test_brief_is_json_serialisable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _init_planfile(Path(tmp))
            ctx = build_context(
                project=Path(tmp),
                planfile_runner=lambda _c, _p: _ok(json.dumps(
                    {"id": "X", "executor": {"kind": "shell"}}
                )),
                git_probe=_no_git,
            )
            # Round-trip — must not raise.
            payload = json.dumps(ctx, sort_keys=True)
            self.assertIn('"schema_version"', payload)

    def test_files_in_scope_appear_in_instructions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _init_planfile(Path(tmp))
            ctx = build_context(
                project=Path(tmp),
                planfile_runner=lambda _c, _p: _ok(json.dumps({
                    "id": "X",
                    "executor": {"kind": "shell"},
                    "files": ["src/a.py", "src/b.py"],
                })),
                git_probe=_no_git,
            )
            joined = " ".join(ctx["instructions"])
            self.assertIn("src/a.py", joined)


class TestMarkdownHandoff(unittest.TestCase):
    def test_renders_ticket_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _init_planfile(Path(tmp))
            ctx = build_context(
                project=Path(tmp),
                planfile_runner=lambda _c, _p: _ok(json.dumps({
                    "id": "PLF-200",
                    "name": "Refactor X",
                    "status": "open",
                    "executor": {"kind": "shell"},
                    "files": ["a.py"],
                    "inputs": {"prompt": "Move helpers to utils"},
                })),
                git_probe=_no_git,
            )
            md = render_markdown_handoff(ctx)
            self.assertIn("PLF-200", md)
            self.assertIn("Refactor X", md)
            self.assertIn("Move helpers to utils", md)
            self.assertIn("`shell`", md)

    def test_renders_policy_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _init_planfile(Path(tmp))
            ctx = build_context(
                project=Path(tmp),
                planfile_runner=lambda _c, _p: _ok(json.dumps({
                    "id": "X", "executor": {"kind": "shell"},
                })),
                git_probe=_no_git,
            )
            md = render_markdown_handoff(ctx)
            self.assertIn("`allow_commit`", md)
            self.assertIn("`allow_push`", md)
            self.assertIn("`require_ci_pass_before_complete`", md)

    def test_renders_idle_brief_without_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _init_planfile(Path(tmp))
            ctx = build_context(
                project=Path(tmp),
                planfile_runner=lambda _c, _p: _ok("No runnable ticket found.\n"),
                git_probe=_no_git,
            )
            md = render_markdown_handoff(ctx)
            self.assertIn("No active ticket", md)


class TestSetupRequired(unittest.TestCase):
    """When planfile is not initialised, the brief must steer to koru --init."""

    def test_instructions_swap_to_setup_guide(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # No .planfile/ here — uninitialised project.
            ctx = build_context(
                project=Path(tmp),
                planfile_runner=lambda _c, _p: _fail("planfile not configured"),
                git_probe=_no_git,
            )
            joined = " ".join(ctx["instructions"]).lower()
            self.assertIn("koru --init", joined)
            self.assertIn("not been initialised", joined)
            # No DO NOT git commit rules — those only apply post-init.
            self.assertNotIn("git commit", joined)

    def test_self_service_exposes_init_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_context(
                project=Path(tmp),
                planfile_runner=lambda _c, _p: _fail(""),
                git_probe=_no_git,
            )
            ss = ctx["self_service"]
            self.assertIn("init_project", ss)
            self.assertIn("init_from_pipeline", ss)
            self.assertIn("refresh_brief", ss)
            # Planfile ticket commands must NOT leak — the agent cannot
            # use them yet.
            self.assertNotIn("claim_this", ss)
            self.assertNotIn("complete_this", ss)

    def test_environment_planfile_initialised_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_context(
                project=Path(tmp),
                planfile_runner=lambda _c, _p: _fail(""),
                git_probe=_no_git,
            )
            self.assertFalse(ctx["environment"]["planfile_initialised"])

    def test_markdown_renders_setup_required_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ctx = build_context(
                project=Path(tmp),
                planfile_runner=lambda _c, _p: _fail(""),
                git_probe=_no_git,
            )
            md = render_markdown_handoff(ctx)
            self.assertIn("Setup required", md)
            self.assertIn("koru --init --project .", md)


if __name__ == "__main__":
    unittest.main()
