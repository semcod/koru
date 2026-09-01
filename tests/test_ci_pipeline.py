"""Tests for koru ci pipeline."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from koru.ci.gates import DEFAULT_GATES, gate_commands, resolve_gates, run_quality_gates
from koru.ci.publication import (
    PublicationConfig,
    dispatch_validator_merge,
    load_publication_config,
)
from koru.ci.runner import run_local_ci
from koru.cli_ci import ci_main
from koru.policy import Policy


class TestCiRunner(unittest.TestCase):
    def test_run_local_ci_uses_policy_command(self) -> None:
        policy = Policy(ci_command="echo ok")
        with (
            patch("koru.ci.runner.load_policy", return_value=policy),
            patch("koru.ci.runner.run_policy_ci_command", return_value=(0, "ok")),
            patch("koru.ci.runner.run_quality_gates", return_value={"overall_status": "passed", "results": []}),
        ):
            result = run_local_ci(Path("/tmp/project"))
        self.assertEqual(result["overall_status"], "passed")
        stages = [stage["stage"] for stage in result["stages"]]
        self.assertEqual(stages, ["policy_ci", "quality_gates"])

    def test_run_local_ci_fails_on_policy_command(self) -> None:
        policy = Policy(ci_command="false")
        with (
            patch("koru.ci.runner.load_policy", return_value=policy),
            patch("koru.ci.runner.run_policy_ci_command", return_value=(1, "fail")),
        ):
            result = run_local_ci(Path("/tmp/project"), include_gates=False)
        self.assertEqual(result["overall_status"], "failed")

    def test_skip_gates_without_policy_command_is_a_noop(self) -> None:
        policy = Policy(ci_command="")
        with (
            patch("koru.ci.runner.load_policy", return_value=policy),
            patch("koru.ci.runner.run_quality_gates") as quality_gates,
        ):
            result = run_local_ci(Path("/tmp/project"), include_gates=False)
        self.assertEqual(result, {"overall_status": "passed", "stages": []})
        quality_gates.assert_not_called()


class TestPublication(unittest.TestCase):
    def test_load_publication_config_defaults(self) -> None:
        project = Path("/tmp/koru-ci-test-project")
        project.mkdir(parents=True, exist_ok=True)
        cfg = load_publication_config(project)
        self.assertIsInstance(cfg, PublicationConfig)
        self.assertEqual(cfg.validator_repo, "subactor/validator-agent")

    def test_dispatch_validator_dry_run(self) -> None:
        project = Path("/tmp/koru-ci-publish-test")
        cfg = PublicationConfig(
            validator_checkout=Path("/tmp/validator-agent"),
            validator_repo="subactor/validator-agent",
            validator_ref="main",
            merge=False,
            wait_checks=True,
            watch=False,
            update_branch=False,
        )
        with (
            patch("koru.ci.publication.gh_available", return_value=True),
            patch("koru.ci.publication.resolve_github_repo") as repo_mock,
            patch("koru.ci.publication.resolve_pr_head_sha", return_value="abc123"),
            patch(
                "koru.ci.publication._resolve_validator_script",
                return_value=Path("/tmp/validator-agent/bin/dispatch-direct-pr.sh"),
            ),
        ):
            repo_mock.return_value = type("Repo", (), {"owner": "semcod", "name": "koru", "slug": "semcod/koru"})()
            result = dispatch_validator_merge(
                project,
                ticket_id="ticket-021",
                pr_number=99,
                config=cfg,
                dry_run=True,
            )
        self.assertEqual(result["status"], "dry_run")
        self.assertEqual(result["frozen_head"], "abc123")
        self.assertIn("--ticket", result["command"])
        self.assertIn("ticket-021", result["command"])


class TestCiGates(unittest.TestCase):
    def test_resolve_gates_defaults_without_topology(self) -> None:
        project = Path("/tmp/koru-gates-default")
        project.mkdir(parents=True, exist_ok=True)
        commands = gate_commands(project)
        with patch("koru.ci.gates._detect_enabled_gates", return_value=[]):
            selected = resolve_gates(project, None, commands)
        self.assertEqual(selected, list(DEFAULT_GATES))

    def test_skips_testql_when_no_scenarios(self) -> None:
        project = Path("/tmp/koru-testql-skip")
        project.mkdir(parents=True, exist_ok=True)
        with patch("koru.ci.gates.has_testql_scenarios", return_value=False):
            result = run_quality_gates(project, gates=["testql"])
        self.assertEqual(result["overall_status"], "passed")
        self.assertEqual(result["results"][0]["status"], "skipped")


class TestCiCli(unittest.TestCase):
    def test_ci_gates_help(self) -> None:
        with patch("koru.cli_ci.run_quality_gates", return_value={"overall_status": "passed", "results": []}):
            code = ci_main(["--project", "/tmp", "gates", "--format", "json"])
        self.assertEqual(code, 0)

    def test_ci_publish_requires_ticket(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            ci_main(["--project", "/tmp", "publish"])
        self.assertEqual(ctx.exception.code, 2)

    def test_ci_publish_preserves_command_line_overrides(self) -> None:
        config = PublicationConfig(
            validator_checkout=Path("/tmp/validator-agent"),
            validator_repo="subactor/validator-agent",
            validator_ref="main",
            merge=False,
            wait_checks=True,
            watch=False,
            update_branch=False,
        )
        with (
            patch("koru.cli_ci.load_publication_config", return_value=config),
            patch(
                "koru.cli_ci.dispatch_validator_merge",
                return_value={
                    "status": "dry_run",
                    "repo": "semcod/koru",
                    "pr": 99,
                    "frozen_head": "abc123",
                },
            ) as dispatch,
            patch("koru.cli_ci.emit_management_event"),
        ):
            code = ci_main(
                [
                    "--project",
                    "/tmp/project",
                    "publish",
                    "--ticket",
                    "ticket-021",
                    "--pr",
                    "99",
                    "--merge",
                    "--watch",
                    "--update-branch",
                    "--no-wait-checks",
                    "--dry-run",
                    "--format",
                    "json",
                ],
            )

        self.assertEqual(code, 0)
        self.assertEqual(dispatch.call_args.args, (Path("/tmp/project"),))
        self.assertEqual(dispatch.call_args.kwargs["ticket_id"], "ticket-021")
        self.assertEqual(dispatch.call_args.kwargs["pr_number"], 99)
        self.assertTrue(dispatch.call_args.kwargs["dry_run"])
        self.assertEqual(
            dispatch.call_args.kwargs["config"],
            PublicationConfig(
                validator_checkout=Path("/tmp/validator-agent"),
                validator_repo="subactor/validator-agent",
                validator_ref="main",
                merge=True,
                wait_checks=False,
                watch=True,
                update_branch=True,
            ),
        )


if __name__ == "__main__":
    unittest.main()
