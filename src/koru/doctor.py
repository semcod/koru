"""``koru --doctor`` — diagnose a koru-managed project.

When something goes wrong (LLM agent stuck, queue runner refusing to
start, policy not taking effect), the operator should run ``koru
--doctor`` first. The output is a flat list of named checks with
``pass`` / ``warn`` / ``fail`` status and a one-line detail. Both
human (text) and machine (JSON) renderings are produced from the same
report, so the LLM can also self-diagnose by parsing JSON.

Inventory of checks (stable names — ``run_diagnostics`` returns them
in this order so reports diff cleanly across runs):

    git_repo          — `.git/` resolvable from the project tree
    planfile_binary   — KORU_PLANFILE_CMD or `planfile` on PATH
    planfile_config   — `.planfile/config.yaml` exists and parses
    planfile_sprints  — at least one `.planfile/sprints/*.yaml` parses
                        and contains a `sprint.tickets` mapping
    runtime_dir       — `.planfile/.koru/` is writable (or its parent
                        is, since koru creates it lazily)
    policy_yaml       — `.planfile/.koru/policy.yaml` parses (if present)
    gitignore         — `.gitignore` ignores `.planfile/.koru/` (only
                        emitted when `.git/` is present)
    ci_command        — `policy.ci_command` first token resolves on PATH

Exit-code contract for the CLI wrapper: ``has_failures`` ⇒ ``1``;
warnings alone ⇒ ``0`` (warnings are advisory, not blocking).

The module is intentionally side-effect-free (no writes, no network).
"""

from __future__ import annotations

import os
import shlex
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .policy import policy_path
from .runtime import planfile_dir, runtime_dir


PASS = "pass"
WARN = "warn"
FAIL = "fail"
SKIP = "skip"


@dataclass
class Check:
    """A single diagnostic outcome."""

    name: str
    status: str
    detail: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


@dataclass
class DoctorReport:
    """Aggregate result of ``run_diagnostics``."""

    project: Path
    checks: list[Check] = field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return any(c.status == FAIL for c in self.checks)

    @property
    def has_warnings(self) -> bool:
        return any(c.status == WARN for c in self.checks)

    def summary(self) -> dict[str, int]:
        counts = {PASS: 0, WARN: 0, FAIL: 0, SKIP: 0}
        for check in self.checks:
            counts[check.status] = counts.get(check.status, 0) + 1
        return counts

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1",
            "project": str(self.project),
            "summary": self.summary(),
            "has_failures": self.has_failures,
            "checks": [c.to_dict() for c in self.checks],
        }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_diagnostics(project: Path) -> DoctorReport:
    """Run every check against ``project`` and return a frozen report.

    Each check is wrapped so a single buggy probe cannot crash the
    whole diagnostic run — an unexpected exception is converted into
    a ``fail`` entry with the exception's repr in ``detail``.
    """
    project = project.resolve()
    report = DoctorReport(project=project)
    has_git = (project / ".git").exists()

    probes = [
        ("git_repo", _check_git_repo),
        ("planfile_binary", _check_planfile_binary),
        ("planfile_config", _check_planfile_config),
        ("planfile_sprints", _check_planfile_sprints),
        ("planfile_sprints_yaml", _check_planfile_sprints_yaml),
        ("runtime_dir", _check_runtime_dir),
        ("policy_yaml", _check_policy_yaml),
    ]
    if has_git:
        probes.append(("gitignore", _check_gitignore))
    probes.append(("ci_command", _check_ci_command))

    for name, fn in probes:
        try:
            status, detail = fn(project)
        except Exception as exc:  # pragma: no cover — defensive guard
            status, detail = FAIL, f"probe crashed: {exc!r}"
        report.checks.append(Check(name=name, status=status, detail=detail))

    return report


# ---------------------------------------------------------------------------
# Individual probes
# ---------------------------------------------------------------------------


def _check_git_repo(project: Path) -> tuple[str, str]:
    git = project / ".git"
    if git.is_dir():
        return PASS, "initialised"
    if git.is_file():  # worktree pointer
        return PASS, "git worktree"
    return WARN, "no .git/ — git history is required for CI/CD review"


def _check_planfile_binary(_project: Path) -> tuple[str, str]:
    explicit = os.environ.get("KORU_PLANFILE_CMD")
    if explicit:
        first = shlex.split(explicit)[0] if explicit.strip() else ""
        resolved = shutil.which(first) if first else None
        if resolved or (first and Path(first).is_file()):
            return PASS, f"KORU_PLANFILE_CMD={explicit}"
        return FAIL, f"KORU_PLANFILE_CMD set but not executable: {explicit}"
    on_path = shutil.which("planfile")
    if on_path:
        return PASS, on_path
    return FAIL, "`planfile` not on PATH and KORU_PLANFILE_CMD unset"


def _check_planfile_config(project: Path) -> tuple[str, str]:
    cfg = planfile_dir(project) / "config.yaml"
    if not cfg.exists():
        return FAIL, f"missing {cfg.relative_to(project)} — run `koru --init`"
    try:
        data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return FAIL, f"YAML parse error in {cfg.relative_to(project)}: {exc}"
    if not isinstance(data, dict):
        return FAIL, "config.yaml is not a YAML mapping"
    return PASS, "valid"


