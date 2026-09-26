"""Unit and contract tests for koru.scan_artifacts."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from koru import scan as scan_module
from koru import scan_artifacts
from koru.scan_artifacts import (
    _ANALYSIS_ARTIFACT_PATHS,
    _CALLS_ARTIFACT_PATHS,
    _PLANFILE_TICKETS_ARTIFACT_PATHS,
    _find_analysis_file,
    _first_existing_artifact,
    _load_yaml_mapping,
    _scan_jscpd_report,
    _scan_testql_export,
    _scan_vallm_validation,
    scan_semcod_quality_artifacts,
)


class TestScanArtifacts(unittest.TestCase):
    def test_reexports_in_scan_module(self) -> None:
        """Verify backward compatibility re-exports from scan.py."""
        self.assertIs(scan_module.scan_semcod_quality_artifacts, scan_artifacts.scan_semcod_quality_artifacts)
        self.assertIs(scan_module._find_analysis_file, scan_artifacts._find_analysis_file)
        self.assertIs(scan_module._load_yaml_mapping, scan_artifacts._load_yaml_mapping)
        self.assertEqual(scan_module._ANALYSIS_ARTIFACT_PATHS, _ANALYSIS_ARTIFACT_PATHS)
        self.assertEqual(scan_module._PLANFILE_TICKETS_ARTIFACT_PATHS, _PLANFILE_TICKETS_ARTIFACT_PATHS)
        self.assertEqual(scan_module._CALLS_ARTIFACT_PATHS, _CALLS_ARTIFACT_PATHS)

    def test_first_existing_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "b.txt").write_text("hello", encoding="utf-8")
            found = _first_existing_artifact(p, ("a.txt", "b.txt", "c.txt"))
            self.assertIsNotNone(found)
            assert found is not None
            self.assertEqual(found[0], p / "b.txt")
            self.assertEqual(found[1], "b.txt")

            none_found = _first_existing_artifact(p, ("x.txt", "y.txt"))
            self.assertIsNone(none_found)

    def test_find_analysis_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "project").mkdir()
            nested = p / "project" / "analysis.toon"
            nested.write_text("HEALTH\n", encoding="utf-8")
            (p / "analysis.toon.yaml").write_text("HEALTH\n", encoding="utf-8")
            self.assertEqual(_find_analysis_file(p), (nested, "project/analysis.toon"))

    def test_load_yaml_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "project").mkdir()
            (p / "project" / "planfile-tickets.yaml").write_text("tickets:\n  - id: 1\n", encoding="utf-8")
            loaded = _load_yaml_mapping(p, _PLANFILE_TICKETS_ARTIFACT_PATHS)
            self.assertEqual(loaded, {"tickets": [{"id": 1}]})

    def test_scan_jscpd_report_empty_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(_scan_jscpd_report(Path(tmp)), [])

    def test_scan_jscpd_report_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            jscpd_dir = p / ".jscpd"
            jscpd_dir.mkdir()
            (jscpd_dir / "jscpd-report.json").write_text(
                json.dumps(
                    {
                        "statistics": {
                            "total": {
                                "duplicatedLines": 500,
                                "percentage": 16.5,
                                "clones": 12,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            suggestions = _scan_jscpd_report(p)
            self.assertEqual(len(suggestions), 1)
            self.assertEqual(suggestions[0].signal, "jscpd_report")
            self.assertEqual(suggestions[0].priority, "high")

    def test_scan_testql_export_empty_when_few_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "testql_api_results.json").write_text("❌ api.yaml\n", encoding="utf-8")
            self.assertEqual(_scan_testql_export(p), [])

    def test_scan_vallm_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "validation.toon.yaml").write_text("ERRORS[2]\nWARNINGS[15]\n", encoding="utf-8")
            suggestions = _scan_vallm_validation(p)
            self.assertEqual(len(suggestions), 1)
            self.assertEqual(suggestions[0].signal, "vallm_validation")
            self.assertEqual(suggestions[0].priority, "high")

    def test_scan_semcod_quality_artifacts_aggregated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "validation.toon.yaml").write_text("ERRORS[1]\nWARNINGS[0]\n", encoding="utf-8")
            all_suggs = scan_semcod_quality_artifacts(p)
            self.assertTrue(any(s.signal == "vallm_validation" for s in all_suggs))


if __name__ == "__main__":
    unittest.main()
