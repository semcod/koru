"""NL hints → coru:// URI (nlp2uri layer)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from uri2coru.uri import uri_for_block, uri_for_cmd


@dataclass(frozen=True)
class ResolvedCoruUri:
    uri: str
    confidence: float
    match_reason: str
    dsl: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "uri": self.uri,
            "confidence": self.confidence,
            "match_reason": self.match_reason,
            "dsl": self.dsl,
        }


def nlp2uri(prompt: str, *, default_file: str | None = None, project: str | None = None) -> list[ResolvedCoruUri]:
    normalized = re.sub(r"\s+", " ", prompt.lower().strip())
    if not normalized:
        return []

    hits: list[ResolvedCoruUri] = []
    ctx = default_file or project or "."

    if any(h in normalized for h in ("repair history", "historia repair", "repair log")):
        uri = uri_for_block("repair", "history", default_file=ctx)
        hits.append(
            ResolvedCoruUri(
                uri=uri,
                confidence=0.9,
                match_reason="block:repair/history",
                dsl="REPAIR_HISTORY",
            ),
        )

    if any(h in normalized for h in ("lane status", "status lane", "lane-status")):
        uri = uri_for_block("lane", "status", default_file=ctx)
        hits.append(
            ResolvedCoruUri(
                uri=uri,
                confidence=0.85,
                match_reason="block:lane/status",
                dsl="LANE_STATUS --ide auto --instance default",
            ),
        )

    if any(h in normalized for h in ("validate lane", "waliduj lane", "lane setup", "ustaw lane")):
        uri = uri_for_cmd("LANE", ide="auto", instance="default", default_file=ctx)
        hits.append(
            ResolvedCoruUri(
                uri=uri,
                confidence=0.82,
                match_reason="cmd:LANE",
                dsl="LANE --ide auto --instance default",
            ),
        )

    if any(h in normalized for h in ("repair run", "napraw", "fix lane")):
        uri = uri_for_cmd("REPAIR_RUN", ide="auto", instance="default", default_file=ctx)
        hits.append(
            ResolvedCoruUri(
                uri=uri,
                confidence=0.8,
                match_reason="cmd:REPAIR_RUN",
                dsl="REPAIR_RUN --ide auto --instance default",
            ),
        )

    seen: set[str] = set()
    unique: list[ResolvedCoruUri] = []
    for hit in sorted(hits, key=lambda h: h.confidence, reverse=True):
        if hit.uri in seen:
            continue
        seen.add(hit.uri)
        unique.append(hit)
    return unique


def best_uri(prompt: str, *, default_file: str | None = None, project: str | None = None) -> ResolvedCoruUri | None:
    hits = nlp2uri(prompt, default_file=default_file, project=project)
    return hits[0] if hits else None
