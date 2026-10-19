"""Autonomous operator management for process control and plugin lifecycle."""

# Lazy barrel (PEP 562): importing this package imports none of its
# submodules.  Public names are materialized into package globals on first
# attribute access, star-import, or ``dir()``, reproducing the historical
# eager star-imports (later submodules win name conflicts, as before).

from importlib import import_module as _import_module
from importlib.util import find_spec as _find_spec

_SUBMODULES = (
    "operator_daemon",
    "operator_diag_markers",
    "operator_diagnostics",
    "operator_loop_narration",
    "operator_loop_runner",
    "operator_onboarding",
    "operator_operator",
    "operator_parser",
    "operator_plugin",
    "operator_plugin_lifecycle",
    "operator_plugin_runtime",
    "operator_plugin_wait",
    "operator_process_guard",
    "operator_processes",
    "operator_resources",
    "operator_runtime",
    "operator_up",
    "operator_vdisplay_defaults",
    "operator_wup",
)


_loading = False


def _load_all():
    """Replay the historical star-imports once, into package globals."""
    global _loading
    if "__all__" in globals() or _loading:
        # Re-entry happens when a submodule imports from this package while
        # it is being loaded; like the eager barrel, it only sees names bound so far.
        return
    _loading = True
    try:
        _replay_star_imports()
    finally:
        _loading = False


def _replay_star_imports():
    for submodule_name in _SUBMODULES:
        module = _import_module(f"{__name__}.{submodule_name}")
        names = getattr(module, "__all__", None)
        if names is None:
            names = [name for name in vars(module) if not name.startswith("_")]
        for name in names:
            globals()[name] = getattr(module, name)
    # The eager package had no ``__all__``: its star-import exported every public
    # global, including the submodules bound as package attributes on import.
    globals()["__all__"] = sorted(name for name in globals() if not name.startswith("_"))


def __getattr__(name):
    if name.startswith("__") and name != "__all__":
        raise AttributeError(name)
    # ``from koru.autonomy.operator import operator_x`` (used by the
    # koru.autonomous_* shims) must load only that submodule, not the barrel.
    if name.startswith("operator_") and _find_spec(f"{__name__}.{name}") is not None:
        return _import_module(f"{__name__}.{name}")
    _load_all()
    try:
        return globals()[name]
    except KeyError:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        ) from None


def __dir__():
    _load_all()
    return sorted(globals())
