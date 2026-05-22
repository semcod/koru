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
    pytest_collect    — `python3 -m pytest --collect-only` exits 0 within
                        15 s (override via ``KORU_DOCTOR_PYTEST_TIMEOUT``).
                        Only emitted when ``pyproject.toml`` or ``tests/``
                        exists; pairs with ``koru scan``'s timeout fix to
                        catch hung collection (see PLF-093 post-mortem).
    koru_project_pipeline — root ``koru.yaml`` exists and parses when the
                        project is planfile-initialised (``SKIP`` before
                        ``.planfile/config.yaml``).
    autonomous_environ — ``TICKET_SOURCES`` / idle-diag / WUP-related env vars
                        for ``koru autonomous up`` (``FAIL`` on invalid
                        ``TICKET_SOURCES``).
    agent_backends_registry — static profile ids from ``koru.agent_backends``
                        (``PASS`` when the registry loads; see
                        ``koru agent-backends``).
    koru_package_version — installed ``koru`` distribution version (``WARN`` if
                        metadata missing, e.g. bare source tree).
    planfile_cli_version — ``planfile --version`` / ``KORU_PLANFILE_CMD … --version``
                        (``SKIP`` when no planfile executable).

Exit-code contract for the CLI wrapper: ``has_failures`` ⇒ ``1``;
warnings alone ⇒ ``0`` (warnings are advisory, not blocking).

