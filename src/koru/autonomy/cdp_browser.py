"""Chrome DevTools Protocol (CDP) browser automation adapter for Process URI.

Supports:
  - browser://navigate?url=...
  - browser://click?selector=...
  - browser://screenshot?output=...
  - browser://evaluate?expression=...
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from koru.autonomy.process_uri import ProcessUri


@dataclass
class CdpResponse:
    """Standardized response from CDP action execution."""

    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    action: str = ""


class CdpBrowserController:
    """Translates browser:// Process URIs into CDP commands."""

    def __init__(self, endpoint_url: str = "http://127.0.0.1:9222") -> None:
        self.endpoint_url = endpoint_url
        self._message_id = 0

    def next_id(self) -> int:
        self._message_id += 1
        return self._message_id

    def build_cdp_frame(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Construct a standard CDP JSON-RPC frame."""
        return {
            "id": self.next_id(),
            "method": method,
            "params": params or {},
        }

    def execute_uri(
        self,
        uri: ProcessUri,
        payload: dict[str, Any] | None = None,
        *,
        dry_run: bool = False,
    ) -> CdpResponse:
        """Route a browser:// URI to the appropriate CDP method."""
        if uri.scheme != "browser":
            return CdpResponse(
                success=False,
                error=f"Expected 'browser' scheme, got '{uri.scheme}'",
                action=uri.canonical_action,
            )

        merged = dict(uri.query_params)
        if payload:
            merged.update(payload)

        action = uri.domain + ("/" + uri.action_or_resource if uri.action_or_resource else "")

        if action in ("navigate", "goto", "open"):
            url = merged.get("url") or merged.get("target")
            if not url:
                return CdpResponse(success=False, error="Missing required 'url' parameter", action=action)
            frame = self.build_cdp_frame("Page.navigate", {"url": url})
            return CdpResponse(
                success=True,
                data={"cdp_frame": frame, "dry_run": dry_run, "url": url},
                action=action,
            )

        if action in ("screenshot", "capture"):
            out_path = merged.get("output", "screenshot.png")
            frame = self.build_cdp_frame("Page.captureScreenshot", {"format": "png"})
            return CdpResponse(
                success=True,
                data={"cdp_frame": frame, "output_path": out_path, "dry_run": dry_run},
                action=action,
            )

        if action in ("click", "press"):
            selector = merged.get("selector")
            if not selector:
                return CdpResponse(success=False, error="Missing required 'selector' parameter", action=action)
            expr = f"document.querySelector('{selector}').click()"
            frame = self.build_cdp_frame("Runtime.evaluate", {"expression": expr})
            return CdpResponse(
                success=True,
                data={"cdp_frame": frame, "selector": selector, "dry_run": dry_run},
                action=action,
            )

        if action in ("evaluate", "eval", "js"):
            expr = merged.get("expression") or merged.get("js")
            if not expr:
                return CdpResponse(success=False, error="Missing required 'expression' parameter", action=action)
            frame = self.build_cdp_frame("Runtime.evaluate", {"expression": expr, "returnByValue": True})
            return CdpResponse(
                success=True,
                data={"cdp_frame": frame, "expression": expr, "dry_run": dry_run},
                action=action,
            )

        return CdpResponse(
            success=False,
            error=f"Unknown browser action: '{action}'",
            action=action,
        )
