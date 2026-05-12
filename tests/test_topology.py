from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from koru.topology import (
    enabled_components_for_pipeline,
    load_topology,
    save_topology,
    set_component_enabled,
    set_pipeline_enabled,
)


class TestTopology(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_load_defaults_without_file(self) -> None:
        topo = load_topology(self.project)
        self.assertFalse(topo["exists"])
        self.assertIn("regix", topo["components"])
        self.assertIn("idle-diagnostics", topo["pipelines"])

    def test_toggle_and_persist(self) -> None:
        topo = load_topology(self.project)
        r1 = set_component_enabled(topo, "redsl", True)
        r2 = set_pipeline_enabled(topo, "gate:wup", False)
        self.assertTrue(r1.found)
        self.assertTrue(r2.found)
        save_topology(self.project, topo)

        topo2 = load_topology(self.project)
        self.assertTrue(topo2["exists"])
        self.assertTrue(topo2["components"]["redsl"]["enabled"])
        self.assertFalse(topo2["pipelines"]["gate:wup"]["enabled"])

    def test_enabled_components_for_pipeline_respects_component_flags(self) -> None:
        topo = load_topology(self.project)
        set_component_enabled(topo, "wup", False)
        save_topology(self.project, topo)

        enabled = enabled_components_for_pipeline(self.project, "idle-diagnostics")
        self.assertIn("regix", enabled)
        self.assertNotIn("wup", enabled)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
