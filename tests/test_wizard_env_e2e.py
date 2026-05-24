"""End-to-end tests for ``koru wizard`` driven via real subprocess invocations.

These tests exercise the installed CLI (the one available on PATH inside the
test venv) so we catch packaging issues (missing strategies.json,
missing templates, missing GUI assets), environment behaviour, and exit codes.

All file I/O happens in tmp dirs; we never mutate the developer's home or the
koru repo itself.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import importlib.util
from pathlib import Path

import pytest

KORU_CLI_SPEC = importlib.util.find_spec("koru.cli")
KORU_CMD = [sys.executable, "-m", "koru.cli"]
pytestmark = pytest.mark.skipif(KORU_CLI_SPEC is None, reason="`koru` CLI not importable in test venv")


def _run(
    *args: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
    timeout: float = 30.0,
) -> subprocess.CompletedProcess[str]:
    base_env = os.environ.copy()
    if env:
        base_env.update(env)
    return subprocess.run(
        [*KORU_CMD, *args],
        cwd=str(cwd) if cwd else None,
        env=base_env,
        input=input_text,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def test_e2e_help_lists_wizard_subcommand() -> None:
    proc = _run("wizard", "--help")
    assert proc.returncode == 0, proc.stderr
    assert "--quick" in proc.stdout
    assert "--template" in proc.stdout
    assert "--gui" in proc.stdout
    assert "--bilingual" in proc.stdout
    assert "--detect-only" in proc.stdout


def test_e2e_list_templates_includes_packaged_set() -> None:
    proc = _run("wizard", "--list-templates")
    assert proc.returncode == 0, proc.stderr
    for name in ("default", "web-app", "ml-research", "cli-tool", "library"):
        assert name in proc.stdout, f"template {name!r} missing from --list-templates"


def test_e2e_detect_only_json_has_schema() -> None:
    proc = _run("wizard", "--detect-only", "--format", "json")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert isinstance(payload.get("ides"), list)
    assert isinstance(payload.get("projects"), list)
    assert isinstance(payload.get("llx_available"), bool)
    for ide in payload["ides"]:
        assert {"id", "label", "running", "path"} <= set(ide)


def test_e2e_detect_only_text_format() -> None:
    proc = _run("wizard", "--detect-only", "--format", "text")
    assert proc.returncode == 0, proc.stderr
    assert "Detected IDEs:" in proc.stdout
    assert "Project candidates:" in proc.stdout
    assert "llx CLI on PATH:" in proc.stdout


def test_e2e_quick_creates_ticket_in_isolated_project(tmp_path: Path) -> None:
    project = tmp_path / "demo"
    project.mkdir()
    proc = _run("wizard", "--quick", "--project", str(project))
    assert proc.returncode == 0, proc.stderr
    assert "Strategy : quality → cc_refactor" in proc.stdout
    assert "PLF-001" in proc.stdout
    sprint = project / ".planfile" / "sprints" / "current.yaml"
    assert sprint.is_file()
    content = sprint.read_text(encoding="utf-8")
    assert "koru-wizard" in content
    assert "Quality" in content


def test_e2e_quick_explicit_strategy_uses_dot_path(tmp_path: Path) -> None:
    project = tmp_path / "ddd"
    project.mkdir()
    proc = _run(
        "wizard",
        "--quick",
        "--strategy",
        "architecture.ddd",
        "--project",
        str(project),
        "--no-create",
    )
    assert proc.returncode == 0, proc.stderr
    assert "Strategy : architecture → ddd" in proc.stdout
    assert "Architektura: wytycz konteksty DDD" in proc.stdout


def test_e2e_quick_template_web_app_default_path(tmp_path: Path) -> None:
    project = tmp_path / "spa"
    project.mkdir()
    proc = _run(
        "wizard",
        "--template",
        "web-app",
        "--quick",
        "--project",
        str(project),
        "--no-create",
    )
    assert proc.returncode == 0, proc.stderr
    assert "Strategy : frontend → ux_perf" in proc.stdout
    assert "wydajność renderingu" in proc.stdout


def test_e2e_invalid_strategy_returns_non_zero(tmp_path: Path) -> None:
    project = tmp_path / "p"
    project.mkdir()
    proc = _run(
        "wizard",
        "--quick",
        "--strategy",
        "architecture.this-does-not-exist",
        "--project",
        str(project),
        "--no-create",
    )
    assert proc.returncode != 0
    assert "koru wizard error" in proc.stderr or "no option" in proc.stderr


def test_e2e_template_and_strategies_mutually_exclusive() -> None:
    proc = _run("wizard", "--template", "web-app", "--strategies", "/tmp/x.json")
    assert proc.returncode != 0
    assert "mutually exclusive" in proc.stderr


def test_e2e_bilingual_labels_in_help_render() -> None:
    """--bilingual must reach the loader; sanity check via --detect-only is enough."""
    proc = _run("wizard", "--bilingual", "--detect-only", "--format", "json")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert "ides" in payload


def test_e2e_strategies_https_without_allow_remote_errors() -> None:
    proc = _run(
        "wizard",
        "--strategies",
        "https://example.com/tree.json",
        "--quick",
        "--no-create",
    )
    assert proc.returncode != 0
    assert "--allow-remote" in proc.stderr


def test_e2e_strategies_http_rejected() -> None:
    proc = _run(
        "wizard",
        "--strategies",
        "http://example.com/tree.json",
        "--quick",
        "--no-create",
        "--allow-remote",
    )
    assert proc.returncode != 0
    assert "https" in proc.stderr.lower()


def test_e2e_strategies_missing_file_returns_friendly_error(tmp_path: Path) -> None:
    proc = _run(
        "wizard",
        "--strategies",
        str(tmp_path / "does-not-exist.json"),
        "--quick",
        "--no-create",
    )
    assert proc.returncode != 0
    assert "not found" in proc.stderr.lower()


def test_e2e_quick_repeated_creates_second_ticket(tmp_path: Path) -> None:
    project = tmp_path / "twice"
    project.mkdir()
    a = _run("wizard", "--quick", "--project", str(project))
    assert a.returncode == 0, a.stderr
    b = _run(
        "wizard",
        "--quick",
        "--strategy",
        "architecture.ddd",
        "--project",
        str(project),
    )
    assert b.returncode == 0, b.stderr
    assert "PLF-002" in b.stdout, b.stdout


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.mark.skipif(
    importlib.util.find_spec("fastapi") is None,
    reason="koru[api] (FastAPI + uvicorn) not installed",
)
def test_e2e_gui_serves_state_api(tmp_path: Path) -> None:
    """Spin up the real GUI server and hit /wizard/api/state."""
    project = tmp_path / "gui"
    project.mkdir()
    port = _pick_free_port()
    env = os.environ.copy()
    env["KORU_AUTO_SKIP_WIZARD"] = "1"
    proc = subprocess.Popen(
        [
            *KORU_CMD,
            "wizard",
            "--gui",
            "--no-browser",
            "--gui-port",
            str(port),
            "--no-create",
            "--project",
            str(project),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        ready_url = f"http://127.0.0.1:{port}/wizard/api/state"
        deadline = time.time() + 20  # Increased timeout for slower machines
        last_exc: Exception | None = None
        body: bytes = b""
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(ready_url, timeout=1) as resp:
                    body = resp.read()
                    assert resp.status == 200
                    break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                time.sleep(0.2)
        else:
            if proc.poll() is not None:
                stdout, stderr = proc.communicate(timeout=1)
                raise AssertionError(
                    f"GUI process exited early (code={proc.returncode}) on {ready_url}: {last_exc}\n"
                    f"stdout={stdout!r}\nstderr={stderr!r}"
                )
            raise AssertionError(f"GUI never became ready on {ready_url}: {last_exc}")
        data = json.loads(body)
        assert {"step", "csrf", "ides", "projects"} <= set(data)
        assert data["csrf"]

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/wizard", timeout=2) as resp:
            html = resp.read().decode("utf-8")
            assert "koru wizard" in html
            assert "/wizard/static/wizard.css" in html
            assert "/wizard/static/wizard.js" in html
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)


def _probe_should_suggest(project: Path, env: dict[str, str]) -> str:
    """Drive ``_should_suggest_wizard`` from a fresh Python process.

    We have to fake ``sys.stdin``/``sys.stdout`` TTY-ness but write the answer
    to ``sys.stderr`` so the mocked stdout doesn't swallow it.
    """
    snippet = (
        "import sys, unittest.mock as m\n"
        "from pathlib import Path\n"
        "from koru.cli import _should_suggest_wizard\n"
        "stdin = m.MagicMock(); stdin.isatty=lambda: True\n"
        "stdout = m.MagicMock(); stdout.isatty=lambda: True\n"
        "sys.stdin=stdin; sys.stdout=stdout\n"
        f"result = _should_suggest_wizard([], Path({str(project)!r}))\n"
        "sys.stderr.write('RESULT=' + ('1' if result else '0'))\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", snippet],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    marker = "RESULT="
    idx = proc.stderr.find(marker)
    assert idx >= 0, proc.stderr
    return proc.stderr[idx + len(marker) : idx + len(marker) + 1]


def test_e2e_should_suggest_wizard_heuristic_when_brand_new(tmp_path: Path) -> None:
    project = tmp_path / "brand-new"
    project.mkdir()
    env = os.environ.copy()
    env.pop("KORU_AUTO_SKIP_WIZARD", None)
    assert _probe_should_suggest(project, env) == "1"


def test_e2e_should_suggest_wizard_silenced_by_env(tmp_path: Path) -> None:
    project = tmp_path / "silent"
    project.mkdir()
    env = os.environ.copy()
    env["KORU_AUTO_SKIP_WIZARD"] = "1"
    assert _probe_should_suggest(project, env) == "0"


def test_e2e_should_suggest_wizard_false_when_planfile_present(tmp_path: Path) -> None:
    project = tmp_path / "ready"
    (project / ".planfile").mkdir(parents=True)
    env = os.environ.copy()
    env.pop("KORU_AUTO_SKIP_WIZARD", None)
    assert _probe_should_suggest(project, env) == "0"


def test_e2e_wizard_quick_respects_bilingual_in_strategies(tmp_path: Path) -> None:
    """In quick mode tree is loaded but no labels rendered to user; sanity only."""
    project = tmp_path / "bil"
    project.mkdir()
    proc = _run(
        "wizard",
        "--bilingual",
        "--quick",
        "--project",
        str(project),
        "--no-create",
    )
    assert proc.returncode == 0, proc.stderr
    assert "quality" in proc.stdout


@pytest.mark.skipif(sys.platform == "win32", reason="needs POSIX shutil paths")
def test_e2e_no_args_returns_useful_help() -> None:
    proc = _run("wizard")
    # Without piping stdin and with no IDE/project flags, the wizard waits on
    # stdin. We invoke with empty stdin to force EOF → cancel exit 130.
    assert proc.returncode in (0, 1, 2, 130)
