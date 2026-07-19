"""Strict, hash-bound output envelope for model-authored proposals.

The model may fill the bounded proposal fields. Koru validates and hashes the
result before an executor sees the artifact; the envelope itself grants no
authority and deliberately has no URI, transport, secret, approval, executor,
or capability field.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Any

from jsonschema import Draft202012Validator

NO_VALID_ARTIFACT = "no_valid_artifact"
SCHEMA_VERSION = "1.0"

_SCHEMA_RESOURCE = "data/proposal-envelope-v1.schema.json"
_FORBIDDEN_SLOT_KEYS = frozenset(
    {
        "approval",
        "approved",
        "capabilities",
        "capability",
        "executor",
        "secret",
        "transport",
        "uri",
        "vault",
        "vault_ref",
    },
)


class ProposalValidationError(ValueError):
    """A structural proposal failure safe to send back for one bounded retry."""

    code = NO_VALID_ARTIFACT
    retryable = True


@dataclass(frozen=True)
class ProposalEnvelope:
    schema_version: str
    intent_pack_id: str
    intent_pack_version: str
    slots: dict[str, Any]
    artifact_kind: str
    artifact_content: Any
    input_hash: str
    prompt_schema_hash: str
    provider: str
    model: str
    artifact_sha256: str
    proposal_sha256: str


@lru_cache(maxsize=1)
def _schema() -> dict[str, Any]:
    resource = resources.files("koru").joinpath(_SCHEMA_RESOURCE)
    return json.loads(resource.read_text(encoding="utf-8"))


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _payload_without_hashes(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "hashes"}


def _forbidden_slot_paths(value: Any, path: str = "slots") -> tuple[str, ...]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key).strip().lower() in _FORBIDDEN_SLOT_KEYS:
                found.append(child_path)
            found.extend(_forbidden_slot_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_forbidden_slot_paths(child, f"{path}[{index}]"))
    return tuple(found)


def build_proposal_envelope(
    *,
    intent_pack_id: str,
    intent_pack_version: str,
    slots: dict[str, Any],
    artifact_kind: str,
    artifact_content: Any,
    input_hash: str,
    prompt_schema_hash: str,
    provider: str,
    model: str,
) -> dict[str, Any]:
    """Build and validate a canonical envelope; hashes are computed, never trusted."""
    base: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "intent_pack": {"id": intent_pack_id, "version": intent_pack_version},
        "slots": slots,
        "artifact": {"kind": artifact_kind, "content": artifact_content},
        "bindings": {
            "input_hash": input_hash,
            "prompt_schema_hash": prompt_schema_hash,
        },
        "provenance": {"provider": provider, "model": model},
    }
    payload = {
        **base,
        "hashes": {
            "artifact_sha256": _sha256(base["artifact"]),
            "proposal_sha256": _sha256(base),
        },
    }
    validate_proposal_envelope(payload)
    return payload


def validate_proposal_envelope(payload: object) -> ProposalEnvelope:
    """Validate shape, authority exclusions, and both content bindings."""
    if not isinstance(payload, dict):
        raise ProposalValidationError("proposal envelope must be a JSON object")

    errors = sorted(
        Draft202012Validator(_schema()).iter_errors(payload),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "envelope"
        raise ProposalValidationError(f"{location}: {first.message}")

    forbidden = _forbidden_slot_paths(payload["slots"])
    if forbidden:
        raise ProposalValidationError(
            "model-authored slots cannot contain authority/execution fields: "
            + ", ".join(forbidden),
        )

    artifact_sha256 = _sha256(payload["artifact"])
    proposal_sha256 = _sha256(_payload_without_hashes(payload))
    if payload["hashes"]["artifact_sha256"] != artifact_sha256:
        raise ProposalValidationError("artifact_sha256 does not match canonical artifact")
    if payload["hashes"]["proposal_sha256"] != proposal_sha256:
        raise ProposalValidationError("proposal_sha256 does not match canonical envelope")

    return ProposalEnvelope(
        schema_version=payload["schema_version"],
        intent_pack_id=payload["intent_pack"]["id"],
        intent_pack_version=payload["intent_pack"]["version"],
        slots=dict(payload["slots"]),
        artifact_kind=payload["artifact"]["kind"],
        artifact_content=payload["artifact"]["content"],
        input_hash=payload["bindings"]["input_hash"],
        prompt_schema_hash=payload["bindings"]["prompt_schema_hash"],
        provider=payload["provenance"]["provider"],
        model=payload["provenance"]["model"],
        artifact_sha256=artifact_sha256,
        proposal_sha256=proposal_sha256,
    )


def parse_proposal_envelope(content: str) -> ProposalEnvelope:
    """Parse exact JSON. Markdown fences and surrounding prose are not accepted."""
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ProposalValidationError(f"proposal envelope is not exact JSON: {exc.msg}") from exc
    return validate_proposal_envelope(payload)


def looks_like_proposal_envelope(content: str) -> bool:
    """Distinguish an attempted envelope from the legacy bare-diff contract."""
    stripped = content.strip()
    if not stripped.startswith("{"):
        return False
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return '"schema_version"' in stripped or '"artifact"' in stripped
    return isinstance(payload, dict) and (
        "schema_version" in payload or "artifact" in payload or "intent_pack" in payload
    )
