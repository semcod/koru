"""Subprocess runner utilities."""

import subprocess
from collections.abc import Sequence
from pathlib import Path


def default_subprocess_runner(cmd: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Default subprocess runner with standard options."""
    return subprocess.run(
        list(cmd),
        cwd=cwd,
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
    Prefers project-local .venv/bin/python if it exists.
    """
    for venv_name in (".venv", "venv"):
        candidate = Path(project) / venv_name / "bin" / "python"
        if candidate.is_file():
            return [str(candidate)]
    return ["python3"]
