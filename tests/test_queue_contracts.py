"""Capability contracts: the box an actor works in, and its enforcement.

The core property: nothing the model or the ticket authors can widen the box.
A ticket names a contract; the definition lives in koru.yaml; a typo'd name is
an unsatisfiable contract, not freedom.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from koru.queue.contracts import (
    CAP_PROPOSE,
    CAP_STAGE,
    CapabilityContract,
    contract_for_ticket,
)
from koru.queue.patch_mode import POLICY_DENIED
from tests import _repolab

_CONTRACT = CapabilityContract(
    id="local-refactor-r1",
    actor="bot:koru-refactor",
    allow_paths=("src/**", "tests/**"),
    deny_paths=(".env", ".git/**", "secrets/**"),
    allow_capabilities=(CAP_PROPOSE, CAP_STAGE),
    max_risk="R1",
    max_files=4,
    max_patch_bytes=50_000,
    max_attempts=2,
)

_GOOD_REPLY = (
    "```diff\n"
    "diff --git a/src/a.txt b/src/a.txt\n"
    "--- a/src/a.txt\n"
    "+++ b/src/a.txt\n"
    "@@ -1 +1 @@\n"
    "-old\n"
    "+new\n"
    "```\n"
)


def _reply(stdout: str = "", stderr: str = "", returncode: int = 0):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


class TestContractEvaluation(unittest.TestCase):
    def _ok(self, **overrides):
        fields = {
            "actor": "bot:koru-refactor",
            "capability": CAP_STAGE,
            "targets": ("src/a.py",),
            "diff": "small",
            "risk_class": "R1",
        }
        fields.update(overrides)
        return _CONTRACT.evaluate(**fields)

    def test_the_happy_path_is_allowed(self) -> None:
        self.assertTrue(self._ok().allowed)

    def test_each_violation_refuses(self) -> None:
        cases = {
            "wrong actor": {"actor": "bot:impostor"},
            "capability outside the box": {"capability": "code.patch.promote_main"},
            "risk above ceiling": {"risk_class": "R2"},
            "denied path": {"targets": ("src/a.py", ".env")},
            "path outside allowlist": {"targets": ("deploy/run.sh",)},
            "too many files": {"targets": tuple(f"src/f{i}.py" for i in range(5))},
            "patch too large": {"diff": "x" * 50_001},
        }
        for name, overrides in cases.items():
            with self.subTest(case=name):
                self.assertFalse(self._ok(**overrides).allowed, name)

    def test_deny_wins_over_allow(self) -> None:
        """`.git/**` inside an allowed tree is still denied — deny is absolute."""
        contract = CapabilityContract(
            id="c", actor="a", allow_paths=("**",), deny_paths=(".git/**",),
            allow_capabilities=(CAP_STAGE,),
        )

        decision = contract.evaluate(
            actor="a", capability=CAP_STAGE, targets=(".git/hooks/pre-commit",),
        )

        self.assertFalse(decision.allowed)

    def test_glob_star_does_not_cross_directories(self) -> None:
        contract = CapabilityContract(
            id="c", actor="a", allow_paths=("src/*.py",), allow_capabilities=(CAP_STAGE,),
        )

        flat = contract.evaluate(actor="a", capability=CAP_STAGE, targets=("src/a.py",))
        nested = contract.evaluate(
            actor="a", capability=CAP_STAGE, targets=("src/deep/a.py",),
        )

        self.assertTrue(flat.allowed)
        self.assertFalse(nested.allowed, "* must not cross /")

    def test_a_ticket_naming_an_undefined_contract_gets_an_unsatisfiable_one(self) -> None:
        """A typo must not widen anyone's box."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)

            contract = contract_for_ticket(
                project, {"inputs": {"contract": "no-such-contract"}},
            )

            assert contract is not None
            self.assertFalse(
                contract.evaluate(actor="anyone", capability=CAP_STAGE).allowed,
            )

    def test_a_ticket_without_a_contract_is_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(contract_for_ticket(Path(tmp), {"inputs": {}}))


class _RepoCase(unittest.TestCase):
    def _git_repo(self, tmp: str) -> Path:
        return _repolab.git_repo(tmp)

    def _commit_file(self, project: Path, rel: str, body: str) -> None:
        _repolab.commit_file(project, rel, body)

    def _write_contract(self, project: Path, *, allow_paths='["src/**"]') -> None:
        (project / "koru.yaml").write_text(
            "queue:\n"
            "  contracts:\n"
            "    local-r1:\n"
            '      actor: "koru-test"\n'
            f"      allow_paths: {allow_paths}\n"
            '      deny_paths: [".env"]\n'
            "      allow_capabilities:\n"
            "        - code.patch.propose\n"
            "        - code.patch.stage\n"
            "        - code.patch.promote_branch\n"
            "      max_files: 4\n",
            encoding="utf-8",
        )

    def _run(self, project: Path, ticket: dict):
        from koru.queue.patch_retry import apply_patch_with_retry

        return apply_patch_with_retry(
            project,
            _reply(stdout=_GOOD_REPLY),
            ticket,
            {"prompt": "x"},
            lambda action, p: _reply(returncode=1),
            lambda command, cwd: _reply(),
            actor="koru-test",
        )


