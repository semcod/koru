"""NL hints → koru:// URI (nlp2uri layer)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from uri2koru.uri import uri_for_block, uri_for_cmd


@dataclass(frozen=True)
class ResolvedKoruUri:
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


def nlp2uri(prompt: str, *, project: str | None = None) -> list[ResolvedKoruUri]:
    normalized = re.sub(r"\s+", " ", prompt.lower().strip())
    if not normalized:
        return []

    hits: list[ResolvedKoruUri] = []
    proj = project or "."

    if any(h in normalized for h in ("repair history", "historia repair", "repair log")):
        uri = uri_for_block("repair", "history", project=proj)
        hits.append(ResolvedKoruUri(uri=uri, confidence=0.9, match_reason="block:repair/history", dsl=f"QUERY_REPAIR_HISTORY PROJECT {proj}"))

    if any(h in normalized for h in ("lane status", "status lane", "lane-status")):
        uri = uri_for_block("lane", "status", project=proj)
        hits.append(
            ResolvedKoruUri(
                uri=uri,
                confidence=0.85,
                match_reason="block:lane/status",
                dsl="QUERY_LANE_STATUS IDE auto INSTANCE default",
            ),
        )

    if any(h in normalized for h in ("validate lane", "waliduj lane")):
        uri = uri_for_cmd("VALIDATE_LANE", ide="auto", instance="default", project=proj)
        hits.append(
            ResolvedKoruUri(
                uri=uri,
                confidence=0.82,
                match_reason="cmd:VALIDATE_LANE",
                dsl="VALIDATE_LANE IDE auto INSTANCE default",
            ),
        )

    if any(h in normalized for h in ("repair run", "napraw", "fix lane")):
        uri = uri_for_cmd("REPAIR_RUN", ide="auto", instance="default", project=proj)
        hits.append(
            ResolvedKoruUri(
                uri=uri,
                confidence=0.8,
                match_reason="cmd:REPAIR_RUN",
                dsl=f"REPAIR_RUN IDE auto INSTANCE default PROJECT {proj}",
            ),
        )

    seen: set[str] = set()
    unique: list[ResolvedKoruUri] = []
    for hit in sorted(hits, key=lambda h: h.confidence, reverse=True):
        if hit.uri in seen:
            continue
        seen.add(hit.uri)
        unique.append(hit)
    return unique


def best_uri(prompt: str, *, project: str | None = None) -> ResolvedKoruUri | None:
    hits = nlp2uri(prompt, project=project)
    return hits[0] if hits else None