def _check_planfile_sprints(project: Path) -> tuple[str, str]:
    sprints = planfile_dir(project) / "sprints"
    if not sprints.is_dir():
        return FAIL, "no .planfile/sprints/ directory"
    yamls = sorted(sprints.glob("*.yaml"))
    if not yamls:
        return FAIL, ".planfile/sprints/ is empty"
    total_tickets = 0
    bad: list[str] = []
    for path in yamls:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            bad.append(path.name)
            continue
        if not isinstance(data, dict):
            bad.append(path.name)
            continue
        sprint = data.get("sprint")
        tickets = sprint.get("tickets") if isinstance(sprint, dict) else None
        if isinstance(tickets, dict):
            total_tickets += len(tickets)
    if bad:
        return FAIL, f"unparseable sprints: {', '.join(bad)}"
    if total_tickets == 0:
        return WARN, f"{len(yamls)} sprint(s), 0 tickets — nothing to drain"
    return PASS, f"{len(yamls)} sprint(s), {total_tickets} ticket(s)"


def _check_planfile_sprints_yaml(project: Path) -> tuple[str, str]:
    sprints = planfile_dir(project) / "sprints"
    if not sprints.is_dir():
        return SKIP, "no .planfile/sprints/ directory"
    yamls = sorted(sprints.glob("*.yaml"))
    if not yamls:
        return SKIP, ".planfile/sprints/ is empty"
    errors = []
    for path in yamls:
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            errors.append(f"{path.name}: {exc}")
    if errors:
        return FAIL, f"YAML parse errors in: {', '.join(errors)}"
    return PASS, "all sprint files have valid YAML syntax"


def _check_runtime_dir(project: Path) -> tuple[str, str]:
    rt = runtime_dir(project)
    if rt.is_dir():
        if os.access(rt, os.W_OK):
            return PASS, f".planfile/.koru/ writable"
        return FAIL, ".planfile/.koru/ exists but is not writable"
    parent = rt.parent
    if parent.is_dir() and os.access(parent, os.W_OK):
        return PASS, ".planfile/.koru/ will be created on first write"
    if not parent.exists():
        return WARN, "no .planfile/ yet — run `koru --init`"
    return FAIL, f".planfile/ exists but is not writable"


def _check_policy_yaml(project: Path) -> tuple[str, str]:
    path = policy_path(project)
    if not path.exists():
        return PASS, "absent — strict defaults apply"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return FAIL, (
            "policy.yaml YAML parse error — koru is silently using "
            f"strict defaults: {exc.__class__.__name__}"
        )
    if not isinstance(data, dict):
        return FAIL, "policy.yaml is not a YAML mapping — strict defaults in use"
    llm = data.get("llm")
    if llm is not None and not isinstance(llm, dict):
        return FAIL, "policy.llm must be a mapping"
    # Detect string-truthy values (e.g. allow_commit: "true") which
    # load_policy rejects silently — flag them so the operator sees it.
    if isinstance(llm, dict):
        for key, value in llm.items():
            if key.startswith("allow_") or key.startswith("require_"):
                if not isinstance(value, bool):
                    return WARN, (
                        f"llm.{key} is {type(value).__name__} (must be bool); "
                        "koru is using the strict default for this gate"
                    )
    return PASS, "parses; loaded values match schema"


def _check_gitignore(project: Path) -> tuple[str, str]:
    gi = project / ".gitignore"
    if not gi.exists():
        return WARN, ".gitignore missing — runtime artefacts may be committed"
    text = gi.read_text(encoding="utf-8")
    needle = ".planfile/.koru/"
    if any(line.strip() == needle for line in text.splitlines()):
        return PASS, f"ignores {needle}"
    return WARN, f".gitignore does not list {needle} — re-run `koru --init`"


def _check_ci_command(project: Path) -> tuple[str, str]:
    from .policy import load_policy

    policy = load_policy(project)
    if not policy.ci_command.strip():
        return WARN, (
            "policy.ci.command is empty — agent must defer to a human "
            "for CI verification before completing tickets"
        )
    try:
        first = shlex.split(policy.ci_command)[0]
    except ValueError as exc:
        return FAIL, f"ci.command unparseable: {exc}"
    resolved = shutil.which(first)
    if resolved:
        return PASS, f"`{policy.ci_command}` (resolves to {resolved})"
    if Path(first).is_file():
        return PASS, f"`{policy.ci_command}` (file exists)"
    return FAIL, f"ci.command first token `{first}` not on PATH"


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


_STATUS_GLYPH = {PASS: "OK ", WARN: "WARN", FAIL: "FAIL", SKIP: "SKIP"}


def render_text(report: DoctorReport) -> str:
    """Human-readable rendering — fixed-width status column."""
    lines: list[str] = []
    lines.append(f"koru doctor — {report.project}")
    lines.append("")
    width = max((len(c.name) for c in report.checks), default=0)
    for c in report.checks:
        glyph = _STATUS_GLYPH.get(c.status, c.status.upper())
        lines.append(f"  [{glyph}] {c.name.ljust(width)}  {c.detail}")
    counts = report.summary()
    total = sum(counts.values())
    parts = [f"{total} checks"]
    if counts.get(PASS):
        parts.append(f"{counts[PASS]} passed")
    if counts.get(WARN):
        parts.append(f"{counts[WARN]} warning(s)")
    if counts.get(FAIL):
        parts.append(f"{counts[FAIL]} failed")
    lines.append("")
    lines.append("  " + ", ".join(parts))
    return "\n".join(lines)
