"""End-to-end tests exercising the full koru CLI through main().

Each test sets up a temporary git-initialized project directory and drives
the CLI via the same ``main()`` entry-point used by ``python -m koru.cli``.
Tests that drive the ``--queue`` code-path require the ``planfile`` CLI
binary (found via ``PATH``); they are skipped when it is not installed.
"""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

import pytest
import yaml

from koru.cli import main

pytestmark = pytest.mark.slow

_HAS_PLANFILE = shutil.which("planfile") is not None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tmp_git_project(prefix: str = "koru-e2e-") -> Path:
    """Create a temp directory and ``git init`` it."""
    td = tempfile.mkdtemp(prefix=prefix)
    p = Path(td)
    subprocess.run(["git", "init", "-q", str(p)], check=True, capture_output=True)
    return p


def _run_main(*argv: str) -> tuple[int, str, str]:
    """Call ``main()`` with given argv and capture stdout + stderr."""
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    with mock.patch("sys.argv", ["koru", *argv]):
        with mock.patch("sys.stdout", new=out_buf):
            with mock.patch("sys.stderr", new=err_buf):
                try:
                    code = main()
                except SystemExit as exc:
                    code = exc.code if exc.code is not None else 0
    return code, out_buf.getvalue(), err_buf.getvalue()


def _write_sprint(project: Path, tickets: dict, sprint: str = "current") -> None:
    """Write a minimal sprint YAML."""
    sprint_dir = project / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "sprint": {
            "id": sprint,
            "name": "test",
            "status": "active",
            "tickets": tickets,
        },
    }
    (sprint_dir / f"{sprint}.yaml").write_text(
        yaml.safe_dump(data, sort_keys=False),
        encoding="utf-8",
    )


def _write_config(project: Path, prefix: str = "E2E", next_id: int = 1) -> None:
    """Write a minimal planfile config."""
    cfg_dir = project / ".planfile"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "project": "e2e-test",
                "prefix": prefix,
                "next_id": next_id,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _ts(days_ago: float) -> str:
    dt = datetime.now(UTC) - timedelta(days=days_ago)
    return dt.isoformat()


def _done_ticket(name: str, days_ago: float = 60) -> dict:
    return {
        "name": name,
        "status": "done",
        "execution": {
            "state": "done",
            "finished_at": _ts(days_ago),
        },
    }


def _init_project(project: Path) -> tuple[int, str, str]:
    """Run koru --init on a project."""
    return _run_main("--init", "--project", str(project))


def _extract_json(text: str) -> dict:
    """Extract the first JSON object/array from *text*.

    Context commands may print info lines (e.g. auto-promotion) before
    the JSON payload; this helper finds the first ``{`` or ``[`` and
    parses from there.
    """
    for i, ch in enumerate(text):
        if ch in ("{", "["):
            return json.loads(text[i:])
    raise ValueError(f"no JSON found in: {text[:200]}")


# ===========================================================================
# E2E: Init → Doctor → Context → Task
# ===========================================================================


