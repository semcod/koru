"""Tests for korudsl package."""

from __future__ import annotations

from korudsl import (
    dsl_roundtrip_report,
    library_to_dsl,
    normalize_dsl_to_library,
)


def test_normalize_and_roundtrip() -> None:
    dsl = """
    GOAL: boot
    SET x=1
    WAIT 5s
    ERROR "fail"
    """
    lib = normalize_dsl_to_library(dsl)
    assert lib["goals"][0]["name"] == "boot"
    back = library_to_dsl(lib)
    assert "GOAL: boot" in back
    report = dsl_roundtrip_report(dsl)
    assert report["ok"] is True


def test_library_to_dsl_objectives() -> None:
    lib = normalize_dsl_to_library('GOAL: g\nCORRECT "ok"\n')
    text = library_to_dsl(lib)
    assert 'CORRECT "ok"' in text
