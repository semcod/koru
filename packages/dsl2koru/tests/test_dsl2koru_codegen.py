"""Phase 5 — schema → pydantic codegen."""

import pytest

pydantic = pytest.importorskip("pydantic")

from dsl2koru.codegen import build_model_registry, validate_payload


def test_codegen_registry_covers_all_verbs() -> None:
    registry = build_model_registry()
    assert "VALIDATE_LANE" in registry
    assert "REPAIR_RUN" in registry
    assert len(registry) >= 5


def test_validate_lane_model() -> None:
    model = validate_payload({"verb": "VALIDATE_LANE", "ide": "auto", "instance": "default"})
    assert model.verb == "VALIDATE_LANE"
    assert model.ide == "auto"
