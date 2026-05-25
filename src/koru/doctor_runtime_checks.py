"""Runtime identity and virtualenv checks for ``koru --doctor``."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

from koru.doctor_constants import PASS, WARN


def _read_project_version(path: Path) -> str | None:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    project = data.get("project")
    if not isinstance(project, dict):
        return None
    version = project.get("version")
    return str(version) if version else None


def _installed_koru_version() -> str | None:
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version("koru")
    except (ImportError, PackageNotFoundError, ValueError):
        return None


def _path_koru_supports_auto_subcommand(path_koru: str | None) -> bool | None:
    """Probe whether ``koru auto`` works on the executable first on PATH."""
    if not path_koru:
        return None
    try:
        proc = subprocess.run(
            [path_koru, "auto", "--help"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    combined = f"{proc.stdout or ''}\n{proc.stderr or ''}"
    if "unrecognized arguments: auto" in combined:
        return False
    if proc.returncode == 0 and (
        "koru autonomous" in combined or "alias:" in combined.lower()
    ):
        return True
    return proc.returncode == 0 if proc.returncode == 0 else False


def _koru_path_version_issues(
    project_koru: Path,
    path_koru: str | None,
    package_version: str | None,
    source_version: str | None,
) -> tuple[str, list[str]]:
    """Return (status, extra_bits) for path-mismatch and version checks."""
    status = PASS
    bits: list[str] = []
    if project_koru.is_file() and path_koru:
        try:
            if Path(path_koru).resolve() != project_koru.resolve():
                status = WARN
                bits.append("path_mismatch=true")
        except OSError:
            status = WARN
            bits.append("path_mismatch=unknown")
    auto_ok = _path_koru_supports_auto_subcommand(path_koru)
    if auto_ok is False:
        status = WARN
        bits.append("koru_auto_unsupported=true")
        if project_koru.is_file():
            bits.append(
                f"fix=export PATH={project_koru.parent}:$PATH; hash -r; or {project_koru} auto"
            )
        else:
            bits.append("fix=pip install -e . && use koru autonomous")
    if package_version and source_version and package_version != source_version:
        status = WARN
        bits.append("version_mismatch=true")
    if package_version is None:
        status = WARN
        bits.append("package_metadata=missing")
    return status, bits


def _check_koru_runtime_identity(project: Path) -> tuple[str, str]:
    package_version = _installed_koru_version()
    source_version = _read_project_version(project / "pyproject.toml")
    path_koru = shutil.which("koru")
    project_koru = project / ".venv" / "bin" / "koru"
    detail_bits = [
        f"python={sys.executable}",
        f"package={package_version or '-'}",
        f"source_pyproject={source_version or '-'}",
        f"path_koru={path_koru or '-'}",
    ]
    if project_koru.is_file():
        detail_bits.append(f"project_venv_koru={project_koru}")
    status, extra_bits = _koru_path_version_issues(
        project_koru, path_koru, package_version, source_version
    )
    detail_bits.extend(extra_bits)
    return status, "; ".join(detail_bits)


def _is_relative_to(path: Path, parent: Path) -> bool:
    # Use lexical containment rather than ``resolve()`` for the child:
    # virtualenv Python binaries are often symlinks to /usr/bin/python,
    # but the operator still launched the interpreter from project .venv.
    try:
        child = path.expanduser()
        if not child.is_absolute():
            child = Path.cwd() / child
        child.absolute().relative_to(parent.expanduser().resolve())
    except (OSError, ValueError):
        return False
    return True


def _check_python_venv_alignment(project: Path) -> tuple[str, str]:
    project_venv = project / ".venv"
    virtual_env = os.environ.get("VIRTUAL_ENV", "").strip()
    executable = Path(sys.executable)
    python_from_project_venv = _is_relative_to(executable, project_venv)
    detail_bits = [
        f"virtual_env={virtual_env or '-'}",
        f"python={sys.executable}",
        f"project_venv={project_venv}",
    ]
    if not project_venv.exists():
        return WARN, "; ".join(detail_bits + ["project_venv_missing=true"])

    status = PASS
    if virtual_env:
        try:
            if Path(virtual_env).expanduser().resolve() != project_venv.resolve():
                status = WARN
                detail_bits.append("virtual_env_mismatch=true")
        except OSError:
            status = WARN
            detail_bits.append("virtual_env_mismatch=unknown")
    else:
        detail_bits.append("virtual_env_unset=true")

    if not python_from_project_venv:
        status = WARN
        detail_bits.append("python_not_from_project_venv=true")

    path_koru = shutil.which("koru")
    if path_koru and not _is_relative_to(Path(path_koru), project_venv):
        status = WARN
        detail_bits.append("path_koru_not_from_project_venv=true")
    return status, "; ".join(detail_bits)