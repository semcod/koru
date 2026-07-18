"""Each phase of the patch transaction, exercised on its own.

The end-to-end paths are covered in ``test_planfile_queue``. These tests exist
so a phase can be changed — or replaced, as the verify fallback chain is meant
to be — with the contract it owes its neighbours pinned down here rather than
inferred from a full run.
"""

from __future__ import annotations

import contextlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from koru.queue.patch_mode import (
    NO_PATCH_EMITTED,
    PATCH_INTRODUCES_SYMLINK,
    PROMOTION_APPLY,
    PROMOTION_ARTIFACT,
    PROMOTION_COMMIT,
    PROMOTION_CONFLICT,
    PROMOTION_FAILED,
    PROMOTION_REFUSED_DIRTY_REPO,
    UNSAFE_DIRTY_WORKSPACE,
    VERIFY_FAILED_ROLLED_BACK,
)
from koru.queue.transaction import (
    ManifestFreeze,
    build_patch_plan,
    commit_if_requested,
    extract_patch,
    guard_promotion,
    resolve_verify_command,
    roll_back_failed_verify,
    screen_diff_contents,
    screen_direct_apply,
    screen_promotion_preconditions,
    skip_verify_baseline,
    verify_output,
)

_DIFF = (
    "diff --git a/a.txt b/a.txt\n"
    "--- a/a.txt\n"
    "+++ b/a.txt\n"
    "@@ -1 +1 @@\n"
    "-old\n"
    "+new\n"
)


def _reply(stdout: str = "", stderr: str = "", returncode: int = 0):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


class _RepoCase(unittest.TestCase):
    """A throwaway git repo with one committed file."""

    def _git_repo(self, tmp: str) -> Path:
        project = Path(tmp)
        for args in (
            ["init", "-q"],
            ["config", "user.email", "koru@test"],
            ["config", "user.name", "koru"],
        ):
            subprocess.run(["git", *args], cwd=project, check=True, capture_output=True)
        return project

    def _commit_file(self, project: Path, rel: str, body: str) -> None:
        target = project / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=project, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-qm", "baseline"], cwd=project, check=True, capture_output=True,
        )

    def _plan(self, project: Path, ticket: dict | None = None):
        return build_patch_plan(project, ticket if ticket is not None else {"id": "T-1"}, _DIFF)


class TestExtractPatch(unittest.TestCase):
    def test_returns_the_diff_and_no_refusal(self) -> None:
        diff, refusal = extract_patch(_reply(stdout=_DIFF))

        self.assertIsNone(refusal)
        self.assertIsNotNone(diff)
        self.assertIn("+new", diff or "")

    def test_a_reply_without_a_diff_is_retryable_and_quotes_what_came_instead(self) -> None:
        """The agent gets re-asked, so its first line must survive into the refusal."""
        diff, refusal = extract_patch(_reply(stdout="I cannot do that, Dave.\nmore prose"))

        self.assertIsNone(diff)
        self.assertIsNotNone(refusal)
        assert refusal is not None
        self.assertEqual(refusal.code, NO_PATCH_EMITTED)
        self.assertTrue(refusal.retryable)
        self.assertIn("I cannot do that, Dave.", refusal.message)

    def test_an_empty_reply_is_named_rather_than_quoted_blank(self) -> None:
        _diff, refusal = extract_patch(_reply(stdout="   \n"))

        assert refusal is not None
        self.assertIn("(empty reply)", refusal.message)


class TestScreenDiffContents(unittest.TestCase):
    _SYMLINK_DIFF = (
        "diff --git a/link b/link\n"
        "new file mode 120000\n"
        "--- /dev/null\n"
        "+++ b/link\n"
        "@@ -0,0 +1 @@\n"
        "+/etc/passwd\n"
        "\\ No newline at end of file\n"
    )

    def test_an_ordinary_diff_passes(self) -> None:
        self.assertIsNone(screen_diff_contents(_DIFF))

    def test_a_symlink_is_refused_because_it_can_point_outside_the_workspace(self) -> None:
        refusal = screen_diff_contents(self._SYMLINK_DIFF)

        assert refusal is not None
        self.assertEqual(refusal.code, PATCH_INTRODUCES_SYMLINK)

    def test_symlinks_can_be_opted_into(self) -> None:
        with mock.patch.dict("os.environ", {"KORU_QUEUE_ALLOW_SYMLINKS": "1"}):
            self.assertIsNone(screen_diff_contents(self._SYMLINK_DIFF))


