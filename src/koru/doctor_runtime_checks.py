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


_AUTO_PROBE_CACHE: dict[str, bool | None] = {}


def _path_koru_supports_auto_subcommand(path_koru: str | None) -> bool | None:
    """Probe whether ``koru auto`` works on the executable first on PATH."""
    if not path_koru:
        return None
    try:
        proc = subprocess.run(
            [path_koru, "auto", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
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


def _path_koru_is_current_venv(path_koru: str) -> bool:
    """True when ``path_koru`` lives inside the running interpreter's venv.

    In that case it is the very code we are already executing, so it
    inevitably supports ``koru auto`` — no need to spawn a subprocess.
    """
    try:
        return _is_relative_to(Path(path_koru), Path(sys.prefix))
    except (OSError, ValueError):
        return False


def _probe_auto_subcommand_cached(path_koru: str | None) -> bool | None:
    """Cache the ``koru auto`` probe per resolved path within this process."""
    if not path_koru:
        return None
    try:
        key = str(Path(path_koru).resolve())
    except OSError:
        key = path_koru
    if key not in _AUTO_PROBE_CACHE:
        _AUTO_PROBE_CACHE[key] = _path_koru_supports_auto_subcommand(path_koru)
    return _AUTO_PROBE_CACHE[key]


def _resolve_auto_support(path_koru: str | None) -> bool | None:
    """Whether the PATH koru supports ``koru auto`` (skip probe for own venv).

    The venv we are running self-evidently supports ``auto``; only a
    *different* (potentially stale) koru on PATH needs the subprocess probe.
    """
    if path_koru and _path_koru_is_current_venv(path_koru):
        return True
    return _probe_auto_subcommand_cached(path_koru)


def _koru_path_version_issues(
    project_koru: Path,
    path_koru: str | None,
    package_version: str | None,
    source_version: str | None,
) -> tuple[str, list[str]]:
    """Return (status, extra_bits) for path-mismatch and version checks."""
    status = PASS
    detail_bits: list[str] = []
    if project_koru.is_file() and path_koru:
        try:
            if Path(path_koru).resolve() != project_koru.resolve():
                status = WARN
                detail_bits.append("path_mismatch=true")
        except OSError:
            status = WARN
            detail_bits.append("path_mismatch=unknown")
    if _resolve_auto_support(path_koru) is False:
        status = WARN
        detail_bits.append("koru_auto_unsupported=true")
        if project_koru.is_file():
            detail_bits.append(
                f"fix=export PATH={project_koru.parent}:$PATH; hash -r; or {project_koru} auto"
            )
        else:
            detail_bits.append("fix=pip install -e . && use koru autonomous")
    if package_version and source_version and package_version != source_version:
        status = WARN
        detail_bits.append("version_mismatch=true")
    if package_version is None:
        status = WARN
        detail_bits.append("package_metadata=missing")
    return status, detail_bits


def _check_koru_runtime_identity(project: Path) -> tuple[str, str]:
    package_version = _installed_koru_version()
    source_version = _read_project_version(project / "pyproject.toml")
    path_koru = shutil.which("koru")
    project_koru: Path | None = None
    for venv_name in (".venv", "venv"):
        candidate = project / venv_name / "bin" / "koru"
        if candidate.is_file():
            project_koru = candidate
            break
    detail_bits = [
        f"python={sys.executable}",
        f"package={package_version or '-'}",
        f"source_pyproject={source_version or '-'}",
        f"path_koru={path_koru or '-'}",
    ]
    if project_koru is not None and project_koru.is_file():
        detail_bits.append(f"project_venv_koru={project_koru}")
    status, extra_bits = _koru_path_version_issues(
        project_koru or project / ".venv" / "bin" / "koru",
        path_koru,
        package_version,
        source_version,
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
    project_venvs = [project / ".venv", project / "venv"]
    existing_venvs = [venv for venv in project_venvs if venv.exists()]
    virtual_env = os.environ.get("VIRTUAL_ENV", "").strip()
    executable = Path(sys.executable)
    python_from_project_venv = any(_is_relative_to(executable, venv) for venv in existing_venvs)
    detail_bits = [
        f"virtual_env={virtual_env or '-'}",
        f"python={sys.executable}",
        f"project_venv={existing_venvs[0] if existing_venvs else project / '.venv'}",
    ]
    if not existing_venvs:
        return WARN, "; ".join(detail_bits + ["project_venv_missing=true"])

    status = PASS
    if virtual_env:
        try:
            virtual_env_path = Path(virtual_env).expanduser().resolve()
            if not any(virtual_env_path == venv.resolve() for venv in existing_venvs):
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
    if path_koru and not any(_is_relative_to(Path(path_koru), venv) for venv in existing_venvs):
        status = WARN
        detail_bits.append("path_koru_not_from_project_venv=true")
    return status, "; ".join(detail_bits)