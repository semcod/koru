import importlib
import sys

import pytest
from fastapi.testclient import TestClient


def test_legacy_rest_warns_and_reexports_canonical_adapter() -> None:
    sys.modules.pop("rest2coru", None)
    sys.modules.pop("rest2coru.app", None)
    with pytest.warns(DeprecationWarning, match="rest2coru is deprecated"):
        legacy_app = importlib.import_module("rest2coru.app")
    legacy_cli = importlib.import_module("rest2coru.cli")
    canonical_app = importlib.import_module("rest2koru.app")
    canonical_cli = importlib.import_module("rest2koru.cli")

    assert legacy_app.app is canonical_app.app
    assert legacy_app.create_app is canonical_app.create_app
    assert legacy_cli.main is canonical_cli.main

    client = TestClient(legacy_app.create_app())
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    resp = client.post(
        "/v1/dsl?project=.",
        content="VALIDATE_LANE IDE auto INSTANCE default",
        headers={"Content-Type": "text/plain"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
