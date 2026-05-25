from __future__ import annotations

from types import SimpleNamespace

from koru.autonomous_cycle_bridge import run_cycle_with_compat


def test_run_cycle_with_compat_forwards_dependencies_before_running_cycle() -> None:
    seen = {}

    def run_cycle(**kwargs):
        seen["dep"] = module.dep
        seen["kwargs"] = kwargs
        return "ok"

    module = SimpleNamespace(run_cycle=run_cycle)

    result = run_cycle_with_compat(
        {"cycle": 7},
        cycle_module=module,
        dependencies={"dep": "patched"},
    )

    assert result == "ok"
    assert seen == {"dep": "patched", "kwargs": {"cycle": 7}}