The module is intentionally side-effect-free (no writes, no network).
"""


import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from koru.autonomous_env import autonomous_environ_doctor_probe
from koru.policy import policy_path
from koru.project_pipeline import KORU_PROJECT_PIPELINE_FILENAME, project_pipeline_path
from koru.runtime import planfile_dir, runtime_dir
from koru.utils.subprocess_runner import get_python_cmd

# Default timeout for the pytest-collect probe. Doctor is meant to be
# *interactive and fast*; we deliberately keep this tighter than
# ``scan_pytest_collect``'s 30 s so the operator does not stare at a
# black terminal for half a minute. Override via ``KORU_DOCTOR_PYTEST_TIMEOUT``.
DEFAULT_PYTEST_COLLECT_TIMEOUT_SECONDS: float = 15.0


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
        ("koru_package_version", _check_koru_package_version),
        ("planfile_cli_version", _check_planfile_cli_version),
        ("planfile_config", _check_planfile_config),
        ("planfile_sprints", _check_planfile_sprints),
        ("planfile_sprints_yaml", _check_planfile_sprints_yaml),
        ("runtime_dir", _check_runtime_dir),
        ("policy_yaml", _check_policy_yaml),
        ("koru_project_pipeline", _check_koru_project_pipeline),
        ("autonomous_environ", autonomous_environ_doctor_probe),
        ("agent_backends_registry", _check_agent_backends_registry),
        ("inotify_watches", _check_inotify_watches),
        ("wup_binary", _check_wup_binary),
    ]
    if has_git:
        probes.append(("gitignore", _check_gitignore))
    probes.append(("ci_command", _check_ci_command))
    # pytest_collect runs last because it's the slowest probe (subprocess
    # + 15 s timeout). Putting it at the end means the cheaper checks
    # complete first — the operator can already start reading their
    # results while pytest is still warming up.
    if (project / "tests").exists() or (project / "pyproject.toml").exists():
        probes.append(("pytest_collect", _check_pytest_collect))

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


def _check_agent_backends_registry(_project: Path) -> tuple[str, str]:
    del _project
    from koru.agent_backends import list_agent_backend_ids

    ids = list_agent_backend_ids()
    return PASS, f"{len(ids)} profiles: {', '.join(ids)}"


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


def _planfile_version_argv() -> list[str] | None:
    explicit = os.environ.get("KORU_PLANFILE_CMD", "").strip()
    if explicit:
        return shlex.split(explicit) + ["--version"]
    exe = shutil.which("planfile")
    if exe:
        return [exe, "--version"]
    return None


def _check_koru_package_version(_project: Path) -> tuple[str, str]:
    del _project
    try:
        from importlib.metadata import PackageNotFoundError, version

        ver = version("koru")
    except (ImportError, PackageNotFoundError, ValueError):
        return WARN, "koru version metadata unavailable (editable install / src only)"
    return PASS, f"koru {ver}"


def _check_planfile_cli_version(project: Path) -> tuple[str, str]:
    argv = _planfile_version_argv()
    if not argv:
        return SKIP, "no planfile executable"
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=8,
            cwd=str(project.resolve()),
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return WARN, f"planfile --version failed: {exc}"
    blob = f"{proc.stdout or ''}\n{proc.stderr or ''}"
    for line in blob.splitlines():
        if "version" in line.lower() and any(ch.isdigit() for ch in line):
            return PASS, line.strip()[:180]
    return WARN, "planfile --version produced no parseable version line"


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
            return PASS, ".planfile/.koru/ writable"
        return FAIL, ".planfile/.koru/ exists but is not writable"
    parent = rt.parent
    if parent.is_dir() and os.access(parent, os.W_OK):
        return PASS, ".planfile/.koru/ will be created on first write"
    if not parent.exists():
        return WARN, "no .planfile/ yet — run `koru --init`"
    return FAIL, ".planfile/ exists but is not writable"


def _check_koru_project_pipeline(project: Path) -> tuple[str, str]:
    cfg = planfile_dir(project) / "config.yaml"
    if not cfg.is_file():
        return SKIP, "no planfile config (project not initialised)"
    path = project_pipeline_path(project)
    if not path.is_file():
        return WARN, (
            f"missing {KORU_PROJECT_PIPELINE_FILENAME} — "
            "`koru --init` on a fresh repo creates one; copy from another project or add manually"
        )
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return FAIL, f"{KORU_PROJECT_PIPELINE_FILENAME}: {exc}"
    if not isinstance(data, dict):
        return FAIL, f"{KORU_PROJECT_PIPELINE_FILENAME}: expected YAML mapping at top level"
    schema = data.get("schema")
    if schema is not None and str(schema) not in ("1.0", "1"):
        return WARN, f"unknown schema {schema!r} (expected 1.0)"
    return PASS, f"{KORU_PROJECT_PIPELINE_FILENAME} present"


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
            if (key.startswith("allow_") or key.startswith("require_")) and not isinstance(
                value, bool
            ):
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


_PYTEST_COLLECT_COUNT_RE = re.compile(r"(\d+)\s+tests?\s+collected", re.IGNORECASE)
_PYTEST_NO_TESTS_RE = re.compile(r"no tests ran|collected 0 items", re.IGNORECASE)


def _resolve_pytest_collect_timeout() -> float:
    """Return the timeout from env var with a safe fallback.

    Env override exists for two reasons: (1) operators on slow CI boxes
    can extend it; (2) tests can shrink it to keep the suite fast.
    Invalid values silently fall back to the default — the operator
    should not be punished for a typo in their shell rc.
    """
    raw = os.environ.get("KORU_DOCTOR_PYTEST_TIMEOUT", "").strip()
    if not raw:
        return DEFAULT_PYTEST_COLLECT_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_PYTEST_COLLECT_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_PYTEST_COLLECT_TIMEOUT_SECONDS


def _check_pytest_collect(project: Path) -> tuple[str, str]:
    """Run ``pytest --collect-only`` and report whether collection works.

    This is the fast diagnostic counterpart to ``koru scan``'s pytest
    probe. The two share the same root concern — *can pytest even load
    its tests?* — but with different roles:

    - ``koru scan`` creates a ticket when collection fails or times out.
    - ``koru doctor`` returns a status line so the operator can see the
      health of the test infrastructure at a glance, without committing
      anything to the queue.

    Status mapping:
      PASS — exit 0; report N tests collected if parseable.
      WARN — exit non-zero; collection broke. Suggest ``koru scan`` for
             per-file detail rather than dumping pytest's stderr here.
      FAIL — timeout. Strongest signal: pytest is hung, not just broken.
             The operator should treat this as a release blocker.
      SKIP — pytest binary missing; doctor cannot diagnose further.
    """
    timeout_seconds = _resolve_pytest_collect_timeout()
    cmd = get_python_cmd(project) + ["-m", "pytest", "--collect-only", "-q", "--no-header"]
    try:
        result = subprocess.run(
            cmd,
            cwd=project,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return FAIL, (
            f"pytest --collect-only hung > {timeout_seconds:g}s — investigate "
            "heavy conftest imports or runaway test discovery "
            "(see `koru scan` for a queueable ticket with checklist)"
        )
    except (FileNotFoundError, OSError):
        return SKIP, "pytest not invokable (python3/pytest missing on PATH)"

    output = f"{result.stdout or ''}\n{result.stderr or ''}"
    if result.returncode == 0:
        match = _PYTEST_COLLECT_COUNT_RE.search(output)
        if match:
            return PASS, f"{match.group(1)} test(s) collected"
        if _PYTEST_NO_TESTS_RE.search(output):
            return WARN, "0 tests collected — verify testpaths / discovery rules"
        return PASS, "collection clean (count not parseable)"

    # Non-zero exit: collection failed. Keep the detail short — `koru
    # scan` is the place to dig into per-file errors. We just tell the
    # operator *that* it's broken and where to look.
    return WARN, ("pytest --collect-only failed — run `koru scan` for actionable per-file tickets")


def _check_inotify_watches(project: Path) -> tuple[str, str]:
    """Check Linux inotify watches limit (for WUP/watchdog file watching stability)."""
    import sys
    del project
    if sys.platform != "linux":
        return SKIP, "only applicable on Linux"

    path = Path("/proc/sys/fs/inotify/max_user_watches")
    if not path.is_file():
        return SKIP, f"{path} not found"

    try:
        limit_str = path.read_text(encoding="utf-8").strip()
        limit = int(limit_str)
        if limit < 524288:
            return FAIL, f"watches limit too low: {limit} (recommend >= 524288; use `sudo sysctl -w fs.inotify.max_user_watches=1048576` to fix)"
        return PASS, f"limit is {limit} (sufficient)"
    except Exception as exc:
        return WARN, f"could not read limit: {exc}"


def _check_wup_binary(_project: Path) -> tuple[str, str]:
    """Check if the WUP regression testing watcher is available on PATH."""
    import shutil
    on_path = shutil.which("wup")
    if on_path:
        return PASS, on_path
    return WARN, "`wup` not on PATH — WUP-driven hot-reload checks will be skipped"


def _check_ci_command(project: Path) -> tuple[str, str]:
    from koru.policy import load_policy

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
    lines.append(f"  {', '.join(parts)}")
    return "\n".join(lines)