class TestContractEnforcementInTransaction(_RepoCase):
    def test_a_patch_outside_the_contract_is_policy_denied_before_any_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "src/a.txt", "old\n")
            self._write_contract(project, allow_paths='["docs/**"]')  # src is outside
            ticket = {
                "id": "C-1",
                "inputs": {"verify_command": "true", "contract": "local-r1"},
            }

            _r, outcome, bundle = self._run(project, ticket)

            assert outcome is not None
            self.assertEqual(outcome.code, POLICY_DENIED)
            self.assertIn("outside allowed paths", outcome.message)
            self.assertEqual(
                (project / "src/a.txt").read_text(encoding="utf-8"), "old\n",
            )
            assert bundle is not None
            self.assertEqual(bundle["verdict"], "refused")

    def test_a_patch_inside_the_contract_lands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "src/a.txt", "old\n")
            self._write_contract(project)
            ticket = {
                "id": "C-2",
                "inputs": {"verify_command": "true", "contract": "local-r1",
                           "promotion_mode": "apply"},
            }

            _r, outcome, _bundle = self._run(project, ticket)

            self.assertIsNone(outcome, outcome)
            self.assertEqual(
                (project / "src/a.txt").read_text(encoding="utf-8"), "new\n",
            )

    def test_the_contract_caps_retry_attempts(self) -> None:
        """max_attempts=2 leaves one re-ask, whatever the ticket asks for."""
        from koru.queue.patch_retry import _contract_capped_budget

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._write_contract(project)
            (project / "koru.yaml").write_text(
                (project / "koru.yaml").read_text(encoding="utf-8")
                + "      max_attempts: 2\n",
                encoding="utf-8",
            )
            ticket = {
                "inputs": {"contract": "local-r1", "max_patch_attempts": 9},
            }

            self.assertEqual(_contract_capped_budget(project, ticket), 1)


class TestGrantEnforcedTransaction(_RepoCase):
    """The full loop under KORU_QUEUE_REQUIRE_GRANT: freeze → grant → mutate."""

    def _env(self, **extra):
        env = {"KORU_QUEUE_REQUIRE_GRANT": "1", "KORU_MUTATIONS_ENABLED": "1"}
        env.update(extra)
        return mock.patch.dict("os.environ", env)

    def test_without_the_kill_switch_nothing_mutates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "src/a.txt", "old\n")
            ticket = {"id": "G-1", "inputs": {"verify_command": "true"}}

            with self._env(KORU_MUTATIONS_ENABLED="0"):
                _r, outcome, _b = self._run(project, ticket)

            assert outcome is not None
            self.assertEqual(outcome.code, POLICY_DENIED)
            self.assertIn("KORU_MUTATIONS_ENABLED", outcome.message)
            self.assertEqual(
                (project / "src/a.txt").read_text(encoding="utf-8"), "old\n",
            )

    def test_with_the_gate_satisfied_the_run_lands_and_spends_its_jti(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "src/a.txt", "old\n")
            ticket = {"id": "G-2", "inputs": {"verify_command": "true", "promotion_mode": "apply"}}

            with self._env():
                _r, outcome, _b = self._run(project, ticket)

            self.assertIsNone(outcome, outcome)
            self.assertEqual(
                (project / "src/a.txt").read_text(encoding="utf-8"), "new\n",
            )
            grants = list((project / ".koru" / "grants").glob("*.json"))
            self.assertEqual(len(grants), 1, "exactly one jti was spent")
            # The bundle names the grant it ran under — same jti the store spent.
            spent_jti = grants[0].stem
            self.assertIsNotNone(_b)
            self.assertEqual(_b["authorization"]["jti"], spent_jti)
            self.assertIn("code.patch.stage", _b["authorization"]["capabilities"])
            # The journal shows the authorization happened between freeze and staging.
            from koru.queue.journal import read_events

            [journal] = (project / ".koru" / "runs").glob("*/events.jsonl")
            events = read_events(project, journal.parent.name)
            phases = [e["phase"] for e in events]
            self.assertIn("authorized", phases)
            self.assertLess(phases.index("frozen"), phases.index("authorized"))
            self.assertLess(phases.index("authorized"), phases.index("staging"))
            [authorized] = [e for e in events if e["phase"] == "authorized"]
            self.assertEqual((authorized.get("data") or {}).get("jti"), spent_jti)

    def test_an_unenforced_run_journals_no_authorized_event(self) -> None:
        """An audit must be able to tell unauthorized-but-legal from authorized."""
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "src/a.txt", "old\n")
            ticket = {"id": "G-3", "inputs": {"verify_command": "true", "promotion_mode": "apply"}}

            _r, outcome, _b = self._run(project, ticket)

            self.assertIsNone(outcome, outcome)
            from koru.queue.journal import read_events

            [journal] = (project / ".koru" / "runs").glob("*/events.jsonl")
            phases = [e["phase"] for e in read_events(project, journal.parent.name)]
            self.assertNotIn("authorized", phases)
            # ...and the bundle shows the same absence, so both artifacts agree.
            self.assertIsNotNone(_b)
            self.assertIsNone(_b["authorization"])


if __name__ == "__main__":
    unittest.main()
