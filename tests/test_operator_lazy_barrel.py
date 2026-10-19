"""Tests for the lazy (PEP 562) barrel of koru.autonomy.operator."""

import importlib
import os
import subprocess
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"

_OPERATOR_SUBMODULES = (
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


def _run_python(code):
    env = dict(os.environ)
    pythonpath = env.get("PYTHONPATH", "")
    entries = [str(_SRC)] + ([pythonpath] if pythonpath else [])
    env["PYTHONPATH"] = os.pathsep.join(entries)
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def _public_names(module):
    names = getattr(module, "__all__", None)
    if names is None:
        names = [name for name in vars(module) if not name.startswith("_")]
    return list(names)


def test_import_koru_cli_does_not_load_other_operator_submodules():
    code = (
        "import sys\n"
        "import koru.cli\n"
        "for name in sorted(sys.modules):\n"
        "    if name.startswith('koru.autonomy.operator.'):\n"
        "        print(name)\n"
    )
    loaded = set(_run_python(code).split())
    forbidden = {
        "koru.autonomy.operator." + submodule
        for submodule in (
            "operator_diagnostics",
            "operator_wup",
            "operator_resources",
            "operator_loop_runner",
            "operator_daemon",
        )
    }
    assert forbidden.isdisjoint(loaded), sorted(forbidden & loaded)


def test_star_import_exports_union_of_submodule_public_names():
    expected = {}
    for submodule in _OPERATOR_SUBMODULES:
        module = importlib.import_module(f"koru.autonomy.operator.{submodule}")
        for name in _public_names(module):
            expected[name] = getattr(module, name)

    # Submodules are bound as package attributes on import; the eager barrel
    # exported them too, as well as transitively imported operator_* modules.
    package = importlib.import_module("koru.autonomy.operator")
    for name, value in vars(package).items():
        if name.startswith("operator_") and isinstance(value, type(package)):
            expected.setdefault(name, value)

    # The package itself never had ``__all__``, so underscore names listed in a
    # submodule's ``__all__`` were not re-exported by the package star-import.
    expected = {name: value for name, value in expected.items() if not name.startswith("_")}

    namespace = {}
    exec("from koru.autonomy.operator import *", namespace)
    namespace.pop("__builtins__", None)

    assert sorted(namespace) == sorted(expected)
    for name, value in expected.items():
        assert namespace[name] is value


def test_operator_runtime_name_reachable_as_package_attribute():
    package = importlib.import_module("koru.autonomy.operator")
    runtime = importlib.import_module("koru.autonomy.operator.operator_runtime")
    assert hasattr(runtime, "resolve_cli_project")
    assert hasattr(package, "resolve_cli_project")
    assert package.resolve_cli_project is runtime.resolve_cli_project


def test_shim_submodule_import_stays_lazy_and_star_export_stays_complete():
    # koru.autonomous_* shims do ``from koru.autonomy.operator import operator_x``;
    # that must not replay the whole barrel mid-import and freeze a partial __all__.
    code = (
        "import sys, json\n"
        "import koru.autonomous_diag_markers\n"
        "lazy = 'koru.autonomy.operator.operator_wup' not in sys.modules\n"
        "ns = {}\n"
        "exec('from koru.autonomy.operator import *', ns)\n"
        "print(json.dumps({'lazy': lazy, 'has_runtime': 'resolve_cli_project' in ns,\n"
        "                  'has_submodule': 'operator_operator' in ns}))\n"
    )
    import json

    result = json.loads(_run_python(code))
    assert result == {"lazy": True, "has_runtime": True, "has_submodule": True}
