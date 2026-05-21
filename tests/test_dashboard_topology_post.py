"""Tests for dashboard topology POST helper."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

from koruapi.topology_post import apply_topology_post_update


def test_apply_topology_post_update_rejects_non_object_components() -> None:
    _, err, status = apply_topology_post_update(Path("."), {"components": "bad"})
    assert status == 400
    assert err is not None
    assert "must be objects" in err["error"]


def test_apply_topology_post_update_applies_component_toggle(tmp_path: Path) -> None:
    topo = {"components": {"scan": {"enabled": True}}, "pipelines": {}}
    with (
        mock.patch("koruapi.topology_post.load_topology", return_value=topo),
        mock.patch("koruapi.topology_post.save_topology", return_value=tmp_path / "t.yaml"),
        mock.patch(
            "koruapi.topology_post.set_component_enabled",
            return_value=mock.Mock(found=True, id="scan", current=False),
        ),
    ):
        merged, err, status = apply_topology_post_update(
            tmp_path,
            {"components": {"scan": False}, "pipelines": {}},
        )
    assert status == 200
    assert err is None
    assert merged is not None
    assert merged["saved"][0]["id"] == "scan"
