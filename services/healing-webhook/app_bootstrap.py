from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import FastAPI


def create_webhook_app(*, title: str, version: str) -> FastAPI:
    """Create the FastAPI app object for healing-webhook."""
    return FastAPI(title=title, version=version)


def wire_routes(
    app: FastAPI,
    *,
    healthz_handler: Callable[[], dict[str, Any]],
    metrics_handler: Callable[[], Any],
    history_handler: Callable[[], list[dict]],
    alertmanager_handler: Callable[..., Any],
    probe_failure_handler: Callable[..., Any],
    tickets_handler: Callable[[], dict[str, Any]],
) -> None:
    """Bind route paths to handler callables.

    Keeping this wiring separate reduces coupling in app.py and lets future
    route changes happen without touching healing command logic.
    """
    app.add_api_route("/healthz", healthz_handler, methods=["GET"])
    app.add_api_route("/metrics", metrics_handler, methods=["GET"])
    app.add_api_route("/history", history_handler, methods=["GET"])
    app.add_api_route("/alertmanager", alertmanager_handler, methods=["POST"])
    app.add_api_route("/probe-failure", probe_failure_handler, methods=["POST"])
    app.add_api_route("/tickets", tickets_handler, methods=["GET"])
