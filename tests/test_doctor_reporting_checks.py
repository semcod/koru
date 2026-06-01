import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from koru.doctor_constants import SKIP, WARN
from koru.doctor_reporting_checks import (
    _classify_ide_console_lines,
    check_ide_console_log,
)


class TestDoctorReportingChecks(unittest.TestCase):
    def test_check_ide_console_log_skips_without_selected_ide(self) -> None:
        status, detail = check_ide_console_log(selected_autopilot_ide=lambda: "")

        self.assertEqual(status, SKIP)
        self.assertIn("autopilot env unset", detail)

    def test_check_ide_console_log_warns_when_override_root_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "missing-logs"
            with patch.dict("os.environ", {"KORU_IDE_CONSOLE_LOG_DIR": str(missing)}):
                status, detail = check_ide_console_log(
                    selected_autopilot_ide=lambda: "windsurf"
                )

        self.assertEqual(status, WARN)
        self.assertIn("log root missing", detail)

    def test_classify_ide_console_lines_prefers_headlines(self) -> None:
        rows = [
            (Path("session/main.log"), "  at async sendPrompt (/tmp/path.js:1:2)"),
            (Path("session/main.log"), "[Warn] TrustedScript assignment denied"),
        ]

        interesting, headlines, sample_rows = _classify_ide_console_lines(rows)

        self.assertEqual(len(interesting), 1)
        self.assertEqual(len(headlines), 1)
        self.assertEqual(sample_rows, headlines)


if __name__ == "__main__":
    unittest.main()
