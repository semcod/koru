from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from koru.cli import _command_value
from koru.loop import _search_root_for_include, discover_repositories, run_closed_loop


class TestKoruLoop(unittest.TestCase):
    def test_search_root_for_include_uses_literal_prefix(self) -> None:
        workspace = Path("/workspace")

        self.assertEqual(_search_root_for_include(workspace, "semcod/p*"), workspace / "semcod")
        self.assertEqual(
            _search_root_for_include(workspace, "semcod/tools/p*"),
            workspace / "semcod" / "tools",
        )
        self.assertEqual(_search_root_for_include(workspace, "*"), workspace)
        self.assertEqual(_search_root_for_include(workspace, "*/planfile"), workspace)

    def test_discover_repositories_with_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            repo_a = workspace / "semcod" / "alpha"
            repo_b = workspace / "other" / "beta"
            (repo_a / ".git").mkdir(parents=True)
            (repo_b / ".git").mkdir(parents=True)

            repos = discover_repositories(workspace, include_pattern="semcod/*")

            self.assertEqual(repos, [repo_a.resolve()])

    def test_glob_does_not_cross_into_vendor_or_linked_worktrees(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            for name in ("autogrammar/alpha", "autogrammar/alpha/vendor/nested",
                         "autogrammar/.worktrees/pilot", "autogrammar/vendor/third"):
                (root / name / ".git").mkdir(parents=True)
            self.assertEqual(discover_repositories(root, "autogrammar/*"),
                             [root / "autogrammar/alpha"])
            self.assertEqual(discover_repositories(root, "autogrammar/**"),
                             [root / "autogrammar/alpha"])

    def test_exact_linked_worktree_and_missing_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            target = root / ".worktrees/pilot"
            target.mkdir(parents=True)
            (target / ".git").write_text("gitdir: /unused/test-metadata\n")
            self.assertEqual(discover_repositories(root, ".worktrees/pilot"), [target])
            self.assertEqual(discover_repositories(root, "missing/*"), [])

    def test_discovery_refuses_escape_and_skips_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            outside = root / "outside"
            (outside / ".git").mkdir(parents=True)
            workspace = root / "workspace"
            workspace.mkdir()
            (workspace / "alias").symlink_to(outside, target_is_directory=True)
            self.assertEqual(discover_repositories(workspace, "*"), [])
            self.assertEqual(discover_repositories(workspace, "alias"), [])
            for pattern in ("../outside", str(outside)):
                with self.assertRaises(ValueError):
                    discover_repositories(workspace, pattern)

    def test_discovery_fails_closed_on_budget_exhaustion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            for i in range(4):
                (root / str(i) / ".git").mkdir(parents=True)
            with patch("koru.loop._DISCOVERY_LIMIT", 3), self.assertRaises(ValueError):
                discover_repositories(root, "*")

    def test_discovery_never_scans_inside_selected_repository(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            repo = root / "org/repo"
            (repo / ".git").mkdir(parents=True)
            with patch("koru.loop.os.scandir", wraps=__import__("os").scandir) as scan:
                self.assertEqual(discover_repositories(root, "org/*"), [repo])
            self.assertNotIn(repo, [call.args[0] for call in scan.call_args_list])

    def test_run_closed_loop_retries_failed_repositories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            repo_a = (workspace / "semcod" / "alpha").resolve()
            repo_b = (workspace / "semcod" / "beta").resolve()
            repo_a.mkdir(parents=True)
            repo_b.mkdir(parents=True)

            attempts: dict[Path, int] = {repo_a: 0, repo_b: 0}

            def runner(_command: list[str], repository: Path) -> SimpleNamespace:
                attempts[repository] += 1
                if repository == repo_b and attempts[repository] == 1:
                    return SimpleNamespace(returncode=1, stdout="", stderr="failed")
                return SimpleNamespace(returncode=0, stdout="ok", stderr="")

            report = run_closed_loop(
                command=["python", "-V"],
                repositories=[repo_a, repo_b],
                max_rounds=3,
                runner=runner,
            )

            self.assertEqual(attempts[repo_a], 1)
            self.assertEqual(attempts[repo_b], 2)
            self.assertEqual(report.failed, ())
            self.assertEqual(report.succeeded, (repo_a, repo_b))
            self.assertEqual(report.rounds_executed, 2)

    def test_run_closed_loop_single_round_when_all_succeed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            repo_a = (workspace / "semcod" / "alpha").resolve()
            repo_b = (workspace / "semcod" / "beta").resolve()
            repo_a.mkdir(parents=True)
            repo_b.mkdir(parents=True)

            def runner(_command: list[str], _repository: Path) -> SimpleNamespace:
                return SimpleNamespace(returncode=0, stdout="ok", stderr="")

            report = run_closed_loop(
                command=["python", "-V"],
                repositories=[repo_a, repo_b],
                max_rounds=3,
                runner=runner,
            )

            self.assertEqual(report.failed, ())
            self.assertEqual(report.succeeded, (repo_a, repo_b))
            self.assertEqual(report.rounds_executed, 1)

    def test_nonpositive_rounds_cannot_report_an_unexecuted_run_as_success(self) -> None:
        for rounds in (0, -1):
            with self.assertRaises(ValueError):
                run_closed_loop(command=["unused"], repositories=[Path(".")], max_rounds=rounds)

    def test_command_value_rejects_blank_value(self) -> None:
        with self.assertRaises(argparse.ArgumentTypeError):
            _command_value("   ")


if __name__ == "__main__":
    unittest.main()
