"""LLM agent control policy for koru.

This module is the **gate**. When an LLM agent (Cascade, Cursor, aider,
local model, …) is driving a koru-managed project, it MUST first read
the policy via ``koru --context`` and obey it. The defaults are
deliberately strict:

- the agent does NOT make commits, branches, pushes, or PRs by itself;
- the agent does NOT touch files outside the ticket's declared scope;
- the agent does NOT mark a ticket complete until the project's CI
  command exits 0;
- the agent does NOT bypass planfile (no direct sprint YAML edits).

A project can relax these defaults by writing
``<project>/.planfile/.koru/policy.yaml``. There is no way to relax
them from the command line — that is a deliberate design choice so
that "force the LLM to skip CI" requires a tracked YAML edit.

The policy is also embedded verbatim in every ``koru --context`` brief
so the LLM has zero ambiguity about what is allowed.
"""


from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

POLICY_FILENAME = "policy.yaml"


# Strict-by-default constants. Editing these requires a code change AND
# a passing test — they are the security floor for autonomous agents.
DEFAULT_FORBIDDEN_PATHS: tuple[str, ...] = (
    ".git/",
    ".github/",
    ".planfile/",  # planfile owns this — only via planfile CLI
    ".env",
    "secrets/",
    "*.pem",
    "*.key",
    "id_rsa",
    "id_ed25519",
    "node_modules/",  # never let the agent touch installed deps
)

DEFAULT_FORBIDDEN_SHELL_PATTERNS: tuple[str, ...] = (
    "rm -rf /",
    "rm -rf ~",
    "rm -rf $HOME",
    ":(){:|:&};:",  # fork bomb
    "dd if=",
    "mkfs",
    "> /dev/sda",
    "shutdown",
    "reboot",
    "git push --force",
    "git push -f",
    "git reset --hard HEAD~",  # rewrite history
)


