"""Regression tests for diagnostic marker path sanitization."""

from pathlib import Path

from koru.autonomous_diag_markers import diagnostic_marker_path


def test_diagnostic_marker_path_flattens_slashes(tmp_path: Path) -> None:
    marker = diagnostic_marker_path(tmp_path, "wup-src/koru")
    assert marker == tmp_path / "wup-src_koru.failed"
    assert marker.parent == tmp_path


def test_diagnostic_marker_path_preserves_simple_ids(tmp_path: Path) -> None:
    assert diagnostic_marker_path(tmp_path, "wup-api") == tmp_path / "wup-api.failed"
