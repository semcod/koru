"""Compatibility exports for ``koru.cli``.

The repository currently contains both:
- ``src/koru/cli.py`` (legacy CLI implementation used by tests/entrypoints), and
- ``src/koru/cli/`` (new package layout scaffolding).

Because package imports take precedence, ``import koru.cli`` resolves to this
package and would otherwise hide the legacy module symbols. We bridge to the
legacy implementation here until the package migration is completed.
"""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from types import ModuleType


def _load_legacy_cli_module() -> ModuleType:
    module_name = "koru._legacy_cli_impl"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing

    module_path = Path(__file__).resolve().parents[1] / "cli.py"
    spec = spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load legacy CLI module from {module_path}")

    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_legacy = _load_legacy_cli_module()

main = _legacy.main
_SUBCOMMANDS = _legacy._SUBCOMMANDS
_build_parser = _legacy._build_parser
_is_bare_invocation = _legacy._is_bare_invocation
_command_value = _legacy._command_value

__all__ = [
    "main",
    "_SUBCOMMANDS",
    "_build_parser",
    "_is_bare_invocation",
    "_command_value",
]


def __getattr__(name: str):
    return getattr(_legacy, name)
