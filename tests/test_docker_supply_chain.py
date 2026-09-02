from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DOCKERFILES = {
    "Dockerfile",
    "docker/capture/Dockerfile",
    "docker/novnc/Dockerfile",
    "examples/Dockerfile.remote-mesh",
    "examples/docker/koru-e2e.Dockerfile",
    "services/healing-webhook/Dockerfile",
    "tests/docker/ide-matrix.Dockerfile",
}

COMPOSE_FILES = {
    "docker-compose.yml",
    "docker/novnc/docker-compose.yml",
    "examples/ci/headless-autonomous-jsonl/docker-compose.yml",
    "examples/docker-compose-remote-mesh.yml",
    "examples/env/autopilot-ide-auto/docker-compose.yml",
    "examples/env/autopilot-ide-cursor/docker-compose.yml",
    "examples/nlp2uri-testql-browser/docker-compose.yml",
    "examples/planfile/http-api-curl/docker-compose.yml",
    "examples/planfile/queue-cli-dryrun/docker-compose.yml",
    "examples/protocol/autopilot-socket-smoke/docker-compose.yml",
    "examples/runtime/koru-serve-health/docker-compose.yml",
}

DOCKERFILE_NAME = re.compile(r"^(?:Dockerfile(?:\..+)?|.+\.Dockerfile)$")
COMPOSE_NAME = re.compile(r"^(?:docker-)?compose(?:[.-].+)?\.ya?ml$")
FROM = re.compile(r"^FROM\s+(?:--platform=\S+\s+)?(?P<image>\S+)(?:\s+AS\s+(?P<alias>\S+))?\s*$", re.I)
DIGEST_IMAGE = re.compile(r"^\S+@sha256:[0-9a-f]{64}$")
REMOTE_CONTEXT = re.compile(r"^https://github\.com/(?P<repository>[^#]+\.git)#(?P<revision>[0-9a-f]{40})$")


def _tracked_files() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return set(result.stdout.splitlines())


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _assert_immutable_froms(path: str, content: str) -> None:
    aliases: set[str] = set()
    references = 0
    for raw_line in content.splitlines():
        match = FROM.fullmatch(raw_line.strip())
        if match is None:
            continue
        references += 1
        image = match.group("image")
        if image.lower() in aliases:
            pass
        elif image == "${BASE_IMAGE}":
            default = re.search(r"^ARG BASE_IMAGE=(\S+)$", content, re.MULTILINE)
            assert default is not None, f"{path}: variable FROM has no default"
            assert DIGEST_IMAGE.fullmatch(default.group(1)), f"{path}: mutable BASE_IMAGE default"
        else:
            assert DIGEST_IMAGE.fullmatch(image), f"{path}: mutable external FROM {image}"
        alias = match.group("alias")
        if alias:
            aliases.add(alias.lower())
    assert references, f"{path}: no FROM declaration found"


def test_inventory_is_exhaustive_for_tracked_build_inputs() -> None:
    tracked = _tracked_files()
    dockerfiles = {path for path in tracked if DOCKERFILE_NAME.fullmatch(Path(path).name)}
    compose_files = {path for path in tracked if COMPOSE_NAME.fullmatch(Path(path).name)}

    assert dockerfiles == DOCKERFILES
    assert compose_files == COMPOSE_FILES


def test_every_external_from_and_compose_image_is_digest_pinned() -> None:
    for path in sorted(DOCKERFILES):
        _assert_immutable_froms(path, _text(path))

    for path in sorted(COMPOSE_FILES):
        content = _text(path)
        if "dockerfile_inline:" in content:
            _assert_immutable_froms(f"{path}:dockerfile_inline", content)
        for image in re.findall(r"^\s*image:\s*([^\s#]+)", content, re.MULTILINE):
            assert DIGEST_IMAGE.fullmatch(image), f"{path}: mutable Compose image {image}"


def test_remote_git_contexts_use_expected_repositories_and_full_commits() -> None:
    contexts: list[str] = []
    for path in sorted(COMPOSE_FILES):
        contexts.extend(re.findall(r"^\s*context:\s*(https://\S+)$", _text(path), re.MULTILINE))

    parsed = [REMOTE_CONTEXT.fullmatch(context) for context in contexts]
    assert all(parsed), contexts
    assert {match.group("repository") for match in parsed if match} == {
        "autogrammar/testql.git",
        "semcod/planfile.git",
        "semcod/regix.git",
    }
    assert len(contexts) == 3


def test_non_root_python_installers_are_lock_driven_and_pip_free() -> None:
    for path in sorted(DOCKERFILES - {"Dockerfile"}):
        content = _text(path)
        assert not re.search(r"(?<!uv )\bpip\s+install", content, re.I), path
        if "uv pip install" in content:
            assert "--no-deps --require-hashes" in content, path

    lock_driven_inputs = {
        "docker/capture/Dockerfile": _text("docker/capture/Dockerfile"),
        "docker/novnc/Dockerfile": _text("docker/novnc/Dockerfile") + _text("docker/novnc/start-vnc.sh"),
        "examples/Dockerfile.remote-mesh": _text("examples/Dockerfile.remote-mesh"),
        "examples/docker/koru-e2e.Dockerfile": _text("examples/docker/koru-e2e.Dockerfile"),
        "services/healing-webhook/Dockerfile": _text("services/healing-webhook/Dockerfile"),
        "tests/docker/ide-matrix.Dockerfile": _text("tests/docker/ide-matrix.Dockerfile"),
    }
    for path, content in lock_driven_inputs.items():
        assert re.search(r"\buv\s+lock\b.*?--check\b.*?--no-sources\b", content, re.DOTALL), path
        assert "uv sync" in content, path
        assert "--frozen" in content, path

    inline = _text("docker-compose.yml")
    assert "uv lock --check --no-sources" in inline
    assert "uv sync --frozen" in inline
    assert "pip install" not in inline
    assert 'PATH="/app/.venv/bin:$${PATH}"' in inline


def test_example_and_ide_matrix_remove_mutable_dependency_injection() -> None:
    example = _text("examples/docker/koru-e2e.Dockerfile")
    nlp_compose = _text("examples/nlp2uri-testql-browser/docker-compose.yml")
    fixture = _text("tests/docker/ide-matrix.Dockerfile")

    assert "EXTRA_PIP" not in example
    assert "EXTRA_PIP" not in nlp_compose
    assert "uv.lock" in fixture
    assert "--no-install-project" in fixture
    assert "UV_PYTHON=python3.12" in fixture


def test_ide_matrix_launcher_accepts_only_digest_pinned_bases() -> None:
    script = _text("scripts/docker-ide-matrix.sh")
    block = re.search(r"DEFAULT_SYSTEMS=\(\n(?P<body>.*?)\n\)", script, re.DOTALL)
    assert block is not None
    entries = dict(re.findall(r'^\s*"([^"=]+)=([^"=]+)"$', block.group("body"), re.MULTILINE))

    assert set(entries) == {"debian-slim", "debian-bookworm", "ubuntu-noble", "fedora", "alpine"}
    assert all(DIGEST_IMAGE.fullmatch(image) for image in entries.values())
    assert '[[ ! "${base_image}" =~ @sha256:[0-9a-f]{64}$ ]]' in script
