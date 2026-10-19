"""inputs.strict_files refuses promotion of patches outside ticket.files (semcod/koru#726)."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from koru.queue.transaction.preflight import (
    PATCH_TARGETS_OUTSIDE_DECLARED_FILES,
    screen_promotion_preconditions,
    undeclared_targets,
)


def _plan(ticket: dict, targets: tuple[str, ...]):
    return SimpleNamespace(
        project=Path("/nonexistent"), ticket=ticket, targets=targets, mode="branch"
    )


def test_strict_files_refuses_undeclared_target() -> None:
    plan = _plan(
        {"files": ["test/a.mjs"], "inputs": {"strict_files": True}},
        ("test/a.mjs", "tests/a.mjs"),
    )
    assert undeclared_targets(plan) == ("tests/a.mjs",)
    refusal = screen_promotion_preconditions(plan)
    assert refusal is not None
    assert refusal.code == PATCH_TARGETS_OUTSIDE_DECLARED_FILES
    assert "tests/a.mjs" in refusal.message


def test_strict_files_accepts_declared_targets_and_dot_prefix() -> None:
    plan = _plan({"files": ["./src/x.py"], "inputs": {"strict_files": True}}, ("src/x.py",))
    assert undeclared_targets(plan) == ()
    assert screen_promotion_preconditions(plan) is None


def test_without_opt_in_extra_targets_are_not_refused() -> None:
    plan = _plan({"files": ["src/x.py"], "inputs": {}}, ("src/x.py", "src/y.py"))
    assert undeclared_targets(plan) == ()
    assert screen_promotion_preconditions(plan) is None
