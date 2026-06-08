"""URI → DSL → dispatch."""

from __future__ import annotations

from dsl2coru.bus import dispatch
from dsl2coru.result import DslResult
from uri2coru.decode import uri_to_dsl


def run_uri(
    uri: str,
    *,
    default_file: str | None = None,
    default_project: str | None = None,
    runner=None,
) -> DslResult:
    ctx = default_file or default_project
    line = uri_to_dsl(uri, default_file=ctx)
    return dispatch(line, default_project=ctx, runner=runner)