@dataclass(frozen=True)
class Policy:
    """Resolved policy for an LLM agent operating on a koru project.

    All boolean fields default to the *most restrictive* value. A YAML
    override can only loosen them where the project owner has decided
    it is safe.
    """

    # Git-level gates. These are the most important rules: the agent
    # never touches the version-control layer directly. All commits go
    # through CI/CD or the human operator.
    allow_commit: bool = False
    allow_push: bool = False
    allow_branch_create: bool = False
    allow_branch_switch: bool = False
    allow_tag: bool = False

    # Filesystem gates.
    forbidden_paths: tuple[str, ...] = DEFAULT_FORBIDDEN_PATHS
    forbidden_shell_patterns: tuple[str, ...] = DEFAULT_FORBIDDEN_SHELL_PATTERNS
    allow_destructive_shell: bool = False

    # Workflow gates — the agent must use planfile for state changes.
    require_planfile_lifecycle: bool = True
    require_ci_pass_before_complete: bool = True

    # Optional CI verification command (e.g. ``pytest -q``).
    # Empty string ⇒ no automated CI gate, agent must request a human review.
    ci_command: str = ""
    ci_timeout_seconds: int = 300

    # Free-form notes the project owner wants to surface in every brief
    # (e.g. "use uv, not pip" or "always run black before signaling done").
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Stable, sorted dict suitable for embedding in a JSON brief."""
        return {
            "allow_branch_create": self.allow_branch_create,
            "allow_branch_switch": self.allow_branch_switch,
            "allow_commit": self.allow_commit,
            "allow_destructive_shell": self.allow_destructive_shell,
            "allow_push": self.allow_push,
            "allow_tag": self.allow_tag,
            "ci_command": self.ci_command,
            "ci_timeout_seconds": self.ci_timeout_seconds,
            "forbidden_paths": list(self.forbidden_paths),
            "forbidden_shell_patterns": list(self.forbidden_shell_patterns),
            "notes": list(self.notes),
            "require_ci_pass_before_complete": self.require_ci_pass_before_complete,
            "require_planfile_lifecycle": self.require_planfile_lifecycle,
        }


def policy_path(project: Path) -> Path:
    """Return the policy YAML location: ``<project>/.planfile/.koru/policy.yaml``."""
    from koru.utils.subprocess_runner import resolve_planfile_subpath

    return resolve_planfile_subpath(project, ".koru", POLICY_FILENAME)


def load_policy(project: Path) -> Policy:
    """Load the policy for a project, falling back to safe defaults.

    Missing file ⇒ defaults. Malformed YAML ⇒ defaults (so a corrupt
    file can never silently *loosen* the policy — it can only fail
    closed). Unknown keys are ignored to allow forward compatibility.

    Boolean overrides are accepted only if the YAML value is a real
    bool — strings like ``"true"`` are rejected, again to fail closed.
    """
    path = policy_path(project)
    if not path.exists():
        return Policy()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return Policy()
    if not isinstance(raw, dict):
        return Policy()

    llm = raw.get("llm") if isinstance(raw.get("llm"), dict) else {}
    ci = raw.get("ci") if isinstance(raw.get("ci"), dict) else {}

    def _b(key: str, default: bool) -> bool:
        value = llm.get(key)
        return value if isinstance(value, bool) else default

    def _str_tuple(key: str, default: tuple[str, ...]) -> tuple[str, ...]:
        value = llm.get(key)
        if not isinstance(value, list):
            return default
        return tuple(str(item) for item in value if isinstance(item, str))

    def _ci_str(key: str, default: str) -> str:
        value = ci.get(key)
        return value if isinstance(value, str) else default

    def _ci_int(key: str, default: int) -> int:
        value = ci.get(key)
        return value if isinstance(value, int) and value > 0 else default

    notes_raw = raw.get("notes")
    notes = (
        tuple(str(item) for item in notes_raw if isinstance(item, str))
        if isinstance(notes_raw, list)
        else ()
    )

    return Policy(
        allow_commit=_b("allow_commit", False),
        allow_push=_b("allow_push", False),
        allow_branch_create=_b("allow_branch_create", False),
        allow_branch_switch=_b("allow_branch_switch", False),
        allow_tag=_b("allow_tag", False),
        allow_destructive_shell=_b("allow_destructive_shell", False),
        forbidden_paths=_str_tuple("forbidden_paths", DEFAULT_FORBIDDEN_PATHS),
        forbidden_shell_patterns=_str_tuple(
            "forbidden_shell_patterns",
            DEFAULT_FORBIDDEN_SHELL_PATTERNS,
        ),
        require_planfile_lifecycle=_b("require_planfile_lifecycle", True),
        require_ci_pass_before_complete=_b("require_ci_pass_before_complete", True),
        ci_command=_ci_str("command", ""),
        ci_timeout_seconds=_ci_int("timeout_seconds", 300),
        notes=notes,
    )


def _check_git_commit_policy(policy: Policy, command: str, violations: list[str]) -> None:
    """Check git commit policy violations."""
    if not policy.allow_commit and "git commit" in command:
        violations.append("policy.allow_commit=false: 'git commit' is forbidden")


def _check_git_push_policy(policy: Policy, command: str, violations: list[str]) -> None:
    """Check git push policy violations."""
    if not policy.allow_push and "git push" in command:
        violations.append("policy.allow_push=false: 'git push' is forbidden")


def _check_git_branch_create_policy(policy: Policy, command: str, violations: list[str]) -> None:
    """Check git branch creation policy violations."""
    if not policy.allow_branch_create and (
        "git branch " in f" {command} "
        or "git checkout -b" in command
        or "git switch -c" in command
    ):
        violations.append("policy.allow_branch_create=false: creating branches is forbidden")


def _check_git_branch_switch_policy(policy: Policy, command: str, violations: list[str]) -> None:
    """Check git branch switching policy violations."""
    if (
        not policy.allow_branch_switch
        and ("git checkout " in command and "-b" not in command)
        or ("git switch " in command and "-c" not in command)
    ):
        violations.append("policy.allow_branch_switch=false: switching branches is forbidden")


def _check_git_tag_policy(policy: Policy, command: str, violations: list[str]) -> None:
    """Check git tag policy violations."""
    if not policy.allow_tag and "git tag" in command:
        violations.append("policy.allow_tag=false: tagging is forbidden")


def _check_destructive_shell_policy(policy: Policy, command: str, violations: list[str]) -> None:
    """Check destructive shell pattern violations."""
    if not policy.allow_destructive_shell:
        for pattern in policy.forbidden_shell_patterns:
            if pattern and pattern in command:
                violations.append(
                    f"policy.allow_destructive_shell=false: forbidden pattern '{pattern}'",
                )


def policy_violations(policy: Policy, command: str) -> list[str]:
    """Return a list of policy violations for a candidate shell command.

    Empty list ⇒ command is allowed under the policy. The check is
    purely lexical (substring match on each forbidden pattern) so it
    can flag obviously dangerous commands without parsing every shell
    grammar. The LLM is expected to use this as a pre-flight check
    BEFORE asking the user for execution approval.
    """
    if not isinstance(command, str) or not command.strip():
        return []
    violations: list[str] = []

    _check_git_commit_policy(policy, command, violations)
    _check_git_push_policy(policy, command, violations)
    _check_git_branch_create_policy(policy, command, violations)
    _check_git_branch_switch_policy(policy, command, violations)
    _check_git_tag_policy(policy, command, violations)
    _check_destructive_shell_policy(policy, command, violations)

    return violations
