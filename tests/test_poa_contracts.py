from __future__ import annotations

import json

import pytest

from koru.poa.contracts import (
    POA_PROCESS_SCHEMA_PATH,
    POA_PROCESS_SCHEMA_SHA256,
    SOURCE_REGISTRY_SCHEMA_PATH,
    SOURCE_REGISTRY_SCHEMA_SHA256,
    WELLMANIFEST_LOGS_CONTRACT_PATH,
    WELLMANIFEST_LOGS_CONTRACT_SHA256,
    ContractError,
    canonical_json,
    load_logs_contract,
    load_pinned_document,
    load_poa_schema,
    load_source_registry_schema,
    verify_contract_pins,
)


def test_exact_contract_bytes_are_pinned() -> None:
    assert verify_contract_pins() == {
        "wellmanifest/poa:v1": POA_PROCESS_SCHEMA_SHA256,
        "koru/poa-source-registry:v1": SOURCE_REGISTRY_SCHEMA_SHA256,
        "wellmanifest/logs:v0.3": WELLMANIFEST_LOGS_CONTRACT_SHA256,
    }
    assert load_poa_schema()["$id"].endswith("poa-process.schema.v1.json")
    logs = load_logs_contract()
    assert logs["version"] == "0.3.0"
    assert logs["hashProfile"] == "wellmanifest-canonical-json-v1+SHA-256"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (POA_PROCESS_SCHEMA_PATH, POA_PROCESS_SCHEMA_SHA256),
        (SOURCE_REGISTRY_SCHEMA_PATH, SOURCE_REGISTRY_SCHEMA_SHA256),
        (WELLMANIFEST_LOGS_CONTRACT_PATH, WELLMANIFEST_LOGS_CONTRACT_SHA256),
    ],
)
def test_contract_byte_drift_fails_closed(tmp_path, source, expected) -> None:
    changed = tmp_path / source.name
    changed.write_bytes(source.read_bytes() + b"\n")
    with pytest.raises(ContractError, match="contract digest drift"):
        load_pinned_document(changed, expected)


def test_source_registry_schema_is_closed_and_excludes_policy() -> None:
    schema = load_source_registry_schema()
    assert schema["additionalProperties"] is False
    assert "policyDecision" not in schema["properties"]
    assert schema["$id"].endswith("source-registry-snapshot.v1.json")
    assert json.loads(SOURCE_REGISTRY_SCHEMA_PATH.read_text("utf-8")) == schema


def test_logs_event_contract_has_exact_safety_and_chain_fields() -> None:
    event = load_logs_contract()["schemas"]["event"]
    assert event["additionalProperties"] is False
    assert {
        "sequence",
        "previousHash",
        "eventHash",
        "rawOutputIncluded",
        "secretMaterialIncluded",
    }.issubset(event["required"])
    assert event["properties"]["rawOutputIncluded"] == {"const": False}
    assert event["properties"]["secretMaterialIncluded"] == {"const": False}


def test_canonical_domain_rejects_floating_point_values() -> None:
    with pytest.raises(ContractError, match="floating-point"):
        canonical_json({"unsafe": 0.1})