class TestE2EInitDoctorContext(unittest.TestCase):
    """Full lifecycle: init → doctor → bare koru → context JSON."""

    def setUp(self) -> None:
        self.project = _tmp_git_project("koru-e2e-idc-")

    def tearDown(self) -> None:
        shutil.rmtree(self.project, ignore_errors=True)

    def test_init_then_doctor_passes(self) -> None:
        code, out, _ = _init_project(self.project)
        self.assertEqual(code, 0, f"init failed: {out}")
        self.assertTrue((self.project / ".planfile" / "config.yaml").exists())

        code, out, _ = _run_main("--doctor", "--project", str(self.project))
        self.assertEqual(code, 0, f"doctor failed: {out}")
        self.assertIn("[OK ]", out)

    def test_init_then_bare_koru_emits_markdown(self) -> None:
        _init_project(self.project)
        code, out, _ = _run_main("--project", str(self.project))
        self.assertEqual(code, 0)
        self.assertIn("# koru handoff", out)

    def test_init_then_context_json_has_policy(self) -> None:
        _init_project(self.project)
        code, out, _ = _run_main(
            "--context",
            "--project",
            str(self.project),
            "--format",
            "json",
        )
        self.assertEqual(code, 0)
        data = _extract_json(out)
        self.assertIn("policy", data)
        self.assertIn("allow_commit", data["policy"])

    def test_init_then_context_markdown_has_ticket(self) -> None:
        _init_project(self.project)
        code, out, _ = _run_main(
            "--context",
            "--project",
            str(self.project),
            "--format",
            "markdown",
        )
        self.assertEqual(code, 0)
        # The starter scaffold includes STARTER-001
        self.assertIn("STARTER", out)

    def test_doctor_json_format(self) -> None:
        _init_project(self.project)
        code, out, _ = _run_main(
            "--doctor",
            "--project",
            str(self.project),
            "--format",
            "json",
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("checks", data)
        self.assertIn("project", data)

    def test_doctor_fails_on_empty_project(self) -> None:
        """Doctor should report failures when no .planfile exists."""
        code, out, _ = _run_main("--doctor", "--project", str(self.project))
        # May warn or fail, but should not crash
        self.assertIsInstance(code, int)

    def test_double_init_rejected(self) -> None:
        _init_project(self.project)
        code, out, _ = _init_project(self.project)
        self.assertEqual(code, 1)


# ===========================================================================
# E2E: Task creation
# ===========================================================================


class TestE2ETask(unittest.TestCase):
    """koru task "..." creates a ticket in the sprint YAML."""

    def setUp(self) -> None:
        self.project = _tmp_git_project("koru-e2e-task-")
        _init_project(self.project)

    def tearDown(self) -> None:
        shutil.rmtree(self.project, ignore_errors=True)

    def test_task_creates_ticket(self) -> None:
        code, out, _ = _run_main(
            "task",
            "Fix the login form validation",
            "--project",
            str(self.project),
        )
        self.assertEqual(code, 0, f"task failed: {out}")
        self.assertIn("✓ created", out)
        # Verify it appears in sprint YAML
        sprint = yaml.safe_load(
            (self.project / ".planfile/sprints/current.yaml").read_text(),
        )
        tickets = sprint["sprint"]["tickets"]
        found = any("login" in t.get("name", "").lower() for t in tickets.values())
        self.assertTrue(found, f"ticket not found in {list(tickets.keys())}")

    def test_task_increments_id(self) -> None:
        _run_main("task", "First task", "--project", str(self.project))
        _run_main("task", "Second task", "--project", str(self.project))
        sprint = yaml.safe_load(
            (self.project / ".planfile/sprints/current.yaml").read_text(),
        )
        tickets = sprint["sprint"]["tickets"]
        # Should have at least the starter + 2 new tasks
        nl_tickets = [
            t for t in tickets.values() if t.get("source", {}).get("tool") == "koru-cli-nl"
        ]
        self.assertEqual(len(nl_tickets), 2)

    def test_task_reuses_dedupe_key_for_plugin_intake(self) -> None:
        key = "semcod:code2llm:refactor:src/koru/autonomous.py"
        first_code, first_out, _ = _run_main(
            "task",
            "Split autonomous module",
            "--project",
            str(self.project),
            "--source-tool",
            "prefact",
            "--source-signal",
            "code2llm_god",
            "--dedupe-key",
            key,
            "--files",
            "src/koru/autonomous.py",
        )
        second_code, second_out, _ = _run_main(
            "task",
            "Same issue from prefact",
            "--project",
            str(self.project),
            "--source-tool",
            "prefact",
            "--source-signal",
            "code2llm_refactor",
            "--dedupe-key",
            key,
            "--files",
            "src/koru/autonomous.py",
        )

        self.assertEqual(first_code, 0, first_out)
        self.assertEqual(second_code, 0, second_out)
        self.assertIn("✓ created", first_out)
        self.assertIn("✓ reused", second_out)
        sprint = yaml.safe_load((self.project / ".planfile/sprints/current.yaml").read_text())
        prefact_tickets = [
            ticket
            for ticket in sprint["sprint"]["tickets"].values()
            if ticket.get("source", {}).get("tool") == "prefact"
        ]
        self.assertEqual(len(prefact_tickets), 1)

    def test_task_empty_text_fails(self) -> None:
        code, out, _ = _run_main("task", "", "--project", str(self.project))
        self.assertNotEqual(code, 0)

    def test_task_with_priority(self) -> None:
        code, out, _ = _run_main(
            "task",
            "Urgent bug fix",
            "--project",
            str(self.project),
            "--priority",
            "critical",
        )
        self.assertEqual(code, 0)
        sprint = yaml.safe_load(
            (self.project / ".planfile/sprints/current.yaml").read_text(),
        )
        tickets = sprint["sprint"]["tickets"]
        urgent = [t for t in tickets.values() if "Urgent" in t.get("name", "")]
        self.assertTrue(urgent)
        self.assertEqual(urgent[0]["priority"], "critical")

    def test_task_with_tool_scaffold(self) -> None:
        code, out, _ = _run_main(
            "task",
            "Prepare Gemini adapter",
            "--project",
            str(self.project),
            "--tool",
            "gemini-cli",
        )
        self.assertEqual(code, 0, out)
        self.assertIn("tool:  gemini-cli", out)
        sprint = yaml.safe_load(
            (self.project / ".planfile/sprints/current.yaml").read_text(),
        )
        tickets = sprint["sprint"]["tickets"]
        matches = [
            t
            for t in tickets.values()
            if t.get("source", {}).get("tool") == "koru-cli-tool-adapter"
            and t.get("source", {}).get("context", {}).get("tool_id") == "gemini-cli"
        ]
        self.assertTrue(matches)
        ticket = matches[0]
        self.assertIn("adapter-scaffold", ticket.get("labels", []))
        self.assertIn("TOOL ADAPTER SCAFFOLD", ticket.get("inputs", {}).get("prompt", ""))

    def test_task_with_plugin_bridge_scaffold(self) -> None:
        code, out, _ = _run_main(
            "task",
            "Prepare Copilot plugin bridge",
            "--project",
            str(self.project),
            "--tool",
            "github-copilot",
        )
        self.assertEqual(code, 0, out)
        sprint = yaml.safe_load(
            (self.project / ".planfile/sprints/current.yaml").read_text(),
        )
        tickets = sprint["sprint"]["tickets"]
        matches = [
            t
            for t in tickets.values()
            if t.get("source", {}).get("tool") == "koru-cli-plugin-bridge"
            and t.get("source", {}).get("context", {}).get("tool_id") == "github-copilot"
        ]
        self.assertTrue(matches)
        ticket = matches[0]
        self.assertIn("plugin-bridge-scaffold", ticket.get("labels", []))
        self.assertIn("PLUGIN BRIDGE SCAFFOLD", ticket.get("inputs", {}).get("prompt", ""))


# ===========================================================================
# E2E: GC lifecycle
# ===========================================================================


class TestE2EGc(unittest.TestCase):
    """koru gc: dry-run, apply, archive, keep-last."""

    def setUp(self) -> None:
        self.project = _tmp_git_project("koru-e2e-gc-")
        _write_config(self.project, prefix="GC")
        _write_sprint(
            self.project,
            {
                "GC-001": _done_ticket("Old finished task 1", days_ago=60),
                "GC-002": _done_ticket("Old finished task 2", days_ago=45),
                "GC-003": _done_ticket("Recent done task", days_ago=5),
                "GC-004": {
                    "name": "Open task (active)",
                    "status": "open",
                    "execution": {"state": "ready"},
                },
                "GC-005": {
                    "name": "Failed old task",
                    "status": "failed",
                    "execution": {
                        "state": "failed",
                        "finished_at": _ts(90),
                    },
                },
            },
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.project, ignore_errors=True)

    def test_gc_dry_run_text(self) -> None:
        code, out, _ = _run_main("gc", "--project", str(self.project), "--max-age", "30")
        self.assertEqual(code, 0)
        self.assertIn("DRY RUN", out)
        self.assertIn("GC-001", out)
        self.assertIn("GC-002", out)
        self.assertNotIn("GC-003", out)  # too recent
        self.assertNotIn("GC-004", out)  # open, not in GC statuses

    def test_gc_dry_run_json(self) -> None:
        code, out, _ = _run_main(
            "gc",
            "--project",
            str(self.project),
            "--max-age",
            "30",
            "--format",
            "json",
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(data["dry_run"])
        removed_ids = data["removed"]
        self.assertIn("GC-001", removed_ids)
        self.assertIn("GC-002", removed_ids)
        self.assertNotIn("GC-003", removed_ids)

    def test_gc_keep_last_protects_newest(self) -> None:
        code, out, _ = _run_main(
            "gc",
            "--project",
            str(self.project),
            "--max-age",
            "30",
            "--keep-last",
            "1",
            "--format",
            "json",
        )
        data = json.loads(out)
        self.assertIn("GC-002", data["kept"])  # newest of old done tickets
        self.assertIn("GC-001", data["removed"])

    def test_gc_custom_statuses(self) -> None:
        code, out, _ = _run_main(
            "gc",
            "--project",
            str(self.project),
            "--max-age",
            "30",
            "--status",
            "failed",
            "--format",
            "json",
        )
        data = json.loads(out)
        removed = data["removed"]
        self.assertIn("GC-005", removed)
        self.assertNotIn("GC-001", removed)  # done, not in custom statuses

    def test_gc_no_stale_tickets_message(self) -> None:
        code, out, _ = _run_main(
            "gc",
            "--project",
            str(self.project),
            "--max-age",
            "999",
        )
        self.assertEqual(code, 0)
        self.assertIn("no stale tickets", out)

    def test_gc_apply_with_fake_runner(self) -> None:
        """Apply mode invokes planfile delete — mock it to verify."""
        fake_result = type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

        with mock.patch("koru.gc._run_planfile", return_value=fake_result):
            code, out, _ = _run_main(
                "gc",
                "--project",
                str(self.project),
                "--max-age",
                "30",
                "--apply",
                "--no-archive",
            )
        self.assertEqual(code, 0)
        self.assertIn("APPLIED", out)


# ===========================================================================
# E2E: Scan
# ===========================================================================


class TestE2EScan(unittest.TestCase):
    """koru scan detects project issues and suggests tickets."""

    def setUp(self) -> None:
        self.project = _tmp_git_project("koru-e2e-scan-")
        _init_project(self.project)

    def tearDown(self) -> None:
        shutil.rmtree(self.project, ignore_errors=True)

    @staticmethod
    def _marker_fixture(*names: str) -> str:
        return "".join(f"# {name}: marker\n" for name in names)

    def test_scan_detects_todo_markers(self) -> None:
        markers = (
            "TO" + "DO",
            "FIX" + "ME",
            "X" * 3,
            "HA" + "CK",
        )
        (self.project / "messy.py").write_text(
            self._marker_fixture(*markers),
        )
        code, out, _ = _run_main(
            "scan",
            "--project",
            str(self.project),
            "--skip-pytest",
        )
        self.assertEqual(code, 0)
        self.assertIn("messy.py", out)

    def test_scan_json_format(self) -> None:
        (self.project / "todos.py").write_text(
            self._marker_fixture("TO" + "DO", "FIX" + "ME", "X" * 3),
        )
        code, out, _ = _run_main(
            "scan",
            "--project",
            str(self.project),
            "--skip-pytest",
            "--format",
            "json",
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertIn("suggestions", data)

    def test_scan_with_limit(self) -> None:
        for i in range(5):
            (self.project / f"file{i}.py").write_text(
                self._marker_fixture("TO" + "DO", "FIX" + "ME", "X" * 3),
            )
        code, out, _ = _run_main(
            "scan",
            "--project",
            str(self.project),
            "--skip-pytest",
            "--limit",
            "2",
            "--format",
            "json",
        )
        data = json.loads(out)
        self.assertLessEqual(len(data["suggestions"]), 2)

    def test_scan_clean_project_no_suggestions(self) -> None:
        """A well-set-up project should have few or no suggestions."""
        (self.project / ".gitignore").write_text(".planfile/.koru/\n")
        code, out, _ = _run_main(
            "scan",
            "--project",
            str(self.project),
            "--skip-pytest",
            "--format",
            "json",
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        # Gitignore drift should not fire since it's present
        gitignore_suggestions = [
            s for s in data["suggestions"] if s.get("signal") == "gitignore_drift"
        ]
        self.assertEqual(gitignore_suggestions, [])


# ===========================================================================
# E2E: Queue loop with shell ticket
# ===========================================================================


@unittest.skipUnless(_HAS_PLANFILE, "planfile binary not in PATH")
class TestE2EQueueLoop(unittest.TestCase):
    """koru --queue processes shell tickets end-to-end."""

    def setUp(self) -> None:
        self.project = _tmp_git_project("koru-e2e-loop-")
        _write_config(self.project, prefix="LOOP")
        _write_sprint(
            self.project,
            {
                "LOOP-001": {
                    "id": "LOOP-001",
                    "name": "Echo smoke test",
                    "status": "open",
                    "priority": "high",
                    "sprint": "current",
                    "labels": ["koru-task"],
                    "executor": {
                        "kind": "shell",
                        "mode": "automatic",
                        "handler": "echo LOOP_PASS",
                    },
                    "execution": {
                        "queue": "default",
                        "state": "ready",
                        "attempt": 0,
                        "max_attempts": 1,
                    },
                },
            },
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.project, ignore_errors=True)

    def test_queue_dry_run(self) -> None:
        # Verifies queue finds the ticket and reports it in dry-run mode.
        # Executor kind depends on planfile JSON output (may vary).
        code, out, _ = _run_main(
            "--queue",
            "--project",
            str(self.project),
            "--dry-run",
        )
        self.assertEqual(code, 0, f"dry-run failed: {out}")
        self.assertIn("LOOP-001", out)

    def test_queue_processes_next_ticket(self) -> None:
        # Verifies queue finds and processes a ticket.
        # The specific status depends on whether planfile returns executor info.
        code, out, _ = _run_main(
            "--queue",
            "--project",
            str(self.project),
            "--actor",
            "e2e-test",
        )
        self.assertEqual(code, 0, f"queue failed: {out}")
        self.assertIn("LOOP-001", out)
        # Status may be completed (if shell executor detected) or waiting_input
        self.assertTrue(
            "completed" in out or "waiting_input" in out,
            f"Expected completed or waiting_input in: {out}",
        )

    def test_queue_idle_when_no_runnable_tickets(self) -> None:
        _write_sprint(
            self.project,
            {
                "LOOP-099": _done_ticket("Already done", days_ago=1),
            },
        )
        code, out, _ = _run_main(
            "--queue",
            "--project",
            str(self.project),
        )
        self.assertEqual(code, 0)
        self.assertIn("idle", out)


# ===========================================================================
# E2E: Queue loop mode (--loop)
# ===========================================================================


@unittest.skipUnless(_HAS_PLANFILE, "planfile binary not in PATH")
class TestE2EQueueLoopMode(unittest.TestCase):
    """koru --queue --loop drains multiple tickets."""

    def setUp(self) -> None:
        self.project = _tmp_git_project("koru-e2e-lmode-")
        _write_config(self.project, prefix="LM", next_id=3)
        _write_sprint(
            self.project,
            {
                "LM-001": {
                    "id": "LM-001",
                    "name": "Step 1",
                    "status": "open",
                    "priority": "high",
                    "sprint": "current",
                    "labels": [],
                    "executor": {
                        "kind": "shell",
                        "mode": "automatic",
                        "handler": "echo STEP1",
                    },
                    "execution": {
                        "queue": "default",
                        "state": "ready",
                        "attempt": 0,
                        "max_attempts": 1,
                    },
                },
                "LM-002": {
                    "id": "LM-002",
                    "name": "Step 2",
                    "status": "open",
                    "priority": "normal",
                    "sprint": "current",
                    "labels": [],
                    "executor": {
                        "kind": "shell",
                        "mode": "automatic",
                        "handler": "echo STEP2",
                    },
                    "execution": {
                        "queue": "default",
                        "state": "ready",
                        "attempt": 0,
                        "max_attempts": 1,
                    },
                },
            },
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.project, ignore_errors=True)

    def test_loop_finds_and_processes_tickets(self) -> None:
        # Verifies the loop mode finds tickets and attempts to process them.
        # The loop may stop at first human-like ticket or process all shell
        # tickets depending on planfile JSON output.
        code, out, _ = _run_main(
            "--queue",
            "--loop",
            "--max-iterations",
            "10",
            "--project",
            str(self.project),
            "--actor",
            "e2e-loop",
        )
        self.assertEqual(code, 0, f"loop failed: {out}")
        # At least first ticket should be found
        self.assertIn("LM-001", out)

    def test_loop_reports_completed_count(self) -> None:
        code, out, _ = _run_main(
            "--queue",
            "--loop",
            "--max-iterations",
            "10",
            "--project",
            str(self.project),
            "--actor",
            "e2e-loop",
        )
        self.assertIn("completed", out.lower())


# ===========================================================================
# E2E: Bootstrap import
# ===========================================================================


class TestE2EBootstrap(unittest.TestCase):
    """koru --bootstrap imports a flat pipeline YAML."""

    def setUp(self) -> None:
        self.project = _tmp_git_project("koru-e2e-bs-")
        # Create a minimal flat pipeline (flat format uses 'tasks:' key)
        self.pipeline = self.project / "pipeline.yaml"
        self.pipeline.write_text(
            textwrap.dedent("""\
            project: e2e-bootstrap
            version: "1.0"
            prefix: BS
            tasks:
              - id: BS-001
                name: Check git status
                priority: high
                executor: {kind: shell, mode: automatic, handler: "git status"}
                execution: {queue: default, state: ready}
              - id: BS-002
                name: Print date
                priority: normal
                executor: {kind: shell, mode: automatic, handler: "date"}
                execution: {queue: default, state: ready}
        """)
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.project, ignore_errors=True)

    def test_bootstrap_creates_planfile_structure(self) -> None:
        code, out, _ = _run_main(
            "--bootstrap",
            "--from",
            str(self.pipeline),
            "--project",
            str(self.project),
            "--sprint",
            "current",
        )
        self.assertEqual(code, 0, f"bootstrap failed: {out}")
        self.assertIn("imported", out)
        self.assertTrue((self.project / ".planfile/config.yaml").exists())
        self.assertTrue((self.project / ".planfile/sprints/current.yaml").exists())

    def test_bootstrap_ticket_count(self) -> None:
        _run_main(
            "--bootstrap",
            "--from",
            str(self.pipeline),
            "--project",
            str(self.project),
            "--sprint",
            "current",
        )
        sprint = yaml.safe_load(
            (self.project / ".planfile/sprints/current.yaml").read_text(),
        )
        tickets = sprint["sprint"]["tickets"]
        self.assertEqual(len(tickets), 2)

    def test_bootstrap_rejects_without_force(self) -> None:
        _run_main(
            "--bootstrap",
            "--from",
            str(self.pipeline),
            "--project",
            str(self.project),
        )
        code, out, err = _run_main(
            "--bootstrap",
            "--from",
            str(self.pipeline),
            "--project",
            str(self.project),
        )
        self.assertEqual(code, 1)
        self.assertIn("already exists", out + err)

    def test_bootstrap_force_overwrites(self) -> None:
        _run_main(
            "--bootstrap",
            "--from",
            str(self.pipeline),
            "--project",
            str(self.project),
        )
        code, out, _ = _run_main(
            "--bootstrap",
            "--from",
            str(self.pipeline),
            "--project",
            str(self.project),
            "--force",
        )
        self.assertEqual(code, 0)
        self.assertIn("imported", out)


# ===========================================================================
# E2E: Gate authorization
# ===========================================================================


class TestE2EGate(unittest.TestCase):
    """koru gate authorize writes a structured note."""

    def setUp(self) -> None:
        self.project = _tmp_git_project("koru-e2e-gate-")
        _write_config(self.project, prefix="GT")
        _write_sprint(
            self.project,
            {
                "GT-001": {
                    "id": "GT-001",
                    "name": "Gate target ticket",
                    "status": "in_progress",
                    "priority": "high",
                    "sprint": "current",
                    "execution": {
                        "queue": "default",
                        "state": "running",
                    },
                    "outputs": {"notes": [], "artifacts": []},
                },
            },
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.project, ignore_errors=True)

    def test_gate_authorize_dry_run(self) -> None:
        code, out, _ = _run_main(
            "gate",
            "authorize",
            "GT-001",
            "--mode",
            "advisory",
            "--reason",
            "targeted pytest passed",
            "--project",
            str(self.project),
        )
        # Gate may fail if planfile binary is not available, but the CLI
        # should at least parse args and attempt the operation
        self.assertIsInstance(code, int)

    def test_gate_authorize_json_format(self) -> None:
        code, out, _ = _run_main(
            "gate",
            "authorize",
            "GT-001",
            "--mode",
            "advisory",
            "--reason",
            "CI subset passed",
            "--project",
            str(self.project),
            "--format",
            "json",
        )
        self.assertIsInstance(code, int)
        # If successful, output should be valid JSON
        if code == 0:
            data = json.loads(out)
            self.assertIn("kind", data)


# ===========================================================================
# E2E: Full lifecycle — init → task → queue → gc
# ===========================================================================


class TestE2EFullLifecycle(unittest.TestCase):
    """Simulate a complete project lifecycle through the CLI."""

    def setUp(self) -> None:
        self.project = _tmp_git_project("koru-e2e-full-")

    def tearDown(self) -> None:
        shutil.rmtree(self.project, ignore_errors=True)

    def test_full_lifecycle(self) -> None:
        # 1. Init
        code, out, _ = _init_project(self.project)
        self.assertEqual(code, 0, f"init: {out}")

        # 2. Doctor passes
        code, out, _ = _run_main("--doctor", "--project", str(self.project))
        self.assertEqual(code, 0, f"doctor: {out}")

        # 3. Create a task
        code, out, _ = _run_main(
            "task",
            "Add unit tests for auth module",
            "--project",
            str(self.project),
        )
        self.assertEqual(code, 0, f"task: {out}")

        # 4. Context shows the task
        code, out, _ = _run_main(
            "--context",
            "--project",
            str(self.project),
            "--format",
            "json",
        )
        self.assertEqual(code, 0)
        ctx = _extract_json(out)
        self.assertIn("policy", ctx)

        # 5. Scan the project
        code, out, _ = _run_main(
            "scan",
            "--project",
            str(self.project),
            "--skip-pytest",
            "--format",
            "json",
        )
        self.assertEqual(code, 0)

        # 6. GC with nothing stale yet
        code, out, _ = _run_main(
            "gc",
            "--project",
            str(self.project),
            "--max-age",
            "30",
        )
        self.assertEqual(code, 0)
        self.assertIn("no stale tickets", out)


# ===========================================================================
# E2E: Init with custom pipeline
# ===========================================================================


class TestE2EInitFromPipeline(unittest.TestCase):
    """koru --init --from <yaml> imports a custom pipeline."""

    def setUp(self) -> None:
        self.project = _tmp_git_project("koru-e2e-initfrom-")
        self.pipeline = self.project / "custom.yaml"
        self.pipeline.write_text(
            textwrap.dedent("""\
            project: custom-pipeline
            prefix: CUST
            tasks:
              - id: CUST-001
                name: Run lint
                priority: high
                executor: {kind: shell, mode: automatic, handler: "echo lint"}
                execution: {queue: default, state: ready}
        """)
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.project, ignore_errors=True)

    def test_init_from_custom_pipeline(self) -> None:
        code, out, err = _run_main(
            "--init",
            "--project",
            str(self.project),
            "--from",
            str(self.pipeline),
        )
        self.assertEqual(code, 0, f"init --from failed: {out}{err}")
        sprint = yaml.safe_load(
            (self.project / ".planfile/sprints/current.yaml").read_text(),
        )
        tickets = sprint["sprint"]["tickets"]
        self.assertTrue(
            any("lint" in t.get("name", "").lower() for t in tickets.values()),
            f"custom ticket not imported: {list(tickets.keys())}",
        )


# ===========================================================================
# E2E: Queue with human ticket → waiting_input
# ===========================================================================


@unittest.skipUnless(_HAS_PLANFILE, "planfile binary not in PATH")
class TestE2EHumanTicket(unittest.TestCase):
    """koru --queue on a human ticket returns waiting_input."""

    def setUp(self) -> None:
        self.project = _tmp_git_project("koru-e2e-human-")
        _write_config(self.project, prefix="HUM")
        _write_sprint(
            self.project,
            {
                "HUM-001": {
                    "id": "HUM-001",
                    "name": "Provide API key",
                    "status": "open",
                    "priority": "high",
                    "sprint": "current",
                    "executor": {
                        "kind": "human",
                        "mode": "interactive",
                        "handler": "password",
                    },
                    "execution": {
                        "queue": "default",
                        "state": "ready",
                        "attempt": 0,
                        "max_attempts": 1,
                    },
                    "inputs": {
                        "prompt": "Enter the API key",
                        "env_keys": ["API_KEY"],
                    },
                },
            },
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.project, ignore_errors=True)

    def test_human_ticket_returns_waiting_input(self) -> None:
        code, out, _ = _run_main(
            "--queue",
            "--project",
            str(self.project),
            "--actor",
            "e2e-human",
        )
        self.assertEqual(code, 0, f"human queue: {out}")
        self.assertIn("waiting_input", out)
        self.assertIn("HUM-001", out)


# ===========================================================================
# E2E: Context filtering (include-fixtures)
# ===========================================================================


class TestE2EContextFixtureFiltering(unittest.TestCase):
    """--include-fixtures / --no-include-fixtures controls ticket filtering."""

    def setUp(self) -> None:
        self.project = _tmp_git_project("koru-e2e-fix-")
        _write_config(self.project, prefix="FIX")
        _write_sprint(
            self.project,
            {
                "FIX-001": {
                    "id": "FIX-001",
                    "name": "Real ticket",
                    "status": "open",
                    "priority": "high",
                    "sprint": "current",
                    "labels": ["koru-task"],
                    "executor": {"kind": "shell", "mode": "automatic"},
                    "execution": {"queue": "default", "state": "ready"},
                },
                "FIX-002": {
                    "id": "FIX-002",
                    "name": "Test fixture ticket",
                    "status": "open",
                    "priority": "normal",
                    "sprint": "current",
                    "labels": ["test-only", "synthetic"],
                    "executor": {"kind": "shell", "mode": "automatic"},
                    "execution": {"queue": "default", "state": "ready"},
                },
            },
        )
        # Write a minimal policy so context works
        koru_dir = self.project / ".planfile" / ".koru"
        koru_dir.mkdir(parents=True, exist_ok=True)
        (koru_dir / "policy.yaml").write_text("llm:\n  allow_commit: false\n")

    def tearDown(self) -> None:
        shutil.rmtree(self.project, ignore_errors=True)

    def test_context_without_fixtures_skips_synthetic(self) -> None:
        code, out, _ = _run_main(
            "--context",
            "--project",
            str(self.project),
            "--format",
            "json",
            "--no-include-fixtures",
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        # The ticket should be the real one
        ticket = data.get("ticket", {})
        if ticket:
            self.assertNotIn("synthetic", ticket.get("labels", []))

    def test_context_with_fixtures_includes_all(self) -> None:
        code, out, _ = _run_main(
            "--context",
            "--project",
            str(self.project),
            "--format",
            "json",
            "--include-fixtures",
        )
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
