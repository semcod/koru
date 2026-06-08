"""Compatibility exports for ``koru.cli``.

The repository currently contains both:
- ``src/koru/cli.py`` (legacy CLI implementation used by tests/entrypoints), and
- ``src/koru/cli/`` (new package layout scaffolding).

Because package imports take precedence, ``import koru.cli`` resolves to this
package and would otherwise hide the legacy module symbols. We bridge to the
legacy implementation here until the package migration is completed.
"""

from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

_LEGACY_REQUIRED_EXPORTS = (
    "main",
    "_SUBCOMMANDS",
    "_build_parser",
    "_is_bare_invocation",
    "_command_value",
    "_peek_project_from_argv",
    "_should_suggest_wizard",
)


def _has_legacy_exports(module: ModuleType) -> bool:
    return all(hasattr(module, name) for name in _LEGACY_REQUIRED_EXPORTS)


def _load_legacy_cli_module() -> ModuleType:
    module_name = "koru._legacy_cli_impl"
    existing = sys.modules.get(module_name)
    if existing is not None and _has_legacy_exports(existing):
        return existing
    if existing is not None:
        sys.modules.pop(module_name, None)

    module_path = Path(__file__).resolve().parents[1] / "cli.py"
    spec = spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load legacy CLI module from {module_path}")

    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    missing = [name for name in _LEGACY_REQUIRED_EXPORTS if not hasattr(module, name)]
    if missing:
        sys.modules.pop(module_name, None)
        missing_names = ", ".join(missing)
        raise ImportError(f"Legacy CLI module from {module_path} is missing: {missing_names}")
    return module


_legacy = _load_legacy_cli_module()

from koru.cli_agent_backends import agent_backends_main as _agent_backends_main  # noqa: E402
from koru.cli_auto import _auto_main  # noqa: E402
from koru.cli_ide_router import ide_router_main  # noqa: E402

_tillm_main = getattr(_legacy, "_tillm_main", None)

if not hasattr(_legacy, "_auto_main"):
    _legacy._auto_main = _auto_main
if not hasattr(_legacy, "_agent_backends_main"):
    _legacy._agent_backends_main = _agent_backends_main
if not hasattr(_legacy, "ide_router_main"):
    _legacy.ide_router_main = ide_router_main

main = _legacy.main
_SUBCOMMANDS = _legacy._SUBCOMMANDS
_build_parser = _legacy._build_parser
_is_bare_invocation = _legacy._is_bare_invocation
_command_value = _legacy._command_value
_peek_project_from_argv = _legacy._peek_project_from_argv
_should_suggest_wizard = _legacy._should_suggest_wizard

__all__ = [
    "main",
    "_SUBCOMMANDS",
    "_build_parser",
    "_is_bare_invocation",
    "_command_value",
    "_auto_main",
    "_agent_backends_main",
    "_tillm_main",
    "_peek_project_from_argv",
    "_should_suggest_wizard",
    "ide_router_main",
]


def __getattr__(name: str):
    return getattr(_legacy, name)
