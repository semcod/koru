"""Integration and benchmark tests for the native Rust scan_todo engine."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from koru.scan_todo import (
    DEFAULT_SCAN_EXCLUDES,
    count_todo_markers,
    count_todo_markers_in_project,
)

CARGO_MANIFEST = Path(__file__).resolve().parent.parent / "packages" / "koru-scan-todo" / "Cargo.toml"
RUST_BIN = Path(__file__).resolve().parent.parent / "packages" / "koru-scan-todo" / "target" / "release" / "koru-scan-todo"


@pytest.fixture(scope="module")
def ensure_rust_binary() -> Path:
    """Ensure release binary of koru-scan-todo is compiled and available."""
    if not RUST_BIN.is_file() or not shutil.which("cargo"):
        subprocess.run(
            ["cargo", "build", "--release", "--manifest-path", str(CARGO_MANIFEST)],
            check=True,
            capture_output=True,
            text=True,
        )
    assert RUST_BIN.is_file(), f"Binary not found at {RUST_BIN}"
    return RUST_BIN


def test_rust_binary_help(ensure_rust_binary: Path) -> None:
    """Test CLI help output."""
    res = subprocess.run(
        [str(ensure_rust_binary), "--help"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert "Usage: koru-scan-todo" in res.stderr or "Usage: koru-scan-todo" in res.stdout


def test_rust_binary_output_contract(ensure_rust_binary: Path, tmp_path: Path) -> None:
    """Verify JSON structure produced by the Rust scanner matches expected schema."""
    sub = tmp_path / "sub"
    sub.mkdir()
    f1 = sub / "module_a.py"
    f1.write_text(
        "# TODO: implement feature\n"
        "# FIXME: bug in parser\n"
        "# XXX: needs audit\n"
        "x = 'TODO: not a comment'\n",
        encoding="utf-8",
    )
    f2 = sub / "module_b.py"
    f2.write_text(
        "\"\"\"Docstring with TODO: ignore me\"\"\"\n"
        "# HACK: fast path\n",
        encoding="utf-8",
    )

    res = subprocess.run(
        [str(ensure_rust_binary), str(tmp_path), "--min", "1", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(res.stdout)
    assert "totalMarkers" in data
    assert "matchingFiles" in data
    assert "elapsedMs" in data
    assert "files" in data
    assert data["matchingFiles"] == 2
    assert data["totalMarkers"] == 4
    assert data["files"].get("sub/module_a.py") == 3
    assert data["files"].get("sub/module_b.py") == 1


def test_rust_and_python_exact_match(ensure_rust_binary: Path, tmp_path: Path) -> None:
    """Verify Python and Rust scanning logic yield identical file marker counts."""
    pkg = tmp_path / "pkg"
    pkg.mkdir()

    # Create several test files with comments, strings, multiline strings
    (pkg / "test1.py").write_text(
        "# TODO: marker 1\n"
        "# FIXME: marker 2\n"
        "# HACK: marker 3\n"
        "s = '''\n# TODO: multiline string not a comment\n'''\n",
        encoding="utf-8",
    )
    (pkg / "test2.py").write_text(
        "# Regular comment\n"
        "def f():\n"
        "    # XXX: marker 4\n"
        "    return 42\n",
        encoding="utf-8",
    )
    (pkg / "test3.py").write_text(
        "# Clean file without markers\n",
        encoding="utf-8",
    )

    py_counts = count_todo_markers_in_project(tmp_path, min_per_file=1)

    res = subprocess.run(
        [str(ensure_rust_binary), str(tmp_path), "--min", "1", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    rust_data = json.loads(res.stdout)
    rust_counts = rust_data["files"]

    assert dict(py_counts) == rust_counts


def test_rust_koruignore_filtering(ensure_rust_binary: Path, tmp_path: Path) -> None:
    """Verify that .koruignore rules are respected by the native scanner."""
    (tmp_path / ".koruignore").write_text(
        "ignored_dir/\n"
        "*.ignore.py\n",
        encoding="utf-8",
    )
    ignored_dir = tmp_path / "ignored_dir"
    ignored_dir.mkdir()
    (ignored_dir / "foo.py").write_text("# TODO: ignored 1\n# TODO: ignored 2\n", encoding="utf-8")

    (tmp_path / "bar.ignore.py").write_text("# TODO: ignored 3\n", encoding="utf-8")

    kept_dir = tmp_path / "kept"
    kept_dir.mkdir()
    (kept_dir / "clean.py").write_text("# TODO: kept\n", encoding="utf-8")

    res = subprocess.run(
        [str(ensure_rust_binary), str(tmp_path), "--min", "1", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(res.stdout)
    assert data["matchingFiles"] == 1
    assert "kept/clean.py" in data["files"]
    assert "ignored_dir/foo.py" not in data["files"]
    assert "bar.ignore.py" not in data["files"]


def test_rust_benchmark_execution(ensure_rust_binary: Path) -> None:
    """Benchmark test verifying native Rust engine runs fast on the src tree."""
    src_dir = Path(__file__).resolve().parent.parent / "src"

    start_rust = time.perf_counter()
    res = subprocess.run(
        [str(ensure_rust_binary), str(src_dir), "--min", "1", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    rust_duration = time.perf_counter() - start_rust

    rust_data = json.loads(res.stdout)
    assert isinstance(rust_data["elapsedMs"], (int, float))
    assert rust_duration < 1.0, f"Rust scanning took too long: {rust_duration:.2f}s"
