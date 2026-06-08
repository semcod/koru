"""Phase 5 — schema → pydantic codegen."""

import pytest

pydantic = pytest.importorskip("pydantic")

from dsl2coru.codegen import build_model_registry, validate_payload


def test_codegen_registry_covers_verbs() -> None:
    registry = build_model_registry()
    assert "STATUS" in registry
    assert "AUTO" in registry
    assert len(registry) >= 10


def test_status_model() -> None:
    model = validate_payload({"verb": "STATUS"})
    assert model.verb == "STATUS"
