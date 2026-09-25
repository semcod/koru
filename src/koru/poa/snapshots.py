"""Build and validate hash-pinned Subactor source-registry snapshots.

A snapshot closes discovery output (Config resolutions, Registry and Strategy
evidence, binding candidates) over canonical bytes so later planning stages
can pin exactly what was observed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from .contracts import (
    canonical_json,
    sha256_json,
    validate_poa_document,
    validate_source_snapshot,
)
from .errors import PlanningError
from .validation import parse_utc


def build_source_snapshot(
    *,
    snapshot_id: str,
    created_at: str,
    valid_until: str,
    config_responses: Sequence[Mapping[str, Any]],
    evidence: Sequence[Mapping[str, Any]],
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build and validate a hash-pinned snapshot from secret-free discovery data."""

    responses = [deepcopy(dict(item)) for item in config_responses]
    snapshot: dict[str, Any] = {
        "schema": "koru.poa/source-registry-snapshot/v1",
        "snapshotId": snapshot_id,
        "createdAt": created_at,
        "validUntil": valid_until,
        "resolutions": [{"response": response, "responseSha256": sha256_json(response)} for response in responses],
        "evidence": [deepcopy(dict(item)) for item in evidence],
        "candidates": [deepcopy(dict(item)) for item in candidates],
    }
    snapshot["snapshotHash"] = sha256_json(snapshot)
    return validate_source_registry_snapshot(snapshot)


def validate_source_registry_snapshot(document: Mapping[str, Any]) -> dict[str, Any]:
    snapshot = validate_source_snapshot(document)
    supplied_hash = snapshot["snapshotHash"]
    unhashed = {key: value for key, value in snapshot.items() if key != "snapshotHash"}
    if sha256_json(unhashed) != supplied_hash:
        raise PlanningError("source snapshot hash differs from canonical bytes")

    created_at = parse_utc(snapshot["createdAt"], "snapshot createdAt")
    valid_until = parse_utc(snapshot["validUntil"], "snapshot validUntil")
    if valid_until <= created_at:
        raise PlanningError("source snapshot validity interval is not increasing")

    resolutions, sources, sources_by_need = _validate_snapshot_resolutions(snapshot)
    evidence_by_role = _validate_snapshot_evidence(snapshot, sources)
    _validate_snapshot_candidates(snapshot, resolutions, sources, sources_by_need, evidence_by_role)
    return snapshot


def _validate_snapshot_resolutions(
    snapshot: Mapping[str, Any],
) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]], dict[str, set[str]]]:
    resolutions: dict[str, Mapping[str, Any]] = {}
    sources: dict[str, Mapping[str, Any]] = {}
    sources_by_need: dict[str, set[str]] = {}
    for resolution in snapshot["resolutions"]:
        response = resolution["response"]
        if sha256_json(response) != resolution["responseSha256"]:
            raise PlanningError("Subactor Config response digest differs from canonical bytes")
        data = response["data"]
        need = data["need"]
        if need in resolutions:
            raise PlanningError("source snapshot contains duplicate Config resolution needs")
        resolutions[need] = response
        source_rows = data["matchedSources"]
        source_ids = [row["id"] for row in source_rows]
        if len(source_ids) != len(set(source_ids)):
            raise PlanningError("Subactor Config response contains duplicate source IDs")
        if any(need not in row["provides"] for row in source_rows):
            raise PlanningError("Subactor Config response source does not provide its resolved need")
        sources_by_need[need] = set(source_ids)
        for row in source_rows:
            existing = sources.get(row["id"])
            if existing is not None and canonical_json(existing) != canonical_json(row):
                raise PlanningError("Subactor Config source differs between resolution responses")
            sources[row["id"]] = row
    return resolutions, sources, sources_by_need


def _validate_snapshot_evidence(
    snapshot: Mapping[str, Any],
    sources: Mapping[str, Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    evidence_by_role: dict[str, Mapping[str, Any]] = {}
    for item in snapshot["evidence"]:
        role = item["role"]
        if role in evidence_by_role:
            raise PlanningError(f"source snapshot contains duplicate {role} evidence")
        evidence_by_role[role] = item
    if set(evidence_by_role) != {"registry", "strategy"}:
        raise PlanningError("source snapshot requires exactly one Registry and one Strategy evidence reference")
    for role, item in evidence_by_role.items():
        source = sources.get(item["sourceId"])
        if source is None or source["kind"] != role:
            raise PlanningError(f"{role} evidence is not bound to its discovered source kind")
        if source["availability"]["state"] != "ready":
            raise PlanningError(f"{role} evidence source is not ready")
    return evidence_by_role


def _validate_snapshot_candidates(
    snapshot: Mapping[str, Any],
    resolutions: Mapping[str, Any],
    sources: Mapping[str, Mapping[str, Any]],
    sources_by_need: Mapping[str, set[str]],
    evidence_by_role: Mapping[str, Mapping[str, Any]],
) -> None:
    required_source_ids = {item["sourceId"] for item in evidence_by_role.values()}
    binding_ids: set[str] = set()
    for candidate in snapshot["candidates"]:
        config_needs = set(candidate["configNeeds"])
        if not config_needs.issubset(resolutions):
            raise PlanningError("binding candidate references an unavailable Config resolution need")
        candidate_sources = set(candidate["sourceIds"])
        if not required_source_ids.issubset(candidate_sources) or not candidate_sources.issubset(sources):
            raise PlanningError(
                "binding candidate provenance is not closed over discovered Registry and Strategy sources"
            )
        if any(not candidate_sources.intersection(sources_by_need[need]) for need in config_needs):
            raise PlanningError("binding candidate does not bind every declared Config resolution need")
        binding = validate_poa_document(candidate["binding"], expected_schema="poa.binding/v1")
        binding_id = binding["binding_id"]
        if binding_id in binding_ids:
            raise PlanningError("source snapshot contains duplicate binding IDs")
        binding_ids.add(binding_id)


__all__ = [
    "build_source_snapshot",
    "validate_source_registry_snapshot",
]