class TestResolveVerifyCommand(_RepoCase):
    def test_the_ticket_input_wins_over_everything_else(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            (project / "koru.yaml").write_text(
                "when:\n  before_complete_ticket:\n    commands:\n      - pytest -q\n",
                encoding="utf-8",
            )
            ticket = {
                "inputs": {"verify_command": "node --check a.js"},
                "acceptance_criteria": ["npm test"],
            }

            with mock.patch.dict(
                "os.environ", {"KORU_QUEUE_VERIFY_COMMAND": "bash gate.sh"},
            ):
                self.assertEqual(resolve_verify_command(project, ticket), "node --check a.js")

    def test_an_acceptance_criterion_that_is_a_command_is_used_next(self) -> None:
        """Planfile drops unknown ``inputs`` keys, so criteria are a real fallback."""
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            ticket = {"acceptance_criteria": ["the tests pass", "pytest -q tests/"]}

            self.assertEqual(resolve_verify_command(project, ticket), "pytest -q tests/")

    def test_prose_criteria_are_not_mistaken_for_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            ticket = {"acceptance_criteria": ["the module no longer imports yaml"]}

            self.assertEqual(resolve_verify_command(project, ticket), "")

    def test_the_project_gate_is_the_last_resort(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            (project / "koru.yaml").write_text(
                "when:\n  before_complete_ticket:\n    commands:\n      - pytest -q\n",
                encoding="utf-8",
            )

            self.assertEqual(resolve_verify_command(project, {}), "pytest -q")

    def test_a_project_without_a_declared_gate_resolves_to_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)

            self.assertEqual(resolve_verify_command(project, {}), "")

    def test_a_missing_pyyaml_resolves_to_nothing_instead_of_crashing(self) -> None:
        """The gate is unknowable without yaml, but that must not take the run down.

        Naming ``yaml.YAMLError`` in the handler that also caught ``ImportError``
        used to raise ``UnboundLocalError`` out of the whole transaction.
        """
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            (project / "koru.yaml").write_text(
                "when:\n  before_complete_ticket:\n    commands:\n      - pytest -q\n",
                encoding="utf-8",
            )

            with mock.patch.dict("sys.modules", {"yaml": None}):
                self.assertEqual(resolve_verify_command(project, {}), "")


class TestSkipVerifyBaseline(unittest.TestCase):
    def test_a_repair_ticket_skips_the_baseline_it_is_meant_to_be_failing(self) -> None:
        self.assertTrue(skip_verify_baseline({"labels": ["type:development-defect"]}))

    def test_an_ordinary_ticket_does_not(self) -> None:
        self.assertFalse(skip_verify_baseline({"labels": ["type:chore"]}))
        self.assertFalse(skip_verify_baseline(None))

    def test_it_can_be_declared_on_the_inputs(self) -> None:
        self.assertTrue(skip_verify_baseline({"inputs": {"expect_broken_baseline": True}}))


class TestVerifyOutput(unittest.TestCase):
    def test_stderr_is_preferred_over_stdout(self) -> None:
        self.assertEqual(verify_output(_reply(stdout="noise", stderr="the failure")), "the failure")

    def test_it_falls_back_to_stdout_and_keeps_the_tail(self) -> None:
        self.assertEqual(verify_output(_reply(stdout="abcdef"), limit=3), "def")


class TestBuildPatchPlan(_RepoCase):
    def test_isolation_requires_both_a_gate_and_worktrees(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")  # a worktree is cut from HEAD

            with mock.patch.dict("os.environ", {"KORU_QUEUE_WORKTREE": "1"}):
                gated = self._plan(project, {"inputs": {"verify_command": "true"}})
                ungated = self._plan(project, {})

            self.assertTrue(gated.isolated)
            self.assertFalse(ungated.isolated, "nothing to verify means nothing to isolate")

    def test_it_adopts_the_run_id_of_a_manifest_pinned_by_an_earlier_attempt(self) -> None:
        """A retry must stay the same run, or its evidence would split in two."""
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)

            plan = build_patch_plan(project, {}, _DIFF, {"run_id": "deadbeef"})

            self.assertEqual(plan.run_id, "deadbeef")

    def test_the_targets_come_from_the_diff_itself(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")

            self.assertEqual(self._plan(project).targets, ("a.txt",))


class TestScreenPreconditions(_RepoCase):
    def test_commit_mode_refuses_a_dirty_repository(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            (project / "unrelated.txt").write_text("someone else's work\n", encoding="utf-8")
            plan = self._plan(project, {"inputs": {"promotion_mode": PROMOTION_COMMIT}})

            refusal = screen_promotion_preconditions(plan)

            assert refusal is not None
            self.assertEqual(refusal.code, PROMOTION_REFUSED_DIRTY_REPO)

    def test_apply_mode_does_not_care_about_unrelated_dirt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            (project / "unrelated.txt").write_text("someone else's work\n", encoding="utf-8")

            self.assertIsNone(screen_promotion_preconditions(self._plan(project)))

    def test_direct_apply_refuses_when_a_target_carries_uncommitted_work(self) -> None:
        """`git checkout --` would restore from the index and discard those edits."""
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            (project / "a.txt").write_text("someone was editing this\n", encoding="utf-8")

            refusal = screen_direct_apply(self._plan(project))

            assert refusal is not None
            self.assertEqual(refusal.code, UNSAFE_DIRTY_WORKSPACE)
            self.assertIn("a.txt", refusal.message)

    def test_direct_apply_passes_on_a_clean_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")

            self.assertIsNone(screen_direct_apply(self._plan(project)))


class TestManifestFreeze(_RepoCase):
    def test_it_pins_once_so_a_later_freeze_cannot_adopt_a_patched_workspace(self) -> None:
        """Re-pinning would destroy exactly the drift detection this exists for."""
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            freeze = ManifestFreeze(self._plan(project))

            first = freeze.freeze()
            (project / "a.txt").write_text("patched\n", encoding="utf-8")
            second = freeze.freeze()

            self.assertEqual(first["manifest_hash"], second["manifest_hash"])

    def test_it_persists_on_every_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            plan = self._plan(project)

            ManifestFreeze(plan).freeze()

            self.assertTrue(list((project / ".koru" / "runs").glob("*/manifest.json")))

    def test_a_manifest_handed_in_is_adopted_rather_than_rebuilt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            pinned = ManifestFreeze(self._plan(project)).freeze()

            adopted = ManifestFreeze(self._plan(project), pinned).freeze()

            self.assertEqual(adopted["manifest_hash"], pinned["manifest_hash"])


class TestGuardPromotion(_RepoCase):
    def test_an_unmoved_workspace_may_promote(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            manifest = ManifestFreeze(self._plan(project)).freeze()

            self.assertIsNone(guard_promotion(self._plan(project), manifest))

    def test_a_workspace_edited_during_verification_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            plan = self._plan(project)
            manifest = ManifestFreeze(plan).freeze()

            (project / "a.txt").write_text("another session got here first\n", encoding="utf-8")
            refusal = guard_promotion(plan, manifest)

            assert refusal is not None
            self.assertEqual(refusal.code, PROMOTION_CONFLICT)


class TestPromotionDecisions(_RepoCase):
    def test_apply_mode_commits_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            plan = self._plan(project, {"inputs": {"promotion_mode": PROMOTION_APPLY}})

            self.assertIsNone(commit_if_requested(plan, ("a.txt",)))
            self.assertEqual(_head_subject(project), "baseline")

    def test_commit_mode_commits_the_changed_files_on_the_current_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            (project / "a.txt").write_text("new\n", encoding="utf-8")
            plan = self._plan(
                project, {"id": "T-7", "inputs": {"promotion_mode": PROMOTION_COMMIT}},
            )

            self.assertIsNone(commit_if_requested(plan, ("a.txt",)))
            self.assertIn("koru(T-7)", _head_subject(project))

    def test_artifact_mode_is_not_a_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            plan = self._plan(project, {"inputs": {"promotion_mode": PROMOTION_ARTIFACT}})

            self.assertIsNone(commit_if_requested(plan, ("a.txt",)))
            self.assertEqual(_head_subject(project), "baseline")


class TestRollback(_RepoCase):
    def test_it_restores_the_file_and_reports_the_gate_that_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            (project / "a.txt").write_text("new\n", encoding="utf-8")
            plan = self._plan(project, {"inputs": {"verify_command": "pytest -q"}})

            outcome = roll_back_failed_verify(
                plan, ("a.txt",), _reply(returncode=2, stderr="1 failed"),
            )

            self.assertEqual(outcome.code, VERIFY_FAILED_ROLLED_BACK)
            self.assertTrue(outcome.workspace_left_untouched)
            self.assertIn("pytest -q", outcome.message)
            self.assertIn("1 failed", outcome.message)
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "old\n")


class TestWorktreeUnavailable(_RepoCase):
    """A checkout that cannot host a worktree must not silently lose the guards.

    ``staging_worktree`` yields ``None`` on a read-only checkout — koru's own
    noVNC image mounts the repo that way. That used to be indistinguishable from
    "verified, promote", so the patch either vanished or landed ungated.
    """

    _REPLY = (
        "```diff\n"
        "diff --git a/a.txt b/a.txt\n"
        "--- a/a.txt\n"
        "+++ b/a.txt\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
        "```\n"
    )

    @contextlib.contextmanager
    def _no_worktree(self):
        @contextlib.contextmanager
        def _unavailable(project: Path, targets: tuple[str, ...]):
            yield None

        with mock.patch(
            "koru.queue.transaction.staging.staging_worktree", _unavailable,
        ):
            yield

    def _apply(self, project: Path, ticket: dict, gate):
        from koru.queue.patch_transaction import apply_proposed_patch

        with self._no_worktree():
            return apply_proposed_patch(
                project, _reply(stdout=self._REPLY), ticket, gate,
            )[1]

    def test_branch_mode_refuses_rather_than_reporting_a_patch_it_never_made(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            ticket = {"inputs": {"verify_command": "true", "promotion_mode": "branch"}}

            outcome = self._apply(project, ticket, lambda cmd, cwd: _reply())

            assert outcome is not None
            self.assertEqual(outcome.code, PROMOTION_FAILED)
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "old\n")
            branches = subprocess.run(
                ["git", "branch", "--list", "koru/run-*"],
                cwd=project, capture_output=True, text=True, check=True,
            ).stdout
            self.assertEqual(branches.strip(), "", "no ref may claim an unmade patch")

    def test_apply_mode_still_refuses_to_clobber_uncommitted_work(self) -> None:
        """The dirty guard lives on the direct path, so the fallback must go there."""
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            (project / "a.txt").write_text("someone was editing this\n", encoding="utf-8")
            ticket = {"inputs": {"verify_command": "true"}}

            outcome = self._apply(project, ticket, lambda cmd, cwd: _reply())

            assert outcome is not None
            self.assertEqual(outcome.code, UNSAFE_DIRTY_WORKSPACE)
            self.assertEqual(
                (project / "a.txt").read_text(encoding="utf-8"),
                "someone was editing this\n",
            )

    def test_apply_mode_still_runs_the_gate_and_rolls_back_when_it_fails(self) -> None:
        """Losing isolation must not mean losing verification."""
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            ran: list[Path] = []

            def failing_gate(command: str, cwd: Path):
                ran.append(cwd)
                return _reply(returncode=1, stderr="boom")

            outcome = self._apply(
                project, {"inputs": {"verify_command": "pytest -q"}}, failing_gate,
            )

            assert outcome is not None
            self.assertEqual(outcome.code, VERIFY_FAILED_ROLLED_BACK)
            self.assertEqual(ran, [project], "the gate must run, in the workspace itself")
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "old\n")


def _head_subject(project: Path) -> str:
    return subprocess.run(
        ["git", "log", "-1", "--pretty=%s"],
        cwd=project, capture_output=True, text=True, check=True,
    ).stdout.strip()


if __name__ == "__main__":
    unittest.main()
