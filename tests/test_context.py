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
from koru.git_attribution import KORU_AGENT_COAUTHOR_TRAILER
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
        "sprint:\n  id: current\n  tickets: {}\n",
        encoding="utf-8",
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

    def test_autonomy_loop_brief_reads_telemetry_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_planfile(root)
            koru_dir = root / ".planfile" / ".koru"
            koru_dir.mkdir(parents=True, exist_ok=True)
            snap = {"cycle": 2, "knobs": {"scan_after_idle_queue": True}}
            (koru_dir / "autonomy-telemetry.json").write_text(
                json.dumps(snap),
                encoding="utf-8",
            )

            def planfile_runner(_c, _p):
                return _ok("No runnable ticket found.\n")

            ctx = build_context(
                project=root,
                planfile_runner=planfile_runner,
                git_probe=_no_git,
            )
            al = ctx.get("autonomy_loop") or {}
            self.assertEqual(al.get("last_run_snapshot", {}).get("cycle"), 2)
            self.assertIn("autonomy-telemetry.json", str(al.get("telemetry_file", "")))

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
            joined = " ".join(ctx["instructions"])
            self.assertIn("DO NOT ask the human what to work on", joined)
            self.assertIn("koru scan --apply", joined)

    def test_no_active_ticket_brief_compacts_traceback_error(self) -> None:
        ctx = {
            "project": "/tmp/project",
            "ticket": None,
            "ticket_error": "╭" * 400 + " Traceback most recent call last boom",
            "policy": {},
            "environment": {
                "planfile_initialised": True,
                "project": {"markers": {}},
            },
            "instructions": [],
        }

        brief = render_markdown_handoff(ctx)

        self.assertIn("## No active ticket — planfile error", brief)
        self.assertNotIn("╭" * 20, brief)

    def test_brief_when_queue_idle_ticket_next_json_null(self) -> None:
        """planfile ``ticket next --format json`` returns JSON ``null`` when idle."""
        sample = [
            {
                "id": "PLF-901",
                "name": "Idle list probe",
                "status": "open",
                "executor": {"kind": "shell"},
                "files": [],
            },
        ]

        with tempfile.TemporaryDirectory() as tmp:

            def planfile_runner(command, _project):
                if "next" in command:
                    return _ok("null\n")
                if "list" in command:
                    return _ok(json.dumps(sample))
                return _fail(f"unexpected planfile argv: {command!r}")

            _init_planfile(Path(tmp))
            ctx = build_context(
                project=Path(tmp),
                planfile_runner=planfile_runner,
                git_probe=_no_git,
            )
            self.assertIsNone(ctx["ticket"])
            self.assertEqual(ctx["ticket_error"], "queue is idle")
            self.assertEqual(ctx["all_tickets"], sample)

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
        # Capture every planfile invocation, not just the last one —
        # build_context may issue follow-up `ticket list` calls (to
        # populate `all_tickets` for the dashboard). The contract we
        # assert here is "the requested ticket was fetched via
        # `ticket show <id>`", which is independent of how many extra
        # bookkeeping calls happen afterwards.
        captured: list[list[str]] = []

        def planfile_runner(command, _project):
            captured.append(list(command))
            return _ok(json.dumps({"id": "PLF-074", "executor": {"kind": "shell"}}))

        with tempfile.TemporaryDirectory() as tmp:
            _init_planfile(Path(tmp))
            build_context(
                project=Path(tmp),
                ticket_id="PLF-074",
                planfile_runner=planfile_runner,
                git_probe=_no_git,
            )

        show_calls = [cmd for cmd in captured if "show" in cmd and "PLF-074" in cmd]
        self.assertTrue(
            show_calls,
            f"Expected at least one `ticket show PLF-074` call, got: {captured}",
        )

    def test_instructions_include_no_commit_rule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _init_planfile(Path(tmp))
            ctx = build_context(
                project=Path(tmp),
                planfile_runner=lambda _c, _p: _ok(
                    json.dumps(
                        {"id": "X", "executor": {"kind": "shell"}},
                    )
                ),
                git_probe=_no_git,
            )
            joined = " ".join(ctx["instructions"]).lower()
            self.assertIn("git commit", joined)
            self.assertIn("git push", joined)

    def test_instructions_include_koru_coauthor_trailer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _init_planfile(Path(tmp))
            ctx = build_context(
                project=Path(tmp),
                planfile_runner=lambda _c, _p: _ok(
                    json.dumps(
                        {"id": "X", "executor": {"kind": "shell"}},
                    )
                ),
                git_probe=_no_git,
            )
            joined = " ".join(ctx["instructions"])
            self.assertIn(KORU_AGENT_COAUTHOR_TRAILER, joined)

    def test_instructions_include_ci_command_when_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _init_planfile(Path(tmp))
            ctx = build_context(
                project=Path(tmp),
                policy=Policy(ci_command="pytest -q"),
                planfile_runner=lambda _c, _p: _ok(
                    json.dumps(
                        {"id": "X", "executor": {"kind": "shell"}},
                    )
                ),
                git_probe=_no_git,
            )
            joined = " ".join(ctx["instructions"])
            self.assertIn("pytest -q", joined)

    def test_self_service_includes_concrete_ticket_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _init_planfile(Path(tmp))
            ctx = build_context(
                project=Path(tmp),
                planfile_runner=lambda _c, _p: _ok(
                    json.dumps(
                        {"id": "PLF-100", "executor": {"kind": "shell"}},
                    )
                ),
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
                planfile_runner=lambda _c, _p: _ok(
                    json.dumps(
                        {"id": "X", "executor": {"kind": "shell"}},
                    )
                ),
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
                planfile_runner=lambda _c, _p: _ok(
                    json.dumps(
                        {
                            "id": "X",
                            "executor": {"kind": "shell"},
                            "files": ["src/a.py", "src/b.py"],
                        }
                    )
                ),
                git_probe=_no_git,
            )
            joined = " ".join(ctx["instructions"])
            self.assertIn("src/a.py", joined)

    # ------------------------------------------------------------------
    # Fixture-skip behaviour (PLF-koru improvement #4)
    # ------------------------------------------------------------------

    def test_fixture_tickets_are_skipped_by_default(self) -> None:
        """When the planfile queue contains only fixture tickets, the
        active ticket should be ``None`` and the error should explain why."""
        with tempfile.TemporaryDirectory() as tmp:
            _init_planfile(Path(tmp))
            queue = [
                {"id": "PLF-086", "status": "open", "labels": ["test-only", "dryrun"]},
                {"id": "PLF-090", "status": "open", "labels": ["synthetic", "auto-close"]},
            ]
            ctx = build_context(
                project=Path(tmp),
                planfile_runner=lambda _c, _p: _ok(json.dumps(queue)),
                git_probe=_no_git,
            )
            self.assertIsNone(ctx["ticket"])
            self.assertEqual(ctx["ticket_error"], "queue is idle")

    def test_real_ticket_picked_over_fixture_in_mixed_queue(self) -> None:
        """Mixed queue: agent must see the real ticket, not the fixture."""
        with tempfile.TemporaryDirectory() as tmp:
            _init_planfile(Path(tmp))
            queue = [
                {"id": "PLF-086", "status": "open", "labels": ["test-only", "dryrun"]},
                {"id": "PLF-093", "status": "open", "labels": ["bug", "ci"]},
            ]
            ctx = build_context(
                project=Path(tmp),
                planfile_runner=lambda _c, _p: _ok(json.dumps(queue)),
                git_probe=_no_git,
            )
            self.assertIsNotNone(ctx["ticket"])
            self.assertEqual(ctx["ticket"]["id"], "PLF-093")

    def test_include_fixtures_flag_brings_them_back(self) -> None:
        """`--include-fixtures` (CLI) maps to ``include_fixtures=True``."""
        with tempfile.TemporaryDirectory() as tmp:
            _init_planfile(Path(tmp))
            queue = [
                {"id": "PLF-086", "status": "open", "labels": ["test-only", "dryrun"]},
            ]
            ctx = build_context(
                project=Path(tmp),
                planfile_runner=lambda _c, _p: _ok(json.dumps(queue)),
                git_probe=_no_git,
                include_fixtures=True,
            )
            self.assertIsNotNone(ctx["ticket"])
            self.assertEqual(ctx["ticket"]["id"], "PLF-086")

    def test_single_object_fixture_is_filtered(self) -> None:
        """Legacy `ticket next` returns a single object; if it happens to
        be a fixture (e.g. SyntheticTest from monitor:test-heal), still
        suppress it from the active slot."""
        with tempfile.TemporaryDirectory() as tmp:
            _init_planfile(Path(tmp))
            fixture = {"id": "PLF-090", "status": "open", "labels": ["synthetic", "auto-close"]}
            ctx = build_context(
                project=Path(tmp),
                planfile_runner=lambda _c, _p: _ok(json.dumps(fixture)),
                git_probe=_no_git,
            )
            self.assertIsNone(ctx["ticket"])
            self.assertIn("fixture", (ctx["ticket_error"] or ""))

    def test_explicit_ticket_id_bypasses_fixture_filter(self) -> None:
        """When the user asks for a specific fixture (e.g. to debug the
        fixture rendering itself), they must always get it."""
        with tempfile.TemporaryDirectory() as tmp:
            _init_planfile(Path(tmp))
            fixture = {"id": "PLF-090", "status": "open", "labels": ["synthetic"]}
            ctx = build_context(
                project=Path(tmp),
                ticket_id="PLF-090",
                planfile_runner=lambda _c, _p: _ok(json.dumps(fixture)),
                git_probe=_no_git,
            )
            self.assertIsNotNone(ctx["ticket"])
            self.assertEqual(ctx["ticket"]["id"], "PLF-090")

    def test_all_tickets_are_populated_from_list(self) -> None:
        """The ``all_tickets`` field must be populated from the full queue
        listing, even when a specific ticket ID is requested."""
        with tempfile.TemporaryDirectory() as tmp:
            _init_planfile(Path(tmp))
            active_ticket = {"id": "PLF-101", "status": "open", "executor": {"kind": "shell"}}
            all_tickets_list = [
                active_ticket,
                {"id": "PLF-102", "status": "open", "executor": {"kind": "shell"}},
            ]

            captured_commands = []

            def planfile_runner(command, _project):
                captured_commands.append(command)
                if "show" in command:
                    return _ok(json.dumps(active_ticket))
                elif "list" in command:
                    return _ok(json.dumps(all_tickets_list))
                return _fail("unexpected planfile call")

            ctx = build_context(
                project=Path(tmp),
                ticket_id="PLF-101",
                planfile_runner=planfile_runner,
                git_probe=_no_git,
            )

            self.assertEqual(len(ctx["all_tickets"]), 2)
            self.assertEqual([t["id"] for t in ctx["all_tickets"]], ["PLF-101", "PLF-102"])

            # Verify that both 'show' and 'list' were called
            self.assertTrue(any("show" in cmd for cmd in captured_commands))
            self.assertTrue(any("list" in cmd for cmd in captured_commands))


