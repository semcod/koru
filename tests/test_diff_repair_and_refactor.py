"""Unit tests for diff repair, SEARCH/REPLACE synthesis, governed workspace support,
scan artifact filtering, refactor context slicing, and verify gate auto-detection.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from koru.queue.context_files import _context_files_to_include, _is_readonly_scan_artifact
from koru.queue.context_slicing import (
    _extract_prompt_symbols,
    _extract_symbol_from_corpus,
    slice_file_content,
)
from koru.queue.diff_repair import (
    _repair_missing_file_headers,
    _sanitize_inner_headers,
    extract_unified_diff,
    synthesize_diff_from_search_replace,
)
from koru.queue.patch_mode import wrap_reply_in_proposal_envelope
from koru.queue.patch_retry import _filter_readonly_scan_artifacts
from koru.queue.transaction.preflight import extract_patch
from koru.queue.verify.legacy import resolve_legacy_verify_command
from koru.queue.workspace import (
    _is_admitted_ticket_worktree,
    _worktree_location,
    require_unmanaged_patch_workspace,
)
from koru.scan_artifacts import (
    _parse_dup_suggestions,
    _parse_duplication_toon_suggestions,
    _parse_god_module_suggestions,
    _parse_high_cc_suggestions,
    _parse_layer_hotspot_suggestions,
    _parse_refactor_suggestions,
    _scan_duplication_toon,
)


def _git(repo: Path, *args: str) -> str:
    res = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return res.stdout


def _init_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    return tmp_path


class TestSearchReplaceSynthesis:
    def test_single_and_multi_file_search_replace_and_new_file(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path)
        (repo / "src").mkdir()
        (repo / "src" / "alpha.py").write_text(
            "def greet():\n    return 'hello'\n\ndef bye():\n    return 'bye'\n",
            encoding="utf-8",
        )
        (repo / "src" / "beta.py").write_text(
            "VALUE = 1\nOTHER = 2\n",
            encoding="utf-8",
        )
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "init")

        llm_reply = """Here are the requested changes:

### FILE: src/alpha.py
<<<<<<< SEARCH
def greet():
    return 'hello'
=======
def greet():
    return 'hello world'
>>>>>>> REPLACE

### FILE: src/beta.py
<<<<<<< SEARCH
VALUE = 1
=======
VALUE = 42
>>>>>>> REPLACE

