from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from koru.events import emit_management_event


class FakeResponse:
    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class TestManagementEvents(unittest.TestCase):
    def test_emit_management_event_posts_expected_payload(self) -> None:
        captured: dict[str, object] = {}

        def fake_urlopen(request, timeout: float):  # noqa: ANN001
            captured["url"] = request.full_url
            captured["method"] = request.get_method()
            captured["timeout"] = timeout
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        with patch("urllib.request.urlopen", fake_urlopen):
            ok = emit_management_event(
                events_url="http://planfile.local/events/ingest",
                tool="koru.queue",
                action="completed",
                status="dry_run",
                queue="c2004-runtime",
                message="PLF-073",
                details={"ticket_id": "PLF-073"},
            )

        self.assertTrue(ok)
        self.assertEqual(captured["url"], "http://planfile.local/events/ingest")
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["timeout"], 2.0)
        self.assertEqual(
            captured["payload"],
            {
                "source": "koru",
                "tool": "koru.queue",
                "action": "completed",
                "status": "dry_run",
                "message": "PLF-073",
                "queue": "c2004-runtime",
                "level": "info",
                "details": {"ticket_id": "PLF-073"},
            },
        )

    def test_emit_management_event_is_disabled_without_url(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(
                emit_management_event(tool="koru.queue", action="completed"),
            )


if __name__ == "__main__":
    unittest.main()
