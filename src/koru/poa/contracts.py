"""Pinned POA and Wellmanifest Logs contract helpers.

The module deliberately handles data only.  Loading or validating a document
does not grant authority, resolve credentials, or execute a process URI.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]

POA_PROCESS_SCHEMA_SHA256 = "9222fbe9aded60df6d3c0b39b7a4a89b8ad627f122349e909fdfba44047669ab"
POA_REQUEST_GRAMMAR_SHA256 = "d13d736cc3f4e07dd9366378183055ff0d9ad10dd4fc5bf1f322e2dc37d919ee"
SOURCE_REGISTRY_SCHEMA_SHA256 = "94fc544a75ee5f2e940399a1dba3eda193e8fb916add053c4daca655c723f165"
WELLMANIFEST_LOGS_CONTRACT_SHA256 = "916ccdd3a6f499b160b631da09a6a060233105e907f5582c12d8eaecae92e2eb"

_DATA_ROOT = Path(__file__).resolve().parents[1] / "data"
POA_PROCESS_SCHEMA_PATH = _DATA_ROOT / "poa-process-v1.schema.json"
WELLMANIFEST_LOGS_CONTRACT_PATH = _DATA_ROOT / "wellmanifest-logs-contract-v0.3.json"
SOURCE_REGISTRY_SCHEMA_PATH = _DATA_ROOT / "koru-poa-source-registry-v1.schema.json"
_MAX_CONTRACT_BYTES = 1024 * 1024
_MAX_SAFE_INTEGER = 9_007_199_254_740_991
_SENSITIVE_KEY = re.compile(
    r"(?:^|[_-])(?:token|password|passwd|secret|private[_-]?key|api[_-]?key|access[_-]?key)(?:$|[_-])",
    re.IGNORECASE,
)
_SENSITIVE_VALUE = re.compile(
    r"(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|https?://[^/@\s]+:[^/@\s]+@|"
    r"[?&](?:token|password|passwd|secret|private[_-]?key|api[_-]?key|access[_-]?key)=)",
    re.IGNORECASE,
)


class ContractError(ValueError):
    """A closed contract, digest, or canonicalization failure."""


def canonical_json(value: Any) -> str:
    """Return the canonical JSON used by the adopted bounded data domain.

    The adopted POA and Logs documents exclude floating-point numbers.  Within
    that I-JSON subset, sorted UTF-8 JSON with compact separators is the byte
    projection used for deterministic hashes.
    """

    _validate_canonical_domain(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_pinned_document(path: Path, expected_sha256: str) -> dict[str, Any]:
    """Load one bounded regular JSON file only when its exact bytes are pinned."""

    try:
        if path.is_symlink() or not path.is_file() or not 1 <= path.stat().st_size <= _MAX_CONTRACT_BYTES:
            raise OSError("contract is not a bounded regular file")
        raw = path.read_bytes()
    except OSError as error:
        raise ContractError(f"contract unavailable: {path.name}") from error
    observed = hashlib.sha256(raw).hexdigest()
    if observed != expected_sha256:
        raise ContractError(f"contract digest drift: {path.name}")
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContractError(f"contract JSON invalid: {path.name}") from error
    if not isinstance(value, dict):
        raise ContractError(f"contract root must be an object: {path.name}")
    return value


def load_poa_schema() -> dict[str, Any]:
    return load_pinned_document(POA_PROCESS_SCHEMA_PATH, POA_PROCESS_SCHEMA_SHA256)


def load_logs_contract() -> dict[str, Any]:
    return load_pinned_document(WELLMANIFEST_LOGS_CONTRACT_PATH, WELLMANIFEST_LOGS_CONTRACT_SHA256)


def load_source_registry_schema() -> dict[str, Any]:
    value = load_pinned_document(SOURCE_REGISTRY_SCHEMA_PATH, SOURCE_REGISTRY_SCHEMA_SHA256)
    try:
        Draft202012Validator.check_schema(value)
    except Exception as error:  # jsonschema exposes several schema-error subclasses
        raise ContractError("source registry schema is invalid") from error
    return value


def verify_contract_pins() -> dict[str, str]:
    """Verify the exact vendored bytes and return their stable digests."""

    load_poa_schema()
    load_logs_contract()
    return {
        "wellmanifest/poa:v1": sha256_file(POA_PROCESS_SCHEMA_PATH),
        "koru/poa-source-registry:v1": sha256_file(SOURCE_REGISTRY_SCHEMA_PATH),
        "wellmanifest/logs:v0.3": sha256_file(WELLMANIFEST_LOGS_CONTRACT_PATH),
    }


def validate_poa_document(document: Mapping[str, Any], *, expected_schema: str | None = None) -> dict[str, Any]:
    value = _plain_object(document, "POA document")
    if expected_schema is not None and value.get("schema") != expected_schema:
        raise ContractError(f"POA document must use {expected_schema}")
    validate_json_document(value, load_poa_schema(), label="POA document")
    return value


def validate_source_snapshot(document: Mapping[str, Any]) -> dict[str, Any]:
    value = _plain_object(document, "source snapshot")
    reject_secret_material(value)
    validate_json_document(value, load_source_registry_schema(), label="source snapshot")
    return value


def validate_json_document(document: Any, schema: Mapping[str, Any], *, label: str) -> None:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(document), key=lambda item: tuple(str(part) for part in item.absolute_path))
    if not errors:
        return
    error = errors[0]
    path = ".".join(str(part) for part in error.absolute_path) or "$"
    raise ContractError(f"{label} violates closed schema at {path} ({error.validator})")


def reject_secret_material(value: Any, *, path: str = "$") -> None:
    """Reject secret-shaped keys and values without echoing their contents."""

    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ContractError(f"non-string key at {path}")
            if _SENSITIVE_KEY.search(key):
                raise ContractError(f"secret-shaped key at {path}")
            reject_secret_material(child, path=f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            reject_secret_material(child, path=f"{path}[{index}]")
        return
    if isinstance(value, str) and _SENSITIVE_VALUE.search(value):
        raise ContractError(f"secret-shaped value at {path}")


def _plain_object(value: Mapping[str, Any], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{label} must be an object")
    copied = deepcopy(dict(value))
    _validate_canonical_domain(copied)
    return copied


def _validate_canonical_domain(value: Any, *, path: str = "$") -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int):
        if not -_MAX_SAFE_INTEGER <= value <= _MAX_SAFE_INTEGER:
            raise ContractError(f"integer outside the canonical domain at {path}")
        return
    if isinstance(value, float):
        raise ContractError(f"floating-point value outside the canonical domain at {path}")
    if isinstance(value, list):
        for index, child in enumerate(value):
            _validate_canonical_domain(child, path=f"{path}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ContractError(f"non-string key outside the canonical domain at {path}")
            _validate_canonical_domain(child, path=f"{path}.{key}")
        return
    raise ContractError(f"non-JSON value outside the canonical domain at {path}")