### FILE: src/new_helper.py
```python
def helper() -> int:
    return 99
```
"""
        diff = synthesize_diff_from_search_replace(
            llm_reply,
            repo,
            known_files=["src/alpha.py", "src/beta.py"],
        )
        assert "diff --git a/src/alpha.py b/src/alpha.py" in diff
        assert "diff --git a/src/beta.py b/src/beta.py" in diff
        assert "diff --git a/src/new_helper.py b/src/new_helper.py" in diff
        assert "--- /dev/null" in diff
        assert "+++ b/src/new_helper.py" in diff

        # Verify git apply --check succeeds on the synthesized diff
        proc = subprocess.run(
            ["git", "apply", "--check"],
            cwd=repo,
            input=diff,
            text=True,
            capture_output=True,
        )
        assert proc.returncode == 0, proc.stderr

    def test_wrap_and_extract_patch_uses_search_replace_fallback(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path)
        (repo / "mod.py").write_text("x = 10\ny = 20\n", encoding="utf-8")

        reply = (
            "mod.py\n"
            "<<<<<<< SEARCH\n"
            "x = 10\n"
            "=======\n"
            "x = 100\n"
            ">>>>>>> REPLACE\n"
        )
        res = SimpleNamespace(returncode=0, stdout=reply, stderr="")
        wrapped = wrap_reply_in_proposal_envelope(
            res, "Update mod.py", project=repo, known_files=["mod.py"]
        )
        patch, _bindings, refusal = extract_patch(wrapped, project=repo, known_files=["mod.py"])
        assert refusal is None
        assert patch is not None
        assert "--- a/mod.py" in patch
        assert "+++ b/mod.py" in patch
        assert "-x = 10" in patch
        assert "+x = 100" in patch


class TestFuzzyDiffRepairAndSanitization:
    def test_fuzzy_hunk_repair_fixes_wrong_line_numbers_and_bad_context(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path)
        (repo / "app.py").write_text(
            "# header 1\n# header 2\ndef compute(a, b):\n    total = a + b\n    return total\n",
            encoding="utf-8",
        )
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "init")

        # Hunk has wrong line numbers (@@ -50,3 +50,3 @@) and slightly drifted context
        broken_diff = (
            "```diff\n"
            "--- a/app.py\n"
            "+++ b/app.py\n"
            "@@ -50,3 +50,3 @@\n"
            " def compute(a, b):\n"
            "-    total = a + b\n"
            "+    total = a * b\n"
            "     return total\n"
            "```\n"
            "Explanation after fence that should be stripped.\n"
        )
        repaired = extract_unified_diff(broken_diff, project=repo, known_files=["app.py"])
        assert "Explanation after fence" not in repaired
        proc = subprocess.run(
            ["git", "apply", "--check"],
            cwd=repo,
            input=repaired,
            text=True,
            capture_output=True,
        )
        assert proc.returncode == 0, f"git apply failed: {proc.stderr}\nRepaired diff:\n{repaired}"

    def test_repair_missing_file_headers_new_and_deleted_files(self) -> None:
        new_file_lines = [
            "diff --git a/added.py b/added.py",
            "new file mode 100644",
            "@@ -0,0 +1,2 @@",
            "+x = 1",
            "+y = 2",
        ]
        repaired_new = _repair_missing_file_headers(new_file_lines)
        assert "--- /dev/null" in repaired_new
        assert "+++ b/added.py" in repaired_new

        del_file_lines = [
            "diff --git a/gone.py b/gone.py",
            "deleted file mode 100644",
            "@@ -1,2 +0,0 @@",
            "-x = 1",
            "-y = 2",
        ]
        repaired_del = _repair_missing_file_headers(del_file_lines)
        assert "--- a/gone.py" in repaired_del
        assert "+++ /dev/null" in repaired_del

    def test_sanitize_inner_headers_preserves_removed_triple_dash_content(self) -> None:
        raw_lines = [
            "--- a/query.sql",
            "+++ b/query.sql",
            "@@ -1,3 +1,3 @@",
            "--- a/query.sql",
            "+++ b/query.sql",
            " SELECT 1;",
            "--- comment line to remove",
            "+-- updated comment line",
            " SELECT 2;",
            "```",
            "Some trailing prose from the model.",
        ]
        lines = _sanitize_inner_headers(raw_lines)
        # Outer header kept, inner duplicate --- a/query.sql stripped, content --- comment kept
        assert lines.count("--- a/query.sql") == 1
        assert lines.count("+++ b/query.sql") == 1
        assert "--- comment line to remove" in lines
        assert "Some trailing prose from the model." not in lines

    def test_merge_multiple_diff_sections_for_same_file_and_subblock_fallback(
        self, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        target = tmp_path / "examples" / "composite_gates.py"
        target.parent.mkdir(parents=True)
        original = (
            '"""Composite gates example."""\n'
            "import os\n\n"
            "def first_gate(score: float) -> bool:\n"
            "    return score >= 85.0\n\n"
            "def second_gate(penalty: float) -> float:\n"
            "    return penalty * 0.25\n"
        )
        target.write_text(original, encoding="utf-8")

        # Model emits multiple separate diff --git sections for the same file,
        # each claiming @@ -1,3 +1,3 @@ and bundling non-contiguous edits.
        raw_reply = (
            "```diff\n"
            "diff --git a/examples/composite_gates.py b/examples/composite_gates.py\n"
            "--- a/examples/composite_gates.py\n"
            "+++ b/examples/composite_gates.py\n"
            "@@ -1,3 +1,4 @@\n"
            " import os\n"
            "+MIN_PASS_SCORE = 85.0\n"
            "-    return score >= 85.0\n"
            "+    return score >= MIN_PASS_SCORE\n"
            "```\n\n"
            "```diff\n"
            "diff --git a/examples/composite_gates.py b/examples/composite_gates.py\n"
            "--- a/examples/composite_gates.py\n"
            "+++ b/examples/composite_gates.py\n"
            "@@ -1,3 +1,4 @@\n"
            " import os\n"
            "+PENALTY_FACTOR = 0.25\n"
            "-    return penalty * 0.25\n"
            "+    return penalty * PENALTY_FACTOR\n"
            "```\n"
        )
        repaired = extract_unified_diff(
            raw_reply,
            project=tmp_path,
            known_files=["examples/composite_gates.py"],
        )
        assert repaired is not None
        assert repaired.count("diff --git a/examples/composite_gates.py b/examples/composite_gates.py") == 1
        from koru.queue.workspace import diff_target_files

        assert diff_target_files(tmp_path, repaired) == ("examples/composite_gates.py",)
        proc = subprocess.run(
            ["git", "apply", "--check", "-"],
            input=repaired,
            text=True,
            cwd=tmp_path,
            capture_output=True,
            check=False,
        )
        assert proc.returncode == 0, f"git apply --check failed: {proc.stderr}\n{repaired}"

    def test_full_file_fence_fallback_for_single_known_file(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        target = tmp_path / "src" / "calc.py"
        target.parent.mkdir(parents=True)
        target.write_text(
            "def compute_total(value: int) -> int:\n"
            "    multiplier = 42\n"
            "    offset = 10\n"
            "    return value * multiplier + offset\n",
            encoding="utf-8",
        )
        reply = (
            "Here is the updated file with named constants:\n"
            "```python\n"
            "DEFAULT_MULTIPLIER = 42\n"
            "DEFAULT_OFFSET = 10\n\n"
            "def compute_total(value: int) -> int:\n"
            "    multiplier = DEFAULT_MULTIPLIER\n"
            "    offset = DEFAULT_OFFSET\n"
            "    return value * multiplier + offset\n"
            "```\n"
        )
        repaired = extract_unified_diff(reply, project=tmp_path, known_files=["src/calc.py"])
        assert repaired is not None
        assert "+DEFAULT_MULTIPLIER = 42" in repaired
        proc = subprocess.run(
            ["git", "apply", "--check", "-"],
            input=repaired,
            text=True,
            cwd=tmp_path,
            capture_output=True,
            check=False,
        )
        assert proc.returncode == 0, f"git apply --check failed: {proc.stderr}\n{repaired}"


class TestGovernedWorkspaceSupport:
    def test_admitted_ticket_worktree_accepted_via_intent_json_or_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        worktree = tmp_path / ".worktrees" / "ticket-450--example"
        ticket_dir = worktree / "project" / "ticket-450"
        ticket_dir.mkdir(parents=True)
        _init_repo(worktree)
        (ticket_dir / "intent.json").write_text('{"ticketId": "ticket-450"}', encoding="utf-8")

        assert _is_admitted_ticket_worktree(worktree) is True
        # Should not raise even when workspace_policy.yaml is present
        (worktree / ".governance").mkdir(parents=True)
        (worktree / ".governance" / "workspace_policy.yaml").write_text(
            "schema_version: '1'\n", encoding="utf-8"
        )
        require_unmanaged_patch_workspace(worktree)

        # Also test env var override on arbitrary path
        other = tmp_path / "custom_checkout"
        other.mkdir()
        _init_repo(other)
        (other / ".governance").mkdir()
        (other / ".governance" / "workspace_policy.yaml").write_text(
            "schema_version: '1'\n", encoding="utf-8"
        )
        monkeypatch.setenv("KORU_GOVERNED_WORKTREE_OK", "1")
        assert _is_admitted_ticket_worktree(other) is True
        require_unmanaged_patch_workspace(other)

    def test_worktree_location_uses_in_repo_worktrees_ticket_prefix(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("KORU_QUEUE_WORKTREE_DIR", raising=False)
        loc = _worktree_location(tmp_path, "readiness")
        assert loc == tmp_path / ".worktrees" / "ticket-readiness"

        loc_prefixed = _worktree_location(tmp_path, "ticket-123")
        assert loc_prefixed == tmp_path / ".worktrees" / "ticket-123"


class TestScanArtifactFilteringAndDuplicationToon:
    def test_suggestions_exclude_scan_artifact_paths(self) -> None:
        toon_text = (
            "HEALTH\n"
            "  🔴 GOD src/big.py = 900L, 4 classes, 35m\n"
            "  🔴 DUP 3 duplicate class groups\n"
            "  🟡 CC do_work CC=25 (limit: 15)\n"
            "REFACTOR\n"
            "  1. Split handler in src/h.py (impact=high)\n"
            "LAYERS\n"
            "  │ !! core 600L 3C 25m CC=18.5\n"
        )
        rel = "project/analysis.toon.yaml"
        all_suggestions = (
            _parse_god_module_suggestions(toon_text, rel)
            + _parse_dup_suggestions(toon_text, rel)
            + _parse_high_cc_suggestions(toon_text, rel, locations={"do_work": ["src/complex.py:10"]})
            + _parse_refactor_suggestions(toon_text, rel)
            + _parse_layer_hotspot_suggestions(toon_text, rel, module_paths={"core": "src/core.py"})
        )
        assert len(all_suggestions) == 5
        for sug in all_suggestions:
            assert rel not in sug.files
            assert all(not _is_readonly_scan_artifact(f) for f in sug.files)

    def test_duplication_toon_parsing_and_filtering(self, tmp_path: Path) -> None:
        dup_dir = tmp_path / "project"
        dup_dir.mkdir()
        dup_file = dup_dir / "duplication.toon.yaml"
        dup_file.write_text(
            "duplication_groups:\n"
            "  - lines: 30\n"
            "    locations:\n"
            "      - file: src/one.py\n"
            "        start: 5\n"
            "        end: 35\n"
            "      - file: src/two.py\n"
            "        start: 10\n"
            "        end: 40\n",
            encoding="utf-8",
        )
        suggestions = _scan_duplication_toon(tmp_path)
        assert len(suggestions) == 1
        assert list(suggestions[0].files) == ["src/one.py", "src/two.py"]
        assert "project/duplication.toon.yaml" not in suggestions[0].files

        # Also test top-level clusters key
        clusters_sugs = _parse_duplication_toon_suggestions(
            {"clusters": [{"lines": 20, "files": ["src/x.py", "src/y.py"]}]},
            "project/duplication.toon.yaml",
        )
        assert len(clusters_sugs) == 1
        assert list(clusters_sugs[0].files) == ["src/x.py", "src/y.py"]

    def test_context_files_and_patch_retry_filter_readonly_artifacts(self, tmp_path: Path) -> None:
        (tmp_path / "project").mkdir()
        (tmp_path / "project" / "analysis.toon.yaml").write_text("health: {}\n", encoding="utf-8")
        (tmp_path / "project" / "duplication.toon.yaml").write_text("clusters: []\n", encoding="utf-8")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "real.py").write_text("x = 1\n", encoding="utf-8")

        request = {
            "prompt": "Refactor src/real.py",
            "ticket_files": [
                "src/real.py",
                "project/analysis.toon.yaml",
                "project/duplication.toon.yaml",
            ],
            "context_files": [
                "project/analysis.toon.yaml",
                "project/duplication.toon.yaml",
            ],
        }
        included = _context_files_to_include(tmp_path, request)
        assert included == ["src/real.py"]

        filtered = _filter_readonly_scan_artifacts(
            ["src/real.py", "project/analysis.toon.yaml", "project/duplication.toon.yaml", "calls.yaml"]
        )
        assert list(filtered) == ["src/real.py"]

        prompt_only = _context_files_to_include(
            tmp_path,
            {"prompt": "Resolve 2 unused-imports issues in src/real.py and project/analysis.toon.yaml"},
        )
        assert prompt_only == ["src/real.py"]



class TestContextSlicingStopwordsAndRefactorBypass:
    def test_stopwords_ignored_when_extracting_symbols(self) -> None:
        prompt = "Split the god module and refactor high cyclomatic complexity into clean helpers"
        assert _extract_symbol_from_corpus(prompt) is None
        assert _extract_prompt_symbols(prompt) == []

    def test_slice_file_content_retains_full_module_on_refactor_prompt(self) -> None:
        lines = [f"def func_{i}():\n    return {i}\n" for i in range(600)]
        content = "\n".join(lines)
        assert 12_000 < len(content) < 64_000

        sliced = slice_file_content(
            "src/big_module.py",
            content,
            "Split god module src/big_module.py (650 lines) into focused sub-modules",
            max_chars=64_000,
        )
        assert sliced == content
        assert "# ... [" not in sliced


class TestVerifyAutoDetection:
    def test_auto_detects_pytest_and_venv_pytest(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
        assert resolve_legacy_verify_command(tmp_path, {}) == "pytest -q"

        venv_bin = tmp_path / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        venv_pytest = venv_bin / "pytest"
        venv_pytest.write_text("#!/bin/sh\n", encoding="utf-8")
        assert resolve_legacy_verify_command(tmp_path, {}) == f"{venv_pytest} -q"

    def test_auto_detects_cargo_and_npm(self, tmp_path: Path) -> None:
        rust_dir = tmp_path / "rust_proj"
        rust_dir.mkdir()
        (rust_dir / "Cargo.toml").write_text("[package]\nname = 'demo'\n", encoding="utf-8")
        assert resolve_legacy_verify_command(rust_dir, {}) == "cargo test --locked"

        node_dir = tmp_path / "node_proj"
        node_dir.mkdir()
        (node_dir / "package.json").write_text('{"name": "demo"}\n', encoding="utf-8")
        assert resolve_legacy_verify_command(node_dir, {}) == "npm test"

    def test_skips_unrunnable_koru_yaml_task_command_without_taskfile_or_target(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.delenv("KORU_QUEUE_VERIFY_COMMAND", raising=False)
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
        (tmp_path / "koru.yaml").write_text(
            "when:\n  before_complete_ticket:\n    commands:\n      - task quality:regix:local\n",
            encoding="utf-8",
        )
        # No Taskfile.yml -> falls back to auto-detected pytest -q
        assert resolve_legacy_verify_command(tmp_path, {}) == "pytest -q"

        # Taskfile.yml exists but lacks quality:regix:local target -> still falls back to pytest -q
        (tmp_path / "Taskfile.yml").write_text("version: '3'\ntasks:\n  test:\n    cmds: [pytest]\n", encoding="utf-8")
        assert resolve_legacy_verify_command(tmp_path, {}) == "pytest -q"

        # Taskfile.yml defines quality:regix:local -> honours koru.yaml command
        (tmp_path / "Taskfile.yml").write_text(
            "version: '3'\ntasks:\n  quality:regix:local:\n    cmds: [regix]\n",
            encoding="utf-8",
        )
        assert resolve_legacy_verify_command(tmp_path, {}) == "task quality:regix:local"



class TestScreenPatchQualityGate:
    def test_refuses_destructive_truncation_of_public_symbols(self, tmp_path: Path) -> None:
        from koru.queue.transaction.preflight import (
            PATCH_DESTRUCTIVE_TRUNCATION,
            screen_patch_quality,
        )

        diff = (
            "--- a/src/service.py\n"
            "+++ b/src/service.py\n"
            "@@ -1,10 +1,2 @@\n"
            "-def alpha():\n"
            "-    return 1\n"
            "-def beta():\n"
            "-    return 2\n"
            "-def gamma():\n"
            "-    return 3\n"
            "+def alpha():\n"
            "+    return 10\n"
            "-def delta():\n"
            "-    return 4\n"
        )
        outcome = screen_patch_quality(tmp_path, {"title": "Fix alpha return value"}, diff)
        assert outcome is not None
        assert outcome.code == PATCH_DESTRUCTIVE_TRUNCATION
        assert outcome.retryable is True
        assert "beta" in outcome.message

        # Allowed when ticket explicitly asks to split/extract
        allowed = screen_patch_quality(tmp_path, {"title": "Split and extract helpers from service.py"}, diff)
        assert allowed is None

    def test_refuses_sqlite_connect_without_closing_and_loop_subprocess(self, tmp_path: Path) -> None:
        from koru.queue.transaction.preflight import (
            PATCH_INTRODUCES_ANTIPATTERN,
            screen_patch_quality,
        )

        sqlite_diff = (
            "--- a/src/store.py\n"
            "+++ b/src/store.py\n"
            "@@ -1,2 +1,4 @@\n"
            " def save(db_path):\n"
            "+    with sqlite3.connect(db_path) as conn:\n"
            "+        conn.execute('SELECT 1')\n"
        )
        outcome = screen_patch_quality(tmp_path, {"title": "Update save"}, sqlite_diff)
        assert outcome is not None
        assert outcome.code == PATCH_INTRODUCES_ANTIPATTERN
        assert "PERF-AUDIT-SQLITE-002" in outcome.message

        # Wrapped in closing() passes cleanly
        safe_sqlite_diff = (
            "--- a/src/store.py\n"
            "+++ b/src/store.py\n"
            "@@ -1,2 +1,4 @@\n"
            " def save(db_path):\n"
            "+    with closing(sqlite3.connect(db_path)) as conn:\n"
            "+        conn.execute('SELECT 1')\n"
        )
        assert screen_patch_quality(tmp_path, {"title": "Update save"}, safe_sqlite_diff) is None

        # Subprocess inside loop is flagged
        loop_subproc_diff = (
            "--- a/src/runner.py\n"
            "+++ b/src/runner.py\n"
            "@@ -1,2 +1,4 @@\n"
            " def check_repos(repos):\n"
            "+    for repo in repos:\n"
            "+        subprocess.run(['git', '-C', str(repo), 'status'])\n"
        )
        outcome2 = screen_patch_quality(tmp_path, {"title": "Check repos"}, loop_subproc_diff)
        assert outcome2 is not None
        assert outcome2.code == PATCH_INTRODUCES_ANTIPATTERN
        assert "PERF-AUDIT" in outcome2.message


class TestVerifyFailureReflexionAndLessonLedger:
    def test_verify_failure_reflexion_retries_and_records_self_repaired_lesson(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from koru.queue.patch_retry import (
            apply_patch_with_retry,
            format_lessons_for_prompt,
            load_project_lessons,
        )

        monkeypatch.setenv("KORU_GOVERNED_WORKTREE_OK", "1")
        _init_repo(tmp_path)
        (tmp_path / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
        _git(tmp_path, "add", "calc.py")
        _git(tmp_path, "commit", "-m", "initial")

        bad_diff = (
            "diff --git a/calc.py b/calc.py\n"
            "--- a/calc.py\n"
            "+++ b/calc.py\n"
            "@@ -1,2 +1,2 @@\n"
            " def add(a, b):\n"
            "-    return a - b\n"
            "+    return a * b\n"
        )
        good_diff = (
            "diff --git a/calc.py b/calc.py\n"
            "--- a/calc.py\n"
            "+++ b/calc.py\n"
            "@@ -1,2 +1,2 @@\n"
            " def add(a, b):\n"
            "-    return a - b\n"
            "+    return a + b\n"
        )

        retry_prompts: list[str] = []

        def fake_llm(action: dict, proj: Path):
            retry_prompts.append(str(action.get("prompt") or ""))
            return SimpleNamespace(returncode=0, stdout=good_diff, stderr="")

        def fake_verify(cmd: str, cwd: Path):
            body = (cwd / "calc.py").read_text(encoding="utf-8")
            if "a * b" in body:
                return SimpleNamespace(
                    returncode=1,
                    stdout="",
                    stderr="AssertionError: expected add(2, 3) == 5, got 6\n",
                )
            return SimpleNamespace(returncode=0, stdout="1 passed\n", stderr="")

        ticket = {
            "id": "T-REFLEX-1",
            "title": "Fix add function",
            "files": ["calc.py"],
            "inputs": {
                "verify_command": "pytest -q",
                "max_verify_retries": 1,
                "promotion_mode": "apply",
            },
        }
        initial_reply = SimpleNamespace(returncode=0, stdout=bad_diff, stderr="")

        _res, outcome, bundle = apply_patch_with_retry(
            tmp_path,
            initial_reply,
            ticket,
            {"prompt": "Fix add(a, b) in calc.py"},
            fake_llm,
            fake_verify,
        )
        assert outcome is None
        assert bundle is not None
        assert bundle["verdict"] == "verified"
        assert len(bundle["patch_attempts"]) == 2
        assert bundle["patch_attempts"][0]["outcome"].startswith("verify_failed")
        assert bundle["patch_attempts"][0]["retryable"] is True
        assert bundle["patch_attempts"][1]["outcome"] == "landed"
        assert len(retry_prompts) == 1
        assert "Reflexion" in retry_prompts[0]
        assert "AssertionError: expected add(2, 3) == 5" in retry_prompts[0]
        assert "+    return a * b" in retry_prompts[0]

        # Verify that a self-repaired lesson was persisted to .koru/lessons.jsonl
        lessons = load_project_lessons(tmp_path, ticket_id="T-REFLEX-1", target_files=["calc.py"])
        assert len(lessons) == 1
        assert lessons[0]["self_repaired"] is True
        assert "calc.py" in lessons[0]["target_files"]

        prompt_section = format_lessons_for_prompt(tmp_path, target_files=["calc.py"])
        assert "Learned Constraints from Previous Runs" in prompt_section
        assert "Recovered after initial" in prompt_section

    def test_new_file_diff_repair_and_enveloped_pin_base(self, tmp_path: Path) -> None:
        import hashlib

        from koru.queue.patch_retry import _pin_base

        repo = _init_repo(tmp_path)
        (repo / "README.md").write_text("# Demo\n", encoding="utf-8")
        _git(repo, "add", "README.md")
        _git(repo, "commit", "-m", "init")

        variants = [
            (
                "diff --git a/LICENSE b/LICENSE\n"
                "--- a/LICENSE\n"
                "+++ b/LICENSE\n"
                "@@ -1,0 +1,3 @@\n"
                "+MIT License\n"
                "\n"
                "+Copyright (c) 2026\n"
            ),
            (
                "--- /dev/null\n"
                "+++ b/LICENSE\n"
                "@@ -0,0 +1,3 @@\n"
                "+MIT License\n"
                "\n"
                "+Copyright (c) 2026\n"
            ),
            (
                "Here is the license file:\n"
                "```text\n"
                "MIT License\n\n"
                "Copyright (c) 2026 Demo\n"
                "Permission is hereby granted.\n"
                "```\n"
            ),
        ]
        for raw in variants:
            repaired = extract_unified_diff(raw, project=repo, known_files=["LICENSE"])
            assert repaired is not None
            assert "new file mode 100644" in repaired
            assert "--- /dev/null" in repaired
            assert "+++ b/LICENSE" in repaired
            proc = subprocess.run(
                ["git", "apply", "--check"],
                cwd=repo,
                input=repaired,
                text=True,
                capture_output=True,
            )
            assert proc.returncode == 0, f"git apply failed: {proc.stderr}\n{repaired}"

        enveloped = wrap_reply_in_proposal_envelope(
            SimpleNamespace(returncode=0, stdout=variants[0], stderr=""),
            "Create LICENSE",
            project=repo,
            known_files=["LICENSE"],
        )
        manifest = _pin_base(
            repo,
            {"id": "T-LIC-1", "files": ["LICENSE"]},
            enveloped,
            budget=1,
            run_id="run123",
        )
        empty_sha = hashlib.sha256(b"").hexdigest()
        assert manifest["patch_sha256"] != empty_sha
        assert "LICENSE" in manifest["touched_files"]


