from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _uv_lock_koru_package() -> dict:
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    return next(package for package in lock["package"] if package["name"] == "koru")


def test_base_runtime_dependencies_stay_small() -> None:
    project = _pyproject()["project"]

    assert project["dependencies"] == [
        "gillm>=0.1.9",
        "pyyaml>=6.0,<7.0",
        "rich>=14.3.4",
    ]


def test_all_extra_matches_union_of_other_extras() -> None:
    optional = _pyproject()["project"]["optional-dependencies"]
    expected = {
        requirement
        for extra, requirements in optional.items()
        if extra != "all"
        for requirement in requirements
    }

    assert set(optional["all"]) == expected


def test_readme_documents_each_installation_extra() -> None:
    optional = _pyproject()["project"]["optional-dependencies"]
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    for extra in optional:
        assert f"koru[{extra}]" in readme


def test_uv_lock_koru_metadata_matches_pyproject() -> None:
    project = _pyproject()["project"]
    locked = _uv_lock_koru_package()

    assert locked["version"] == project["version"]
    assert sorted(locked["optional-dependencies"]) == sorted(project["optional-dependencies"])
    assert sorted(locked["metadata"]["provides-extras"]) == sorted(project["optional-dependencies"])
