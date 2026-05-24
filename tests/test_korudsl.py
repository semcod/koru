"""Tests for korudsl package."""

from __future__ import annotations

import pytest

from korudsl import (
    dsl_roundtrip_report,
    library_to_dsl,
    normalize_dsl_to_library,
)
from korudsl.cli import main as koru_dsl_main


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


def test_koru_dsl_version_exits_zero(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        koru_dsl_main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.startswith("koru-dsl ")
