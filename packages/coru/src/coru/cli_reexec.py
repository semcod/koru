"""Project-venv re-exec helpers extracted from ``coru.cli``.

Keeps the large CLI module thinner while preserving the same behaviour when
``coru`` is launched outside a monorepo ``.venv``.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from pathlib import Path


def repo_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".git").exists() and (parent / "pyproject.toml").exists():
            return parent
    return None


def cwd_repo_root() -> Path | None:
    for parent in (Path.cwd(), *Path.cwd().parents):
        if (parent / ".git").exists() and (parent / "pyproject.toml").exists():
            return parent
    return None


def project_repo_root() -> Path | None:
    return cwd_repo_root() or repo_root()


def project_venv_candidates(root: Path) -> list[str]:
    candidates: list[str] = []
    for venv_name in (".venv", "venv"):
        for python_name in ("python", "python3"):
            candidate = root / venv_name / "bin" / python_name
            if candidate.exists():
                candidates.append(str(candidate))
                break
    return candidates


def venv_has_installed_module(venv_python: str, package: str) -> bool:
    try:
        venv_bin = Path(venv_python).absolute().parent
        if venv_bin.name != "bin":
            return False
        venv_root = venv_bin.parent
    except Exception:
        return False
    for lib_dir in venv_root.glob("lib/python*"):
        site_packages = lib_dir / "site-packages"
        if (site_packages / package / "__init__.py").exists():
            return True
        if any(site_packages.glob(f"__editable__.{package}*.pth")):
            return True
    return (venv_bin / package).exists()


def project_venv_python() -> str | None:
    root = project_repo_root()
    if root is None:
        return None
    candidates = project_venv_candidates(root)
    if not candidates:
        return None
    for python in candidates:
        if venv_has_installed_module(python, "coru"):
            return python
    return candidates[0]


def local_module_source_dir(module_name: str) -> Path | None:
    root = repo_root()
    if root is None:
        return None
    package = module_name.split(".", 1)[0]
    if package == "koru":
        source = root / "src"
    else:
        source = root / "packages" / package / "src"
    module_path = source / package
    if (module_path / "__init__.py").exists():
        return source
    return None


def installed_module_source_dir(module_name: str) -> Path | None:
    package = module_name.split(".", 1)[0]
    module = sys.modules.get(package)
    origin: Path | None = None
    if module is not None and getattr(module, "__file__", None):
        origin = Path(module.__file__).resolve()
    else:
        import importlib.util

        try:
            spec = importlib.util.find_spec(package)
        except Exception:
            return None
        if spec is None or spec.origin is None:
            return None
        origin = Path(spec.origin).resolve()
    if origin.name == "__init__.py":
        return origin.parent.parent
    return origin.parent


def module_runtime_source_dir(module_name: str) -> Path | None:
    return local_module_source_dir(module_name) or installed_module_source_dir(module_name)


def reexec_already_done() -> bool:
    return (
        os.environ.get("CORU_DISABLE_AUTO_REEXEC") == "1"
        or os.environ.get("CORU_REEXEC_DONE") == "1"
        or bool(os.environ.get("PYTEST_CURRENT_TEST"))
    )


def already_running_in_project_venv(project_python: str) -> bool:
    try:
        current_python = Path(sys.executable)
        target_python = Path(project_python)
        target_venv = target_python.parent.parent.resolve()
    except Exception:
        return True
    try:
        if (
            current_python.resolve() == target_python.resolve()
            and Path(sys.prefix).resolve() == target_venv
        ):
            return True
    except Exception:
        if str(current_python) == str(target_python):
            return True
    return str(current_python) == str(target_python)


def reexec_env_and_cmd(
    project_python: str, argv: Sequence[str]
) -> tuple[dict[str, str], list[str]] | None:
    target_python = Path(project_python)
    target_venv = target_python.parent.parent.resolve()
    source_dir = module_runtime_source_dir("coru.cli")
    env = dict(os.environ)
    env["CORU_REEXEC_DONE"] = "1"
    target_bin = target_venv / "bin"
    old_path = env.get("PATH", "")
    path_parts = [part for part in old_path.split(os.pathsep) if part and part != str(target_bin)]
    env["VIRTUAL_ENV"] = str(target_venv)
    env["PATH"] = os.pathsep.join([str(target_bin), *path_parts])

    if source_dir is not None:
        runner = (
            "import sys; "
            f"sys.path.insert(0, {str(source_dir)!r}); "
            "from coru.cli import main; "
            "raise SystemExit(main(sys.argv[1:]))"
        )
        cmd = [str(target_python), "-c", runner, *list(argv)]
    elif venv_has_installed_module(str(target_python), "coru"):
        cmd = [str(target_python), "-m", "coru.cli", *list(argv)]
    else:
        return None
    return env, cmd


def maybe_reexec_into_project_python(argv: Sequence[str]) -> bool:
    """Re-exec coru under repo-local .venv to avoid mixed runtime environments."""
    if reexec_already_done():
        return False
    project_python = project_venv_python()
    if not project_python or already_running_in_project_venv(project_python):
        return False
    built = reexec_env_and_cmd(project_python, argv)
    if built is None:
        return False
    env, cmd = built
    target_python = Path(project_python)
    print(
        f"[coru] re-exec into project venv: {target_python}",
        file=sys.stderr,
    )
    os.execve(str(target_python), cmd, env)
    return True


# Historical private names used by coru.cli.
_repo_root = repo_root
_cwd_repo_root = cwd_repo_root
_project_repo_root = project_repo_root
_project_venv_candidates = project_venv_candidates
_venv_has_installed_module = venv_has_installed_module
_project_venv_python = project_venv_python
_local_module_source_dir = local_module_source_dir
_installed_module_source_dir = installed_module_source_dir
_module_runtime_source_dir = module_runtime_source_dir
_reexec_already_done = reexec_already_done
_already_running_in_project_venv = already_running_in_project_venv
_reexec_env_and_cmd = reexec_env_and_cmd
_maybe_reexec_into_project_python = maybe_reexec_into_project_python

__all__ = [
    "already_running_in_project_venv",
    "cwd_repo_root",
    "installed_module_source_dir",
    "local_module_source_dir",
    "maybe_reexec_into_project_python",
    "module_runtime_source_dir",
    "project_repo_root",
    "project_venv_candidates",
    "project_venv_python",
    "reexec_already_done",
    "reexec_env_and_cmd",
    "repo_root",
    "venv_has_installed_module",
]
