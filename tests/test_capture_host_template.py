from __future__ import annotations

from korumesh.browser_capture import _render_capture_host, capture_host_html


def test_capture_host_template_detects_cursor_webview() -> None:
    capture_host_html.cache_clear()
    html = capture_host_html()
    assert "Cursor" in html, "needs to flag Cursor IDE webview UA"
    assert "data-cursor-element-id" in html, "needs the attribute fallback"
    assert "NotSupportedError" in html, "needs friendly explainer for NotSupportedError"
    assert 'id="copy-url"' in html, "needs Copy URL button"


def test_render_capture_host_substitutes_interval_and_peer() -> None:
    rendered = _render_capture_host("/capture/host?peer=alpha").decode("utf-8")
    assert "alpha" in rendered
    assert "{{peer}}" not in rendered
    assert "{{interval}}" not in rendered
