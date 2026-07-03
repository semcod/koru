"""Contract: every late-bound facade attribute must exist on its facade.

koru's extraction convention routes cross-module calls to test-patched names
through a facade at call time (``from koru import autonomous_cycle as
_cycle_mod; _cycle_mod.name(...)``). Three times on 2026-07-03 an extraction
slimmed a facade and silently broke those references at *runtime*
(AttributeError mid-cycle; the quality gate was wedged red for hours).

This test statically collects every ``from koru[...] import X as <alias>`` /
``<alias>.attr`` pair across ``src/`` and asserts the facade actually
exposes each attribute (lazy ``__getattr__`` exports count — ``hasattr``
triggers them). It turns the incident class into a red test at author time.

Tracked as STARTER-564 (part 3 — auditing that *call sites* of test-patched
names go through the facade — is follow-up work).
"""

from __future__ import annotations

import importlib
import re
from collections import defaultdict
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"

# `from koru import autonomous_cycle as _cycle_mod` (also dotted sources like
# `from koru.autonomy import x as _y_mod`); we only track underscore aliases —
# that is the repo's late-binding convention.
_ALIAS_IMPORT_RE = re.compile(
    r"^\s*from\s+(koru(?:\.\w+)*)\s+import\s+(\w+)\s+as\s+(_\w+(?:_mod|_facade))\s*$",
    re.MULTILINE,
)

# Attribute uses of a tracked alias: `_cycle_mod.verify_completed_tickets`
_ATTR_USE_TEMPLATE = r"\b{alias}\.(\w+)"

# Dunder/internal attributes that are not part of the facade contract.
_IGNORED_ATTRS = {"__name__", "__dict__", "__file__"}


def collect_late_bound_pairs() -> dict[str, set[str]]:
    """Return {facade_module_path: {attr, ...}} for every alias use in src/."""
    pairs: dict[str, set[str]] = defaultdict(set)
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        aliases: dict[str, str] = {}
        for match in _ALIAS_IMPORT_RE.finditer(text):
            package, module, alias = match.groups()
            aliases[alias] = f"{package}.{module}"
        for alias, module_path in aliases.items():
            for use in re.finditer(_ATTR_USE_TEMPLATE.format(alias=re.escape(alias)), text):
                attr = use.group(1)
                if attr not in _IGNORED_ATTRS:
                    pairs[module_path].add(attr)
    return dict(pairs)


def test_collector_finds_known_late_bindings() -> None:
    """Self-check: regex rot must not silently collect nothing."""
    pairs = collect_late_bound_pairs()
    flat = {(mod, attr) for mod, attrs in pairs.items() for attr in attrs}

    # Sentinels from three real incidents (coru/cli-class, readiness, cycle-slim):
    assert ("koru.autonomous_cycle", "verify_completed_tickets") in flat
    assert ("koru.autonomous_readiness", "daemon_status_compatible") in flat
    assert any(mod == "koru.autonomous_loop_runner" for mod, _ in flat)
    assert len(flat) >= 25, f"suspiciously few late-bound pairs collected: {len(flat)}"


def test_every_late_bound_attribute_exists_on_its_facade() -> None:
    pairs = collect_late_bound_pairs()
    missing: list[str] = []
    for module_path, attrs in sorted(pairs.items()):
        try:
            module = importlib.import_module(module_path)
        except Exception as exc:  # facade must at least import
            missing.append(f"{module_path}: import failed: {exc!r}")
            continue
        for attr in sorted(attrs):
            if not hasattr(module, attr):
                missing.append(f"{module_path}.{attr}")
    assert not missing, (
        "late-bound facade attributes are missing — an extraction dropped "
        "re-exports the cycle/loop modules resolve at call time "
        "(see koru-facade-late-binding convention):\n  " + "\n  ".join(missing)
    )


@pytest.mark.parametrize(
    "facade",
    [
        "koru.autonomous_cycle",
        "koru.autonomous_loop_runner",
        "koru.autonomous_readiness",
    ],
)
def test_known_facades_importable(facade: str) -> None:
    importlib.import_module(facade)