class TestMarkdownHandoff(unittest.TestCase):
    def test_renders_koru_runtime_version_in_environment(self) -> None:
        ctx = {
            "project": "/tmp/project",
            "ticket": None,
            "ticket_error": "queue is idle",
            "policy": {},
            "environment": {
                "planfile_initialised": True,
                "project": {
                    "name": "project",
                    "cwd": "/tmp/project",
                    "python": "3.13.0",
                    "koru": {
                        "version": "9.9.9",
                        "executable": "/opt/koru/bin/koru",
                    },
                    "markers": {},
                },
            },
            "instructions": [],
        }

        md = render_markdown_handoff(ctx)

        self.assertIn("- **koru**: `9.9.9` (`/opt/koru/bin/koru`)", md)

    def test_renders_ticket_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _init_planfile(Path(tmp))
            ctx = build_context(
                project=Path(tmp),
                planfile_runner=lambda _c, _p: _ok(
                    json.dumps(
                        {
                            "id": "PLF-200",
                            "name": "Refactor X",
                            "status": "open",
                            "executor": {"kind": "shell"},
                            "files": ["a.py"],
                            "inputs": {"prompt": "Move helpers to utils"},
                        }
                    )
                ),
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
                planfile_runner=lambda _c, _p: _ok(
                    json.dumps(
                        {
                            "id": "X",
                            "executor": {"kind": "shell"},
                        }
                    )
                ),
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
            self.assertIn("Immediate action (autopilot)", md)
            self.assertIn("Do not ask the operator what to do next", md)
            self.assertIn("koru scan --apply", md)
            self.assertIn("Autonomous mode (one-command)", md)
            self.assertIn("koru autonomous up --project .", md)
            self.assertIn("Coverage note:", md)
            self.assertIn("AI tool support (2026)", md)
            self.assertIn("ai-tool-support-roadmap-2026.md", md)

    def test_autonomy_loop_brief_tolerates_non_dict_block(self) -> None:
        ctx = {
            "project": "/tmp/project",
            "ticket": None,
            "ticket_error": "queue is idle",
            "policy": {},
            "environment": {
                "planfile_initialised": True,
                "project": {"name": "project", "markers": {}},
            },
            "instructions": [],
            "autonomy_loop": "corrupt",
        }

        md = render_markdown_handoff(ctx)

        self.assertIn("Autonomy loop (koru autonomous)", md)
        self.assertIn("No autonomy telemetry file yet", md)


class TestProjectPipelineInHandoff(unittest.TestCase):
    def test_context_includes_pipeline_when_koru_yaml_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _init_planfile(project)
            (project / "koru.yaml").write_text(
                'schema: "1.0"\nwhen:\n  qa:\n'
                "    description: Run gates\n"
                "    commands:\n      - task quality:regix:local\n",
                encoding="utf-8",
            )

            def planfile_runner(_c, _p):
                return _ok("No runnable ticket found.\n")

            ctx = build_context(
                project=project,
                planfile_runner=planfile_runner,
                git_probe=_no_git,
            )
            self.assertIsNotNone(ctx["project_pipeline"])
            self.assertEqual(ctx["project_pipeline"]["schema"], "1.0")
            phases = ctx["project_pipeline"]["phases"]
            self.assertTrue(any(p["id"] == "qa" for p in phases))
            md = render_markdown_handoff(ctx)
            self.assertIn("Project pipeline", md)
            self.assertIn("task quality:regix:local", md)

    def test_pipeline_absent_without_koru_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _init_planfile(project)

            def planfile_runner(_c, _p):
                return _ok("No runnable ticket found.\n")

            ctx = build_context(
                project=project,
                planfile_runner=planfile_runner,
                git_probe=_no_git,
            )
            self.assertIsNone(ctx.get("project_pipeline"))


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
            self.assertIn("autonomous_bootstrap", ss)
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
            self.assertIn("Autonomous mode (one-command)", md)
            self.assertIn("koru autonomous up --project . --max-cycles 1", md)


if __name__ == "__main__":
    unittest.main()
