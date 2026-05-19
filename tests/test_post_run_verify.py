"""Tests for post-run verification after queue completion."""

from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from koru.autonomy.post_run_verify import (
    PostRunVerifyConfig,
    fetch_recently_done_ticket_ids,
    load_post_run_verify_config,
    run_verify_commands,
    verify_after_ide_work,
    verify_completed_tickets,
)


@dataclass
class _State:
    pending_ide_verify_id: str | None = None
    post_verify_seen: set[str] = field(default_factory=set)


def _ok(stdout: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=0, stdout=stdout, stderr="")


def _fail(stderr: str = "boom") -> SimpleNamespace:
    return SimpleNamespace(returncode=1, stdout="", stderr=stderr)


class TestPostRunVerify(unittest.TestCase):
    def test_load_from_koru_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "koru.yaml").write_text(
                """
schema: "1.0"
queue:
  post_run_verify:
    enabled: true
    on_failure: block
    commands:
      - echo verify
""",
                encoding="utf-8",
            )
            cfg = load_post_run_verify_config(project)
            assert cfg is not None
            self.assertTrue(cfg.enabled)
            self.assertEqual(cfg.on_failure, "block")
            self.assertEqual(cfg.commands, ("echo verify",))

    def test_verify_reopens_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            calls: list[list[str]] = []

            def shell_runner(_cmd: str, _proj: Path) -> SimpleNamespace:
                return _fail("pytest failed")

            def planfile_runner(cmd, _proj: Path) -> SimpleNamespace:
                calls.append(list(cmd))
                return _ok()

            outcomes = verify_completed_tickets(
                project,
                ["PLF-1"],
                config=PostRunVerifyConfig(
                    enabled=True,
                    commands=("pytest -q",),
                    on_failure="reopen",
                ),
                planfile_runner=planfile_runner,
                shell_runner=shell_runner,
            )
            self.assertEqual(len(outcomes), 1)
            self.assertFalse(outcomes[0]["ok"])
            self.assertEqual(outcomes[0]["action"], "reopened")
            self.assertTrue(
                any(
                    c[:4] == ["planfile", "ticket", "update", "PLF-1"] and "--status" in c
                    for c in calls
                ),
            )

    def test_verify_after_ide_work_pending_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            state = _State(pending_ide_verify_id="PLF-9")

            def shell_runner(_cmd: str, _proj: Path) -> SimpleNamespace:
                return _ok()

            def planfile_runner(cmd, _proj: Path) -> SimpleNamespace:
                if cmd[:4] == ["planfile", "ticket", "show", "PLF-9"]:
                    return _ok('{"id": "PLF-9", "status": "done"}')
                return _ok()

            outcomes = verify_after_ide_work(
                project,
                state,
                config=PostRunVerifyConfig(enabled=True, commands=("true",)),
                planfile_runner=planfile_runner,
                shell_runner=shell_runner,
            )
            self.assertEqual(len(outcomes), 1)
            self.assertTrue(outcomes[0]["ok"])
            self.assertIsNone(state.pending_ide_verify_id)
            self.assertIn("PLF-9", state.post_verify_seen)

    def test_fetch_recently_done_ticket_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            recent = datetime.now(UTC).isoformat()

            def runner(cmd, _proj: Path) -> SimpleNamespace:
                self.assertEqual(cmd[:5], ["planfile", "ticket", "list", "--status", "done"])
                return _ok(
                    json.dumps(
                        [
                            {"id": "PLF-1", "updated_at": recent},
                            {"id": "PLF-2", "updated_at": "2020-01-01T00:00:00+00:00"},
                        ],
                    ),
                )

            ids = fetch_recently_done_ticket_ids(
                project,
                within_minutes=60,
                runner=runner,
            )
            self.assertEqual(ids, ["PLF-1"])

    def test_run_verify_commands_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)

            def shell_runner(cmd: str, _proj: Path) -> SimpleNamespace:
                self.assertEqual(cmd, "true")
                return _ok()

            ok, detail, code = run_verify_commands(project, ["true"], shell_runner=shell_runner)
            self.assertTrue(ok)
            self.assertEqual(detail, "")
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
