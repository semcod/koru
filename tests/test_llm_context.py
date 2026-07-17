"""Tests for project context assembly in executor.kind=llm tickets.

Covers:
- context assembly (build_project_context)
- secret filtering
- file tree generation
- context injection into LLM messages
- context-enriched end-to-end queue run
- regression: prompt-only tickets continue to work unchanged
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from koru.queue import run_next_planfile_task
from koru.queue.context import (
    DEFAULT_MAX_CONTEXT_CHARS,
    ContextResult,
    _is_excluded,
    build_project_context,
)
from koru.queue.runners import _build_llm_messages
from koru.queue.ticket import ticket_llm_request

# ---------------------------------------------------------------------------
# Helpers shared across tests
# ---------------------------------------------------------------------------


def _ok(stdout: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=0, stdout=stdout, stderr="")


def _ticket_args(command: list[str]) -> list[str]:
    ticket_index = command.index("ticket")
    return command[ticket_index:]


def _llm_ticket(**overrides) -> dict:
    ticket: dict = {
        "id": "CTX-001",
        "name": "Analyse this PHP and Docker project",
        "executor": {"kind": "llm", "mode": "automatic"},
        "inputs": {
            "prompt": "Describe the architecture of this project.",
            "llm_model": "openai/gpt-4o-mini",
        },
    }
    ticket.update(overrides)
    return ticket


# ---------------------------------------------------------------------------
# _is_excluded — security filtering unit tests
# ---------------------------------------------------------------------------


class TestIsExcluded(unittest.TestCase):

    def test_env_file_excluded(self):
        self.assertTrue(_is_excluded(".env"))

    def test_env_variant_excluded(self):
        self.assertTrue(_is_excluded(".env.production"))

    def test_private_key_excluded(self):
        self.assertTrue(_is_excluded("secrets/private.key"))
        self.assertTrue(_is_excluded("server.pem"))
        self.assertTrue(_is_excluded("cert.p12"))

    def test_git_dir_excluded(self):
        self.assertTrue(_is_excluded(".git"))
        self.assertTrue(_is_excluded(".git/config"))

    def test_node_modules_excluded(self):
        self.assertTrue(_is_excluded("node_modules"))
        self.assertTrue(_is_excluded("node_modules/express/index.js"))

    def test_vendor_excluded(self):
        self.assertTrue(_is_excluded("vendor/bundle/ruby"))

    def test_pycache_excluded(self):
        self.assertTrue(_is_excluded("src/__pycache__/foo.cpython-311.pyc"))

    def test_venv_excluded(self):
        self.assertTrue(_is_excluded(".venv/lib/python3.11/site-packages/foo.py"))
        self.assertTrue(_is_excluded("venv/bin/python"))

    def test_lock_files_excluded(self):
        self.assertTrue(_is_excluded("uv.lock"))
        self.assertTrue(_is_excluded("poetry.lock"))
        self.assertTrue(_is_excluded("Gemfile.lock"))
        # package-lock.json ends with .json (not .lock), so it is NOT excluded by default
        self.assertFalse(_is_excluded("package-lock.json"))

    def test_binary_files_excluded(self):
        self.assertTrue(_is_excluded("lib.so"))
        self.assertTrue(_is_excluded("app.exe"))
        self.assertTrue(_is_excluded("archive.tar.gz"))

    def test_normal_source_files_not_excluded(self):
        self.assertFalse(_is_excluded("src/app.py"))
        self.assertFalse(_is_excluded("Dockerfile"))
        self.assertFalse(_is_excluded("README.md"))
        self.assertFalse(_is_excluded("koru.yaml"))
        self.assertFalse(_is_excluded("docker-compose.yml"))
        self.assertFalse(_is_excluded("pyproject.toml"))
        self.assertFalse(_is_excluded("src/koru/queue/runner.py"))


# ---------------------------------------------------------------------------
# build_project_context — unit tests
# ---------------------------------------------------------------------------


class TestBuildProjectContext(unittest.TestCase):

    def test_returns_none_when_nothing_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            request = {"prompt": "hello", "model": "openai/gpt-4o-mini"}
            result = build_project_context(project, request)
            self.assertIsNone(result)

    def test_include_project_context_true_returns_context_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "README.md").write_text("# My Project", encoding="utf-8")
            request = {"prompt": "analyse", "include_project_context": True}
            result = build_project_context(project, request)
            self.assertIsInstance(result, ContextResult)
            self.assertIn("README.md", result.text)
            self.assertIn("README.md", result.included_files)

    def test_context_files_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "Dockerfile").write_text("FROM python:3.11\n", encoding="utf-8")
            request = {"prompt": "analyse", "context_files": ["Dockerfile"]}
            result = build_project_context(project, request)
            self.assertIsNotNone(result)
            assert result is not None
            self.assertIn("Dockerfile", result.included_files)
            self.assertIn("FROM python:3.11", result.text)

    def test_context_globs(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            src = project / "src"
            src.mkdir()
            (src / "app.py").write_text("# app\n", encoding="utf-8")
            (src / "util.py").write_text("# util\n", encoding="utf-8")
            request = {"prompt": "analyse", "context_globs": ["src/*.py"]}
            result = build_project_context(project, request)
            self.assertIsNotNone(result)
            assert result is not None
            self.assertIn("src/app.py", result.included_files)
            self.assertIn("src/util.py", result.included_files)

    def test_ticket_files_included(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "schema.sql").write_text(
                "-- schema\nCREATE TABLE users (id INT);", encoding="utf-8"
            )
            # .sql suffix IS excluded (binary/database files)
            (project / "model.py").write_text("class User: pass\n", encoding="utf-8")
            request = {"prompt": "analyse", "ticket_files": ["model.py", "schema.sql"]}
            result = build_project_context(project, request)
            self.assertIsNotNone(result)
            assert result is not None
            self.assertIn("model.py", result.included_files)
            # schema.sql is excluded by suffix — must never appear in output
            self.assertNotIn("schema.sql", result.included_files)
            self.assertNotIn("CREATE TABLE", result.text)

    def test_secrets_never_included(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".env").write_text("OPENROUTER_API_KEY=sk-secret123", encoding="utf-8")
            (project / ".env.production").write_text(
                "DB_PASSWORD=hunter2", encoding="utf-8"
            )
            (project / "private.key").write_text("-----BEGIN RSA PRIVATE KEY-----\n", encoding="utf-8")
            (project / "README.md").write_text("# Safe", encoding="utf-8")
            request = {
                "prompt": "analyse",
                "include_project_context": True,
                "context_files": [".env", ".env.production", "private.key"],
            }
            result = build_project_context(project, request)
            self.assertIsNotNone(result)
            assert result is not None
            self.assertNotIn("sk-secret123", result.text)
            self.assertNotIn("hunter2", result.text)
            self.assertNotIn("BEGIN RSA PRIVATE KEY", result.text)
            self.assertNotIn(".env", result.included_files)
            self.assertNotIn("private.key", result.included_files)

    def test_max_context_chars_truncation(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "big.py").write_text("x = 1\n" * 5000, encoding="utf-8")
            request = {
                "prompt": "analyse",
                "context_files": ["big.py"],
                "max_context_chars": 200,
            }
            result = build_project_context(project, request)
            self.assertIsNotNone(result)
            assert result is not None
            self.assertTrue(result.truncated)
            self.assertGreater(result.total_chars, 200)
            self.assertIn("truncated", result.text)
            # text must not exceed max_context_chars (annotation is included in the limit)
            self.assertLessEqual(len(result.text), 200)

    def test_default_max_context_chars_is_reasonable(self):
        self.assertEqual(DEFAULT_MAX_CONTEXT_CHARS, 32_000)

    def test_file_tree_appears_in_auto_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "Dockerfile").write_text("FROM python:3.11", encoding="utf-8")
            (project / "koru.yaml").write_text("project: test", encoding="utf-8")
            request = {"prompt": "analyse", "include_project_context": True}
            result = build_project_context(project, request)
            self.assertIsNotNone(result)
            assert result is not None
            self.assertIn("Project file tree", result.text)

    def test_path_traversal_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            request = {
                "prompt": "analyse",
                "context_files": ["../../etc/passwd"],
            }
            result = build_project_context(project, request)
            # Should return None (no readable file) or not include the escaped path
            if result is not None:
                self.assertNotIn("passwd", result.included_files)

    def test_non_existent_file_skipped_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            request = {
                "prompt": "analyse",
                "context_files": ["does_not_exist.py"],
            }
            result = build_project_context(project, request)
            # File tree will exist but no file content → result may be non-None (has tree)
            if result is not None:
                self.assertNotIn("does_not_exist.py", result.included_files)


# ---------------------------------------------------------------------------
# _build_llm_messages — context injection
# ---------------------------------------------------------------------------


class TestBuildLlmMessages(unittest.TestCase):

    def test_no_context_plain_prompt(self):
        request = {"prompt": "hello world", "system_prompt": None}
        messages = _build_llm_messages(request)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[0]["content"], "hello world")

    def test_system_prompt_prepended(self):
        request = {"prompt": "user question", "system_prompt": "You are helpful."}
        messages = _build_llm_messages(request)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[0]["content"], "You are helpful.")
        self.assertEqual(messages[-1]["role"], "user")
        self.assertEqual(messages[-1]["content"], "user question")

    def test_context_text_injected_as_user_message(self):
        request = {
            "prompt": "Describe the architecture.",
            "context_text": "## Project file tree\n\n```\nDockerfile\n```",
            "context_metadata": {
                "included_files": ["Dockerfile"],
                "truncated": False,
                "total_chars": 50,
            },
        }
        messages = _build_llm_messages(request)
        # Should have: context user message + prompt user message
        self.assertEqual(len(messages), 2)
        ctx_msg = messages[0]
        self.assertEqual(ctx_msg["role"], "user")
        self.assertIn("project_context", ctx_msg["content"])
        self.assertIn("Project file tree", ctx_msg["content"])
        self.assertIn("Dockerfile", ctx_msg["content"])

        prompt_msg = messages[-1]
        self.assertEqual(prompt_msg["role"], "user")
        self.assertEqual(prompt_msg["content"], "Describe the architecture.")

    def test_context_with_system_prompt_order(self):
        request = {
            "prompt": "Describe.",
            "system_prompt": "Be concise.",
            "context_text": "## README\n\nHello",
            "context_metadata": {"included_files": ["README.md"], "truncated": False, "total_chars": 20},
        }
        messages = _build_llm_messages(request)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")  # context block
        self.assertIn("project_context", messages[1]["content"])
        self.assertEqual(messages[2]["role"], "user")  # prompt
        self.assertEqual(messages[2]["content"], "Describe.")

    def test_truncation_note_in_context_message(self):
        request = {
            "prompt": "question",
            "context_text": "x" * 200,
            "context_metadata": {
                "included_files": [],
                "truncated": True,
                "total_chars": 5000,
            },
        }
        messages = _build_llm_messages(request)
        ctx_content = messages[0]["content"]
        self.assertIn("truncated", ctx_content.lower())

    def test_included_files_listed_in_context_message(self):
        request = {
            "prompt": "question",
            "context_text": "## Dockerfile\n\n```\nFROM python\n```",
            "context_metadata": {
                "included_files": ["Dockerfile", "README.md"],
                "truncated": False,
                "total_chars": 30,
            },
        }
        messages = _build_llm_messages(request)
        ctx_content = messages[0]["content"]
        self.assertIn("Dockerfile", ctx_content)
        self.assertIn("README.md", ctx_content)


# ---------------------------------------------------------------------------
# ticket_llm_request — context fields pass-through
# ---------------------------------------------------------------------------


class TestTicketLlmRequestContextFields(unittest.TestCase):

    def test_no_context_fields_when_not_requested(self):
        ticket = {
            "id": "T-1",
            "name": "Basic prompt",
            "executor": {"kind": "llm"},
            "inputs": {"prompt": "hello", "llm_model": "openai/gpt-4o-mini"},
        }
        request = ticket_llm_request(ticket)
        self.assertIsNotNone(request)
        assert request is not None
        self.assertNotIn("include_project_context", request)
        self.assertNotIn("context_files", request)
        self.assertNotIn("context_globs", request)
        self.assertNotIn("max_context_chars", request)

    def test_include_project_context_true_passed_through(self):
        ticket = {
            "id": "T-1",
            "name": "Context ticket",
            "executor": {"kind": "llm"},
            "inputs": {
                "prompt": "analyse",
                "include_project_context": True,
            },
        }
        request = ticket_llm_request(ticket)
        self.assertIsNotNone(request)
        assert request is not None
        self.assertTrue(request.get("include_project_context"))

    def test_context_files_passed_through(self):
        ticket = {
            "id": "T-1",
            "name": "Context ticket",
            "executor": {"kind": "llm"},
            "inputs": {
                "prompt": "analyse",
                "context_files": ["Dockerfile", "README.md"],
            },
        }
        request = ticket_llm_request(ticket)
        self.assertIsNotNone(request)
        assert request is not None
        self.assertEqual(request["context_files"], ["Dockerfile", "README.md"])

    def test_context_globs_passed_through(self):
        ticket = {
            "id": "T-1",
            "name": "Context ticket",
            "executor": {"kind": "llm"},
            "inputs": {
                "prompt": "analyse",
                "context_globs": ["src/**/*.py"],
            },
        }
        request = ticket_llm_request(ticket)
        self.assertIsNotNone(request)
        assert request is not None
        self.assertEqual(request["context_globs"], ["src/**/*.py"])

    def test_max_context_chars_passed_through(self):
        ticket = {
            "id": "T-1",
            "name": "Context ticket",
            "executor": {"kind": "llm"},
            "inputs": {
                "prompt": "analyse",
                "max_context_chars": 8000,
            },
        }
        request = ticket_llm_request(ticket)
        self.assertIsNotNone(request)
        assert request is not None
        self.assertEqual(request["max_context_chars"], 8000)

    def test_ticket_files_passed_through(self):
        ticket = {
            "id": "T-1",
            "name": "Ticket with files",
            "executor": {"kind": "llm"},
            "inputs": {"prompt": "review"},
            "files": ["src/app.py", "tests/test_app.py"],
        }
        request = ticket_llm_request(ticket)
        self.assertIsNotNone(request)
        assert request is not None
        self.assertEqual(request["ticket_files"], ["src/app.py", "tests/test_app.py"])


# ---------------------------------------------------------------------------
# End-to-end: context flows through run_next_planfile_task
# ---------------------------------------------------------------------------


class TestLlmContextEndToEnd(unittest.TestCase):

    def _run_with_context_ticket(self, ticket: dict, project: Path) -> tuple[dict, object]:
        """Run a planfile task and return (captured_request, run_result)."""
        captured: dict = {}

        def planfile_runner(command, _project) -> SimpleNamespace:
            if _ticket_args(command)[:5] == ["ticket", "list", "--status", "open", "--format"]:
                return _ok(json.dumps(ticket))
            return _ok()

        def llm_runner(request: dict, _project) -> SimpleNamespace:
            captured["request"] = request
            return SimpleNamespace(
                returncode=0,
                stdout="The project uses Docker Compose with a PHP service.",
                stderr="",
                status_code=200,
                model="openai/gpt-4o-mini",
                usage={"prompt_tokens": 100, "completion_tokens": 50},
            )

        result = run_next_planfile_task(
            project=project,
            actor="koru-llm",
            planfile_runner=planfile_runner,
            llm_runner=llm_runner,
        )
        return captured.get("request", {}), result

    def test_context_enrichment_with_include_project_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "Dockerfile").write_text(
                "FROM php:8.2-fpm\nRUN docker-php-ext-install pdo\n", encoding="utf-8"
            )
            (project / "README.md").write_text(
                "# PHP App\nA simple PHP project.", encoding="utf-8"
            )
            ticket = _llm_ticket(
                inputs={
                    "prompt": "Describe the architecture.",
                    "llm_model": "openai/gpt-4o-mini",
                    "include_project_context": True,
                }
            )
            request, result = self._run_with_context_ticket(ticket, project)

        self.assertEqual(result.status, "completed")
        # llm_runner received enriched request with context
        self.assertIn("context_text", request)
        self.assertIn("Dockerfile", request["context_text"])
        self.assertIn("PHP App", request["context_text"])
        meta = request.get("context_metadata", {})
        self.assertIn("Dockerfile", meta.get("included_files", []))
        self.assertIn("README.md", meta.get("included_files", []))
        self.assertFalse(meta.get("truncated", True))

    def test_context_enrichment_with_explicit_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "docker-compose.yml").write_text(
                "services:\n  app:\n    image: php:8.2\n", encoding="utf-8"
            )
            ticket = _llm_ticket(
                inputs={
                    "prompt": "Describe the services.",
                    "llm_model": "openai/gpt-4o-mini",
                    "context_files": ["docker-compose.yml"],
                }
            )
            request, result = self._run_with_context_ticket(ticket, project)

        self.assertEqual(result.status, "completed")
        self.assertIn("context_text", request)
        self.assertIn("docker-compose.yml", request["context_text"])
        self.assertIn("php:8.2", request["context_text"])

    def test_prompt_only_ticket_unchanged(self):
        """Regression: a prompt-only ticket must not have context added."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            ticket = _llm_ticket()  # default: no context inputs
            request, result = self._run_with_context_ticket(ticket, project)

        self.assertEqual(result.status, "completed")
        self.assertNotIn("context_text", request)
        self.assertNotIn("context_metadata", request)

    def test_secrets_not_in_context_sent_to_llm(self):
        """Even if .env exists in project root it must never reach the LLM."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / ".env").write_text(
                "OPENROUTER_API_KEY=sk-super-secret\nDB_PASSWORD=hunter2\n",
                encoding="utf-8",
            )
            (project / "README.md").write_text("# Safe file", encoding="utf-8")
            ticket = _llm_ticket(
                inputs={
                    "prompt": "analyse",
                    "llm_model": "openai/gpt-4o-mini",
                    "include_project_context": True,
                    "context_files": [".env"],
                }
            )
            request, result = self._run_with_context_ticket(ticket, project)

        self.assertEqual(result.status, "completed")
        context = request.get("context_text", "")
        self.assertNotIn("sk-super-secret", context)
        self.assertNotIn("hunter2", context)

    def test_context_metadata_recorded_in_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "koru.yaml").write_text("project: myapp\n", encoding="utf-8")
            ticket = _llm_ticket(
                inputs={
                    "prompt": "describe",
                    "llm_model": "openai/gpt-4o-mini",
                    "include_project_context": True,
                }
            )
            request, _ = self._run_with_context_ticket(ticket, project)

        meta = request.get("context_metadata")
        self.assertIsNotNone(meta)
        self.assertIn("included_files", meta)
        self.assertIn("truncated", meta)
        self.assertIn("total_chars", meta)

    def test_context_globs_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            src = project / "src"
            src.mkdir()
            (src / "main.py").write_text("def main(): pass\n", encoding="utf-8")
            (src / "utils.py").write_text("def helper(): pass\n", encoding="utf-8")
            ticket = _llm_ticket(
                inputs={
                    "prompt": "review code",
                    "llm_model": "openai/gpt-4o-mini",
                    "context_globs": ["src/*.py"],
                }
            )
            request, result = self._run_with_context_ticket(ticket, project)

        self.assertEqual(result.status, "completed")
        self.assertIn("context_text", request)
        self.assertIn("def main", request["context_text"])
        self.assertIn("def helper", request["context_text"])
        included = request.get("context_metadata", {}).get("included_files", [])
        self.assertIn("src/main.py", included)
        self.assertIn("src/utils.py", included)

    def test_max_context_chars_respected(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "huge.py").write_text("x = 1\n" * 10_000, encoding="utf-8")
            ticket = _llm_ticket(
                inputs={
                    "prompt": "analyse",
                    "llm_model": "openai/gpt-4o-mini",
                    "context_files": ["huge.py"],
                    "max_context_chars": 500,
                }
            )
            request, result = self._run_with_context_ticket(ticket, project)

        self.assertEqual(result.status, "completed")
        self.assertIn("context_text", request)
        meta = request.get("context_metadata", {})
        self.assertTrue(meta.get("truncated"))


if __name__ == "__main__":
    unittest.main()
