"""Subprocess runner utilities."""

import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path


def sanitized_subprocess_env(project: Path | None = None) -> dict[str, str]:
    """Return an environment for project subprocesses without foreign venv site-packages."""
    env = dict(os.environ)
    env.pop("PYTHONHOME", None)
    project_venvs: tuple[str, ...] = ()
    if project is not None:
        resolved = Path(project).resolve()
        project_venvs = tuple(
            str((resolved / name).resolve())
            for name in (".venv", "venv")
            if (resolved / name).exists()
        )
    raw_pythonpath = env.get("PYTHONPATH", "")
    if raw_pythonpath:
        kept: list[str] = []
        for entry in raw_pythonpath.split(os.pathsep):
            cleaned = entry.strip()
            if not cleaned:
                continue
            normalized = cleaned.rstrip("/")
            if "/.local/share/koru/runtime/" in normalized:
                continue
            if normalized.endswith(("/site-packages", "/dist-packages")):
                if project_venvs and any(normalized.startswith(v + "/") for v in project_venvs):
                    kept.append(cleaned)
                continue
            kept.append(cleaned)
        if kept:
            env["PYTHONPATH"] = os.pathsep.join(kept)
        else:
            env.pop("PYTHONPATH", None)
    venv_var = env.get("VIRTUAL_ENV", "")
    if venv_var and "/.local/share/koru/runtime/" in venv_var:
        env.pop("VIRTUAL_ENV", None)
    return env


def default_subprocess_runner(cmd: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Default subprocess runner with standard options."""
    return subprocess.run(
        list(cmd),
        cwd=cwd,
        env=sanitized_subprocess_env(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def resolve_planfile_subpath(project: Path, *parts: str) -> Path:
    """Resolve a path under the project's .planfile directory.

    Args:
        project: Project root directory.
        *parts: Path components to append to .planfile/ (e.g., ".koru", "policy.yaml").

    Returns:
        Absolute path under <project>/.planfile/.
    """
    return Path(project).resolve() / ".planfile" / Path(*parts)


def get_python_cmd(project: Path) -> list[str]:
    """Return command list starting the best available Python interpreter.
    Prefers project-local .venv/bin/python if it exists, then sys.executable.
    """
    for venv_name in (".venv", "venv"):
        candidate = Path(project) / venv_name / "bin" / "python"
        if candidate.is_file():
            return [str(candidate)]
    return [sys.executable] if sys.executable else ["python3"]
