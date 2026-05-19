"""Tests for topology CLI rendering."""

from koru.topology_cli import render_topology_text


def test_render_topology_text_includes_components_and_pipelines():
    text = render_topology_text(
        {
            "project": "/tmp/p",
            "exists": True,
            "path": "/tmp/p/.planfile/topology.yaml",
            "components": {
                "scan": {"enabled": True, "available": True, "via": "default", "role": "r"}
            },
            "pipelines": {
                "autoloop:queue": {
                    "enabled": False,
                    "trigger": "idle",
                    "description": "queue",
                    "components": ["scan"],
                },
            },
        },
    )
    assert "koru topology: /tmp/p" in text
    assert "scan" in text
    assert "autoloop:queue" in text
