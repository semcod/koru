"""Tests for the LLM-agent control policy.

The policy is the security floor: defaults must always be the most
restrictive option, malformed YAML must NEVER loosen them, and a
``policy_violations`` check must reliably flag obvious offences.
"""

from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from koru.policy import (
    DEFAULT_FORBIDDEN_PATHS,
    DEFAULT_FORBIDDEN_SHELL_PATTERNS,
    Policy,
    load_policy,
    policy_path,
    policy_violations,
)
from koru.runtime import runtime_dir


def _write_policy(project: Path, content: str) -> None:
    rt = runtime_dir(project)
    rt.mkdir(parents=True, exist_ok=True)
    (rt / "policy.yaml").write_text(textwrap.dedent(content), encoding="utf-8")


class TestDefaults(unittest.TestCase):
    def test_defaults_are_strict(self) -> None:
        policy = Policy()
        self.assertFalse(policy.allow_commit)
        self.assertFalse(policy.allow_push)
        self.assertFalse(policy.allow_branch_create)
        self.assertFalse(policy.allow_branch_switch)
        self.assertFalse(policy.allow_tag)
        self.assertFalse(policy.allow_destructive_shell)
        self.assertTrue(policy.require_planfile_lifecycle)
        self.assertTrue(policy.require_ci_pass_before_complete)
        self.assertEqual(policy.ci_command, "")

    def test_default_forbidden_paths_include_critical(self) -> None:
        defaults = set(DEFAULT_FORBIDDEN_PATHS)
        for must_have in (".git/", ".env", ".planfile/", "secrets/"):
            self.assertIn(must_have, defaults)

    def test_default_shell_patterns_include_critical(self) -> None:
        defaults = " ".join(DEFAULT_FORBIDDEN_SHELL_PATTERNS)
        for must_have in ("rm -rf /", "git push --force", "shutdown"):
            self.assertIn(must_have, defaults)

    def test_to_dict_keys_are_sorted(self) -> None:
        d = Policy().to_dict()
        self.assertEqual(list(d.keys()), sorted(d.keys()))


class TestLoad(unittest.TestCase):
    def test_missing_file_returns_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_policy(Path(tmp)), Policy())

    def test_malformed_yaml_falls_back_to_defaults(self) -> None:
        """Critical: corrupt YAML must NEVER loosen the policy."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_policy(project, "this is: : not valid: : yaml")
            policy = load_policy(project)
            self.assertFalse(policy.allow_commit)
            self.assertFalse(policy.allow_push)

    def test_top_level_non_mapping_falls_back_to_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_policy(project, "- just\n- a list\n")
            policy = load_policy(project)
            self.assertFalse(policy.allow_commit)

    def test_string_truthy_value_is_rejected(self) -> None:
        """YAML that passes 'true' as a string must NOT loosen the policy."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_policy(
                project,
                """\
                llm:
                  allow_commit: "true"
                  allow_push: "yes"
            """,
            )
            policy = load_policy(project)
            self.assertFalse(policy.allow_commit)
            self.assertFalse(policy.allow_push)

    def test_explicit_loosening_is_honoured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_policy(
                project,
                """\
                llm:
                  allow_commit: true
                  allow_branch_create: true
                ci:
                  command: pytest -q
                  timeout_seconds: 60
                notes:
                  - "Always run black before signaling done."
            """,
            )
            policy = load_policy(project)
            self.assertTrue(policy.allow_commit)
            self.assertTrue(policy.allow_branch_create)
            self.assertFalse(policy.allow_push)  # not loosened — still false
            self.assertEqual(policy.ci_command, "pytest -q")
            self.assertEqual(policy.ci_timeout_seconds, 60)
            self.assertIn("Always run black before signaling done.", policy.notes)

    def test_zero_or_negative_timeout_falls_back_to_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_policy(
                project,
                """\
                ci:
                  timeout_seconds: -5
            """,
            )
            self.assertEqual(load_policy(project).ci_timeout_seconds, 300)

    def test_unknown_keys_are_ignored(self) -> None:
        """Forward-compat: unknown keys do not error."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_policy(
                project,
                """\
                llm:
                  allow_commit: false
                  unknown_future_key: 42
            """,
            )
            policy = load_policy(project)
            self.assertFalse(policy.allow_commit)


class TestViolations(unittest.TestCase):
    def test_git_commit_blocked_by_default(self) -> None:
        v = policy_violations(Policy(), 'git commit -m "x"')
        self.assertEqual(len(v), 1)
        self.assertIn("allow_commit=false", v[0])

    def test_git_push_blocked_by_default(self) -> None:
        v = policy_violations(Policy(), "git push origin main")
        self.assertTrue(any("allow_push=false" in m for m in v))

    def test_force_push_double_flag(self) -> None:
        """git push --force triggers BOTH allow_push and destructive."""
        v = policy_violations(Policy(), "git push --force")
        self.assertGreaterEqual(len(v), 2)
        self.assertTrue(any("allow_push" in m for m in v))
        self.assertTrue(any("forbidden pattern" in m for m in v))

    def test_branch_create_blocked(self) -> None:
        v = policy_violations(Policy(), "git checkout -b feature/x")
        self.assertTrue(any("branch" in m for m in v))

    def test_rm_rf_root_blocked(self) -> None:
        v = policy_violations(Policy(), "rm -rf /")
        self.assertTrue(any("rm -rf /" in m for m in v))

    def test_safe_command_passes(self) -> None:
        v = policy_violations(Policy(), "pytest -q")
        self.assertEqual(v, [])

    def test_empty_command_passes(self) -> None:
        self.assertEqual(policy_violations(Policy(), ""), [])
        self.assertEqual(policy_violations(Policy(), "   "), [])

    def test_loosened_policy_allows_commit(self) -> None:
        relaxed = Policy(allow_commit=True, allow_push=True)
        self.assertEqual(policy_violations(relaxed, 'git commit -m "x"'), [])

    def test_path_helper_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            expected = Path(tmp).resolve() / ".planfile" / ".koru" / "policy.yaml"
            self.assertEqual(policy_path(Path(tmp)), expected)


if __name__ == "__main__":
    unittest.main()
