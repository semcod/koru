"""FastAPI REST adapter for dsl2coru."""

from __future__ import annotations

import json
from typing import Any

from dsl2coru.bus import dispatch
from dsl2coru.events import EventStore
from dsl2coru.pb_codec import encode_result_protobuf
from dsl2coru.schema_registry import schema_for_verb, validate_schemas
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response


def create_app() -> FastAPI:
    app = FastAPI(title="rest2coru", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/schema/{verb}")
    def get_schema(verb: str) -> dict[str, Any]:
        return schema_for_verb(verb)

    @app.get("/v1/schema")
    def validate_all() -> dict[str, Any]:
        errors = validate_schemas()
        return {"ok": not errors, "errors": errors}

    async def _handle(request: Request, project: str = ".") -> Response:
        content_type = request.headers.get("content-type", "text/plain").split(";")[0].strip()
        body = await request.body()
        if content_type == "application/x-protobuf":
            result = dispatch(body, default_project=project)
            return Response(encode_result_protobuf(result), media_type="application/x-protobuf")
        if content_type == "application/json":
            payload = json.loads(body.decode("utf-8"))
            result = dispatch(payload, default_project=project)
            return JSONResponse(result.to_dict())
        line = body.decode("utf-8").strip()
        result = dispatch(line, default_project=project)
        return JSONResponse(result.to_dict())

    @app.post("/v1/dsl")
    async def post_dsl(request: Request, project: str = ".") -> Response:
        return await _handle(request, project=project)

    @app.post("/v1/commands")
    async def post_commands(request: Request, project: str = ".") -> Response:
        return await _handle(request, project=project)

    @app.get("/v1/events")
    def get_events(project: str = ".") -> JSONResponse:
        store = EventStore.for_default(project)
        events = [event.to_dict() for event in store.read_all()]
        return JSONResponse(events)

    @app.get("/v1/proto")
    def get_proto() -> Response:
        from importlib import resources

        proto_pkg = resources.files("dsl2coru").joinpath("proto/dsl2coru/v1")
        parts = []
        for name in ("command.proto", "result.proto", "event.proto"):
            path = proto_pkg / name
            if path.is_file():
                parts.append(path.read_text(encoding="utf-8"))
        return Response("\n\n".join(parts) or 'syntax = "proto3";\n', media_type="text/plain")

    return app


app = create_app()
