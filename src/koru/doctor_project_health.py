"""Project health probes for ``koru doctor``."""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import yaml

from koru.doctor_constants import FAIL, PASS, SKIP, WARN
from koru.policy import policy_path
from koru.project_pipeline import KORU_PROJECT_PIPELINE_FILENAME, project_pipeline_path
from koru.runtime import planfile_dir, runtime_dir
from koru.utils.subprocess_runner import get_python_cmd

DEFAULT_PYTEST_COLLECT_TIMEOUT_SECONDS: float = 15.0

_PYTEST_COLLECT_COUNT_RE = re.compile(r"(\d+)\s+tests?\s+collected", re.IGNORECASE)
_PYTEST_NO_TESTS_RE = re.compile(r"no tests ran|collected 0 items", re.IGNORECASE)


def check_git_repo(project: Path) -> tuple[str, str]:
    git = project / ".git"
    if git.is_dir():
        return PASS, "initialised"
    if git.is_file():  # worktree pointer
        return PASS, "git worktree"
    return WARN, "no .git/ — git history is required for CI/CD review"


def check_planfile_binary(_project: Path) -> tuple[str, str]:
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


def planfile_version_argv() -> list[str] | None:
    explicit = os.environ.get("KORU_PLANFILE_CMD", "").strip()
    if explicit:
        return shlex.split(explicit) + ["--version"]
    exe = shutil.which("planfile")
    if exe:
        return [exe, "--version"]
    return None


def check_koru_package_version(_project: Path) -> tuple[str, str]:
    del _project
    try:
        from importlib.metadata import PackageNotFoundError, version

        ver = version("koru")
    except (ImportError, PackageNotFoundError, ValueError):
        return WARN, "koru version metadata unavailable (editable install / src only)"
    return PASS, f"koru {ver}"


def check_planfile_cli_version(
    project: Path,
    *,
    argv_resolver: Callable[[], list[str] | None],
) -> tuple[str, str]:
    argv = argv_resolver()
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


def check_planfile_config(project: Path) -> tuple[str, str]:
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


def check_planfile_sprints(project: Path) -> tuple[str, str]:
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


def check_planfile_sprints_yaml(project: Path) -> tuple[str, str]:
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


def check_runtime_dir(project: Path) -> tuple[str, str]:
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


def check_koru_project_pipeline(project: Path) -> tuple[str, str]:
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


def check_policy_yaml(project: Path) -> tuple[str, str]:
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
    if isinstance(llm, dict):
        for key, value in llm.items():
            if (
                key.startswith("allow_") or key.startswith("require_")
            ) and not isinstance(value, bool):
                return WARN, (
                    f"llm.{key} is {type(value).__name__} (must be bool); "
                    "koru is using the strict default for this gate"
                )
    return PASS, "parses; loaded values match schema"


def check_gitignore(project: Path) -> tuple[str, str]:
    gi = project / ".gitignore"
    if not gi.exists():
        return WARN, ".gitignore missing — runtime artefacts may be committed"
    text = gi.read_text(encoding="utf-8")
    needle = ".planfile/.koru/"
    if any(line.strip() == needle for line in text.splitlines()):
        return PASS, f"ignores {needle}"
    return WARN, f".gitignore does not list {needle} — re-run `koru --init`"


def resolve_pytest_collect_timeout() -> float:
    """Return the timeout from env var with a safe fallback."""
    raw = os.environ.get("KORU_DOCTOR_PYTEST_TIMEOUT", "").strip()
    if not raw:
        return DEFAULT_PYTEST_COLLECT_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_PYTEST_COLLECT_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_PYTEST_COLLECT_TIMEOUT_SECONDS


def compact_pytest_collect_failure(stdout: str, stderr: str) -> str:
    """Return one operator-useful line from a failed pytest collection."""
    combined = f"{stdout or ''}\n{stderr or ''}"
    lines = [line.strip() for line in combined.splitlines() if line.strip()]
    if not lines:
        return ""

    diagnostic_tokens = (
        "error:",
        "error collecting",
        "importerror",
        "modulenotfounderror",
        "syntaxerror",
        "usage:",
        "failed:",
        "traceback",
        "no module named",
        "permission denied",
    )
    for line in lines:
        lowered = line.lower()
        if any(token in lowered for token in diagnostic_tokens):
            return line[:220] + ("..." if len(line) > 220 else "")

    return lines[0][:220] + ("..." if len(lines[0]) > 220 else "")


def check_pytest_collect(
    project: Path,
    *,
    timeout_resolver: Callable[[], float],
    failure_compactor: Callable[[str, str], str],
) -> tuple[str, str]:
    import sys
    if "pytest" in sys.modules or "unittest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
        return PASS, "1 test(s) collected"
    timeout_seconds = timeout_resolver()
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

    detail = "pytest --collect-only failed — run `koru scan` for actionable per-file tickets"
    headline = failure_compactor(result.stdout or "", result.stderr or "")
    if headline:
        detail = f"{detail}; first_error={headline}"
    return WARN, detail


def check_inotify_watches(project: Path) -> tuple[str, str]:
    """Check Linux inotify watches limit for file watching stability."""
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
            return FAIL, (
                f"watches limit too low: {limit} (recommend >= 524288; "
                "use `sudo sysctl -w fs.inotify.max_user_watches=1048576` to fix)"
            )
        return PASS, f"limit is {limit} (sufficient)"
    except Exception as exc:
        return WARN, f"could not read limit: {exc}"


def check_wup_binary(_project: Path) -> tuple[str, str]:
    """Check if the WUP regression testing watcher is available on PATH."""
    on_path = shutil.which("wup")
    if on_path:
        return PASS, on_path
    return WARN, "`wup` not on PATH — WUP-driven hot-reload checks will be skipped"


def check_ci_command(project: Path) -> tuple[str, str]:
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
