"""Tests for CDP Browser Controller."""

from koru.autonomy.cdp_browser import CdpBrowserController
from koru.autonomy.process_uri import ProcessUri


def test_cdp_browser_navigate():
    controller = CdpBrowserController()
    uri = ProcessUri.parse("browser://navigate?url=https://example.com")
    resp = controller.execute_uri(uri, dry_run=True)

    assert resp.success is True
    assert resp.action == "navigate"
    frame = resp.data["cdp_frame"]
    assert frame["method"] == "Page.navigate"
    assert frame["params"]["url"] == "https://example.com"
    assert frame["id"] == 1


def test_cdp_browser_click():
    controller = CdpBrowserController()
    uri = ProcessUri.parse("browser://click")
    resp = controller.execute_uri(uri, payload={"selector": "#submit-btn"}, dry_run=True)

    assert resp.success is True
    assert resp.action == "click"
    frame = resp.data["cdp_frame"]
    assert frame["method"] == "Runtime.evaluate"
    assert "document.querySelector('#submit-btn').click()" in frame["params"]["expression"]


def test_cdp_browser_screenshot():
    controller = CdpBrowserController()
    uri = ProcessUri.parse("browser://screenshot?output=report.png")
    resp = controller.execute_uri(uri, dry_run=True)

    assert resp.success is True
    assert resp.action == "screenshot"
    assert resp.data["output_path"] == "report.png"
    frame = resp.data["cdp_frame"]
    assert frame["method"] == "Page.captureScreenshot"


def test_cdp_browser_evaluate():
    controller = CdpBrowserController()
    uri = ProcessUri.parse("browser://evaluate")
    resp = controller.execute_uri(uri, payload={"expression": "1 + 1"}, dry_run=True)

    assert resp.success is True
    assert resp.action == "evaluate"
    frame = resp.data["cdp_frame"]
    assert frame["method"] == "Runtime.evaluate"
    assert frame["params"]["expression"] == "1 + 1"
    assert frame["params"]["returnByValue"] is True


def test_cdp_browser_invalid_scheme():
    controller = CdpBrowserController()
    uri = ProcessUri.parse("sandbox://run?image=alpine")
    resp = controller.execute_uri(uri)

    assert resp.success is False
    assert "Expected 'browser' scheme" in resp.error


def test_cdp_browser_missing_params():
    controller = CdpBrowserController()
    uri = ProcessUri.parse("browser://navigate")
    resp = controller.execute_uri(uri)

    assert resp.success is False
    assert "Missing required 'url' parameter" in resp.error
