from __future__ import annotations

import json
from pathlib import Path

from koru.configurator.schema import CONFIG_REL_PATH
from koru.configurator.store import load_project_config, save_project_config


def test_load_returns_empty_when_no_config_file(tmp_path: Path) -> None:
    assert load_project_config(tmp_path) == {}


def test_load_returns_empty_on_malformed_json(tmp_path: Path) -> None:
    config_file = tmp_path / CONFIG_REL_PATH
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text("{not valid json", encoding="utf-8")
    assert load_project_config(tmp_path) == {}


def test_load_returns_empty_when_json_is_not_a_dict(tmp_path: Path) -> None:
    config_file = tmp_path / CONFIG_REL_PATH
    config_file.parent.mkdir(parents=True, exist_ok=True)
    for payload in ('["a", "b"]', '"a string"', "42", "null", "true"):
        config_file.write_text(payload, encoding="utf-8")
        assert load_project_config(tmp_path) == {}


def test_save_then_load_round_trips(tmp_path: Path) -> None:
    payload = {"schema": "koru.config/v1", "ide": "windsurf", "serve": {"port": 8765}}
    path = save_project_config(tmp_path, payload)
    assert path == tmp_path.resolve() / CONFIG_REL_PATH
    assert load_project_config(tmp_path) == payload


def test_save_creates_parent_dir_and_writes_sorted_pretty_json(tmp_path: Path) -> None:
    project = tmp_path / "deep" / "project"
    payload = {"b": 2, "a": 1, "nested": {"z": 0, "y": 9}}
    path = save_project_config(project, payload)

    assert path.is_file()
    raw = path.read_text(encoding="utf-8")
    # pretty-printed, sorted keys, trailing newline
    assert raw.endswith("\n")
    decoded = json.loads(raw)
    assert decoded == payload
    # top-level keys are sorted (a before b before nested)
    assert list(decoded.keys()) == sorted(decoded.keys())


def test_load_resolves_symlinked_project_root(tmp_path: Path) -> None:
    real = tmp_path / "real"
    link = tmp_path / "link"
    real.mkdir()
    link.symlink_to(real)
    save_project_config(real, {"ide": "vscode"})
    # Reading through the symlink must resolve to the real project's config.
    assert load_project_config(link) == {"ide": "vscode"}
