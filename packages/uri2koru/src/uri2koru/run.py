"""URI → DSL → dispatch."""

from __future__ import annotations

from dsl2koru.bus import dispatch
from dsl2koru.result import DslResult
from uri2koru.decode import uri_to_dsl


def run_uri(uri: str, *, default_project: str | None = None) -> DslResult:
    line = uri_to_dsl(uri, default_project=default_project)
    return dispatch(line, default_project=default_project)
