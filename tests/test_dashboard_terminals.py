"""Tests for the Terminals tab backend and opencode supervisor."""

from __future__ import annotations

import json
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from koruapi import opencode_terminals as ot
from koruapi import opencode_supervisor as ocs


class TestRegistry:
    def test_register_and_load(self, tmp_path: Path) -> None:
        entry = ot.register_instance(
            tmp_path, url="http://127.0.0.1:4099/", label="test", pid=123,
            managed=True,
        )
        assert entry["id"]
        entries = ot.load_registry(tmp_path)
        assert len(entries) == 1
        assert entries[0]["url"] == "http://127.0.0.1:4099"
        assert entries[0]["managed"] is True

    def test_register_same_url_updates(self, tmp_path: Path) -> None:
        ot.register_instance(tmp_path, url="http://127.0.0.1:4099", label="a")
        ot.register_instance(tmp_path, url="http://127.0.0.1:4099", label="b")
        entries = ot.load_registry(tmp_path)
        assert len(entries) == 1
        assert entries[0]["label"] == "b"

    def test_unregister(self, tmp_path: Path) -> None:
        entry = ot.register_instance(tmp_path, url="http://127.0.0.1:1")
        assert ot.unregister_instance(tmp_path, entry["id"]) is True
        assert ot.load_registry(tmp_path) == []
        assert ot.unregister_instance(tmp_path, entry["id"]) is False

    def test_load_missing_or_corrupt(self, tmp_path: Path) -> None:
        assert ot.load_registry(tmp_path) == []
        ot.registry_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
        ot.registry_path(tmp_path).write_text("not json", encoding="utf-8")
        assert ot.load_registry(tmp_path) == []

    def test_set_auto_answer(self, tmp_path: Path) -> None:
        entry = ot.register_instance(tmp_path, url="http://x:1")
        updated = ot.set_auto_answer(tmp_path, entry["id"], False)
        assert updated is not None and updated["auto_answer"] is False
        assert ot.set_auto_answer(tmp_path, "nope", True) is None

    def test_set_auto_answer_adopts_discovered_process(self, tmp_path: Path) -> None:
        discovered = [
            {"id": "proc-4101", "url": "http://127.0.0.1:4101",
             "pid": 99999, "label": "opencode serve :4101",
             "managed": False, "auto_answer": False}
        ]
        with patch.object(ot, "_scan_serve_processes", return_value=discovered):
            entry = ot.set_auto_answer(tmp_path, "proc-4101", True)
        assert entry is not None
        assert entry["auto_answer"] is True
        assert entry["managed"] is False
        entries = ot.load_registry(tmp_path)
        assert len(entries) == 1
        assert entries[0]["url"] == "http://127.0.0.1:4101"
        assert entries[0]["auto_answer"] is True
        # Stop is still refused for an adopted but unmanaged instance.
        assert "not koru-managed" in ot.stop_instance(tmp_path, entry["id"])["error"]

    def test_discovered_process_gets_stable_id(self, tmp_path: Path) -> None:
        discovered = [
            {"id": "proc-4101", "url": "http://127.0.0.1:4101",
             "pid": 99999, "label": "opencode serve :4101",
             "managed": False, "auto_answer": False}
        ]
        with patch.object(ot, "_scan_serve_processes", return_value=discovered):
            instances = ot.discover_instances(tmp_path, probe=False)
            # The same id now resolves for prompt/reply/detail lookups.
            assert ot.terminal_detail(tmp_path, "proc-4101")["id"] == "proc-4101"
        assert instances[0]["id"] == "proc-4101"


class TestApiClient:
    def test_api_request_get(self) -> None:
        fake = MagicMock()
        fake.read.return_value = json.dumps({"data": [{"id": "ses_1"}]}).encode()
        fake.__enter__ = lambda s: s
        fake.__exit__ = lambda *a: False
        with patch("urllib.request.urlopen", return_value=fake) as mock:
            sessions = ot.list_sessions("http://127.0.0.1:4099")
        assert sessions == [{"id": "ses_1"}]
        req = mock.call_args[0][0]
        assert req.full_url == "http://127.0.0.1:4099/api/session"

    def test_reply_permission_validates(self) -> None:
        with pytest.raises(ValueError):
            ot.reply_permission("http://x", "ses_1", "per_1", "bogus")

    def test_session_messages_uses_unprefixed_route(self) -> None:
        fake = MagicMock()
        fake.read.return_value = json.dumps(
            [{"info": {"role": "user"}, "parts": []}]
        ).encode()
        fake.__enter__ = lambda s: s
        fake.__exit__ = lambda *a: False
        with patch("urllib.request.urlopen", return_value=fake) as mock:
            msgs = ot.session_messages("http://x", "ses_9")
        req = mock.call_args[0][0]
        # /api/session/{id}/message returns an event projection, not
        # conversation messages — the unprefixed route is the real one.
        assert req.full_url == "http://x/session/ses_9/message"
        assert msgs == [{"info": {"role": "user"}, "parts": []}]

    def test_send_prompt_body(self) -> None:
        fake = MagicMock()
        fake.read.return_value = b""
        fake.__enter__ = lambda s: s
        fake.__exit__ = lambda *a: False
        with patch("urllib.request.urlopen", return_value=fake) as mock:
            result = ot.send_prompt("http://x", "ses_9", "hello")
        req = mock.call_args[0][0]
        body = json.loads(req.data.decode())
        # prompt_async executes immediately; /prompt only steer-queues.
        assert body == {"parts": [{"type": "text", "text": "hello"}]}
        assert req.full_url == "http://x/session/ses_9/prompt_async"
        assert result["ok"] is True

    def test_send_prompt_passes_normalized_model_and_agent(self) -> None:
        fake = MagicMock()
        fake.read.return_value = b""
        fake.__enter__ = lambda s: s
        fake.__exit__ = lambda *a: False
        with patch("urllib.request.urlopen", return_value=fake) as mock:
            ot.send_prompt(
                "http://x",
                "ses_9",
                "hi",
                model={"providerID": "zai", "modelID": "glm-5.3"},
                agent="build",
            )
        body = json.loads(mock.call_args[0][0].data.decode())
        # prompt_async wants {providerID, modelID}; session create wants
        # {id, providerID} — the server schemas differ.
        assert body["model"] == {"providerID": "zai", "modelID": "glm-5.3"}
        assert body["agent"] == "build"

    def test_create_session_normalizes_model(self) -> None:
        fake = MagicMock()
        fake.read.return_value = json.dumps({"data": {"id": "ses_7"}}).encode()
        fake.__enter__ = lambda s: s
        fake.__exit__ = lambda *a: False
        with patch("urllib.request.urlopen", return_value=fake) as mock:
            sess = ot.create_session(
                "http://x",
                title="t",
                model={"providerID": "zai", "modelID": "glm-5.3"},
            )
        assert sess == {"id": "ses_7"}
        body = json.loads(mock.call_args[0][0].data.decode())
        assert body["model"] == {"id": "glm-5.3", "providerID": "zai"}

    def test_terminal_prompt_session_create_failure_returns_error(
        self, tmp_path: Path
    ) -> None:
        entry = ot.register_instance(tmp_path, url="http://x:9", managed=False)

        def boom(*a, **k):
            raise urllib.error.HTTPError("u", 400, "Bad Request", None, None)

        with patch.object(ot, "create_session", side_effect=boom):
            result = ot.terminal_prompt(
                tmp_path, {"iid": entry["id"], "text": "hi"}
            )
        assert "failed to create session" in result["error"]

    def test_pending_requests_tolerates_failure(self) -> None:
        def boom(*a, **k):
            raise OSError("down")

        with patch.object(ot, "_api_request", side_effect=boom):
            pending = ot.pending_requests("http://x")
        assert pending == {"permissions": [], "questions": []}


class TestSpawnStop:
    def test_stop_unknown(self, tmp_path: Path) -> None:
        assert ot.stop_instance(tmp_path, "nope")["ok"] is False

    def test_stop_refuses_unmanaged(self, tmp_path: Path) -> None:
        entry = ot.register_instance(tmp_path, url="http://x:9", managed=False)
        result = ot.stop_instance(tmp_path, entry["id"])
        assert result["ok"] is False
        assert "not koru-managed" in result["error"]

    def test_stop_refuses_adopted_unmanaged(self, tmp_path: Path) -> None:
        # Discovered via /proc but never persisted: still a managed=false
        # refusal, not "unknown instance".
        discovered = [
            {"id": "proc-4101", "url": "http://127.0.0.1:4101",
             "pid": 99999, "label": "opencode serve :4101",
             "managed": False, "auto_answer": False}
        ]
        with patch.object(ot, "_scan_serve_processes", return_value=discovered):
            result = ot.stop_instance(tmp_path, "proc-4101")
        assert result["ok"] is False
        assert "not koru-managed" in result["error"]

    def test_stop_managed_dead_pid(self, tmp_path: Path) -> None:
        entry = ot.register_instance(
            tmp_path, url="http://x:9", managed=True, pid=99999999
        )
        result = ot.stop_instance(tmp_path, entry["id"])
        assert result["ok"] is True
        assert result["stopped"] is False
        assert ot.load_registry(tmp_path) == []


class TestPayloads:
    def test_terminals_payload_aggregates(self, tmp_path: Path) -> None:
        instances = [
            {"id": "a", "url": "http://a", "healthy": True,
             "managed": True, "auto_answer": True},
            {"id": "b", "url": "http://b", "healthy": False},
        ]
        sessions = [{
            "id": "ses_1", "slug": "s",
            "location": {"directory": "/p/x"},
            "model": {"id": "glm-5.3", "providerID": "zai"},
            "agent": "build",
            "time": {"updated": 0},
        }]
        with (
            patch.object(ot, "discover_instances", return_value=instances),
            patch.object(ot, "list_sessions", return_value=sessions),
            patch.object(
                ot, "pending_requests",
                return_value={"permissions": [{"id": "per_1"}], "questions": []},
            ),
            patch.object(
                ot, "list_providers",
                return_value=[{"id": "zai", "name": "Z.ai",
                               "api_type": "aisdk",
                               "api_url": "https://api.z.ai"}],
            ),
        ):
            payload = ot.terminals_payload(tmp_path)
        assert payload["total"] == 2
        assert payload["healthy"] == 1
        a = next(r for r in payload["instances"] if r["id"] == "a")
        srow = a["sessions"][0]
        assert srow["id"] == "ses_1"
        assert srow["title"] == "s"
        # directory comes from location.directory, not the flat field
        assert srow["directory"] == "/p/x"
        assert srow["model"] == "glm-5.3"
        assert srow["provider"] == "zai"
        assert srow["agent"] == "build"
        assert srow["ticket"] is None
        assert a["project_dirs"] == ["/p/x"]
        assert a["models"] == ["zai/glm-5.3"]
        assert a["providers"][0]["api_url"] == "https://api.z.ai"
        assert a["active_ticket"] is None
        assert a["pending"] == {"permissions": 1, "questions": 0}

    def test_session_ticket_extracted_from_recent_user_prompt(
        self, tmp_path: Path
    ) -> None:
        import time as _time

        now_ms = int(_time.time() * 1000)
        sess = {"id": "ses_t", "time": {"updated": now_ms}}
        messages = [
            {"info": {"role": "user"},
             "parts": [{"type": "text",
                        "text": "Work on planfile ticket STARTER-578: fix"}]},
            {"info": {"role": "assistant"},
             "parts": [{"type": "text", "text": "done"}]},
        ]
        with patch.object(ot, "session_messages", return_value=messages):
            assert ot._session_ticket("http://x", sess) == "STARTER-578"

    def test_session_ticket_skips_stale_sessions(self) -> None:
        sess = {"id": "ses_old", "time": {"updated": 1}}
        with patch.object(
            ot, "session_messages", side_effect=AssertionError("no fetch")
        ):
            assert ot._session_ticket("http://x", sess) is None

    def test_session_ticket_caches_per_updated(self) -> None:
        import time as _time

        now_ms = int(_time.time() * 1000)
        sess = {"id": "ses_c", "time": {"updated": now_ms}}
        calls = []

        def fake(url, sid, **kw):
            calls.append(sid)
            return []

        with patch.object(ot, "session_messages", side_effect=fake):
            assert ot._session_ticket("http://x", sess) is None
            assert ot._session_ticket("http://x", sess) is None
        assert calls == ["ses_c"]

    def test_normalize_message_opencode_shape(self) -> None:
        raw = {
            "info": {"role": "assistant", "agent": "build",
                     "modelID": "glm-5.3", "providerID": "zai",
                     "time": {"created": 123}},
            "parts": [
                {"type": "step-start"},
                {"type": "text", "text": "OK"},
                {"type": "tool", "tool": "bash",
                 "state": {"title": "pytest -q"}},
                {"type": "reasoning", "text": "thinking"},
            ],
        }
        out = ot.normalize_message(raw)
        assert out["role"] == "assistant"
        assert out["model"] == "glm-5.3"
        assert out["provider"] == "zai"
        assert out["created"] == 123
        assert "OK" in out["text"]
        assert "[tool: bash] pytest -q" in out["text"]
        assert "[reasoning]" in out["text"]
        assert "step-start" not in out["text"]

    def test_terminal_messages_normalizes(self, tmp_path: Path) -> None:
        entry = ot.register_instance(tmp_path, url="http://x:9")
        raw = [{"info": {"role": "user"},
                "parts": [{"type": "text", "text": "say ok"}]}]
        with (
            patch.object(ot, "discover_instances",
                         return_value=[entry]),
            patch.object(ot, "session_messages", return_value=raw),
        ):
            payload = ot.terminal_messages(tmp_path, entry["id"], "ses_1")
        assert payload["messages"] == [
            {"role": "user", "text": "say ok", "agent": None,
             "model": None, "provider": None, "created": None}
        ]

    def test_list_providers_sanitizes_request_body(self) -> None:
        fake = MagicMock()
        fake.read.return_value = json.dumps(
            {"data": [{"id": "zai", "name": "Z.ai",
                       "api": {"type": "aisdk", "url": "https://api.z.ai"},
                       "request": {"body": {"apiKey": "secret"}}}]}
        ).encode()
        fake.__enter__ = lambda s: s
        fake.__exit__ = lambda *a: False
        with patch("urllib.request.urlopen", return_value=fake):
            providers = ot.list_providers("http://x")
        assert providers == [{"id": "zai", "name": "Z.ai",
                              "api_type": "aisdk",
                              "api_url": "https://api.z.ai"}]

    def test_terminal_detail_unknown(self, tmp_path: Path) -> None:
        with patch.object(ot, "discover_instances", return_value=[]):
            assert "error" in ot.terminal_detail(tmp_path, "x")


class TestSupervisor:
    def _entry(self, **kw):
        base = {"id": "i1", "url": "http://x", "healthy": True,
                "auto_answer": True}
        base.update(kw)
        return base

    def test_disabled_env(self, monkeypatch) -> None:
        monkeypatch.setenv("KORU_TERMINALS_SUPERVISOR", "0")
        assert ocs.supervisor_enabled() is False
        monkeypatch.setenv("KORU_TERMINALS_SUPERVISOR", "1")
        assert ocs.supervisor_enabled() is True

    def test_supervise_answers_permission(self, tmp_path: Path) -> None:
        pending = {
            "permissions": [
                {"id": "per_1", "sessionID": "ses_1", "action": "bash",
                 "resources": ["ls"]}
            ],
            "questions": [],
        }
        replied = []
        with (
            patch.object(ocs, "discover_instances",
                         return_value=[self._entry()]),
            patch.object(ocs, "pending_requests", return_value=pending),
            patch.object(ocs, "reply_permission",
                         side_effect=lambda u, s, r, rep: replied.append(rep)),
        ):
            stats = ocs.supervise_once(tmp_path, log=lambda m: None)
        assert stats["permissions"] == 1
        assert replied == ["once"]

    def test_supervise_skips_without_auto_answer(self, tmp_path: Path) -> None:
        with patch.object(
            ocs, "discover_instances",
            return_value=[self._entry(auto_answer=False)],
        ):
            stats = ocs.supervise_once(tmp_path, log=lambda m: None)
        assert stats == {"permissions": 0, "questions": 0, "failovers": 0,
                         "errors": 0, "instances": 0}

    def test_question_answers_shape(self, tmp_path: Path) -> None:
        req = {
            "id": "que_1",
            "sessionID": "ses_1",
            "questions": [
                {"header": "refactor", "question": "which option?",
                 "options": [{"label": "A"}, {"label": "B"}]},
            ],
        }
        fake_result = MagicMock()
        fake_result.returncode = 0
        fake_result.stdout = json.dumps([["B"]])
        fake_subllm = MagicMock(return_value=fake_result)
        import sys
        import types

        fake_mod = types.ModuleType("korullm")
        fake_mod.run_subllm = fake_subllm
        with patch.dict(sys.modules, {"korullm": fake_mod}):
            answers = ocs._question_answers_via_llm(tmp_path, req, lambda m: None)
        assert answers == [["B"]]

    def test_question_llm_invents_label_falls_back(self, tmp_path: Path) -> None:
        req = {
            "questions": [
                {"question": "q?", "options": [{"label": "A"}, {"label": "B"}]},
            ],
        }
        fake_result = MagicMock()
        fake_result.returncode = 0
        fake_result.stdout = json.dumps([["bogus"]])
        import sys
        import types

        fake_mod = types.ModuleType("korullm")
        fake_mod.run_subllm = MagicMock(return_value=fake_result)
        with patch.dict(sys.modules, {"korullm": fake_mod}):
            answers = ocs._question_answers_via_llm(tmp_path, req, lambda m: None)
        assert answers == [["A"]]


class TestProviderFailover:
    def setup_method(self) -> None:
        ot.clear_provider_exhaustion()

    def teardown_method(self) -> None:
        ot.clear_provider_exhaustion()

    def test_exhaustion_tracker_lifecycle(self) -> None:
        assert not ot.is_provider_exhausted("zai")
        ot.mark_provider_exhausted("zai", ttl_seconds=10.0, reason="limit test")
        assert ot.is_provider_exhausted("zai")
        exhausted = ot.get_exhausted_providers()
        assert "zai" in exhausted
        assert exhausted["zai"]["reason"] == "limit test"
        assert exhausted["zai"]["remaining_seconds"] > 0

        ot.mark_provider_exhausted("expired-p", ttl_seconds=-1.0)
        assert not ot.is_provider_exhausted("expired-p")

        ot.clear_provider_exhaustion("zai")
        assert not ot.is_provider_exhausted("zai")

    def test_parse_exhaustion_from_error(self) -> None:
        err1 = "AI_APICallError: Usage limit reached for 5 hour. Your limit will reset at 2026-09-17 18:48:17"
        is_ex, ttl, reason = ot.parse_exhaustion_from_error(err1)
        assert is_ex is True
        assert ttl > 0
        assert "Usage limit reached" in reason

        err2 = "HTTP 429: Too Many Requests"
        is_ex, ttl, _ = ot.parse_exhaustion_from_error(err2)
        assert is_ex is True

        err3 = "Connection refused by peer"
        is_ex, _, _ = ot.parse_exhaustion_from_error(err3)
        assert is_ex is False

    def test_scan_opencode_log_for_exhaustion(self, tmp_path: Path) -> None:
        log_file = tmp_path / "opencode.log"
        log_file.write_text(
            'timestamp=2026-09-17T10:40:31.387Z level=ERROR run=db234658 message="stream error" '
            'providerID=zai modelID=glm-5.3 session.id=ses_test123 small=false agent=build mode=primary '
            'error.error="AI_APICallError: Usage limit reached for 5 hour. Your limit will reset at 2026-09-17 18:48:17"\n',
            encoding="utf-8",
        )
        detected = ot.scan_opencode_log_for_exhaustion(log_path=log_file)
        assert len(detected) == 1
        assert detected[0]["providerID"] == "zai"
        assert detected[0]["sessionID"] == "ses_test123"
        assert ot.is_provider_exhausted("zai")

    def test_scan_opencode_log_missing_file_returns_empty(self, tmp_path: Path) -> None:
        assert ot.scan_opencode_log_for_exhaustion(log_path=tmp_path / "absent.log") == []

    def test_scan_opencode_log_reads_only_tail(self, tmp_path: Path) -> None:
        head = (
            'timestamp=2026-09-17T10:40:31.387Z level=ERROR run=headrun message="stream error" '
            'providerID=headp modelID=glm-5.3 error.error="AI_APICallError: Usage limit reached"\n'
        )
        tail = (
            'timestamp=2026-09-17T11:40:31.387Z level=ERROR run=tailrun message="stream error" '
            'providerID=tailp modelID=glm-5.3 error.error="AI_APICallError: Usage limit reached"\n'
        )
        log_file = tmp_path / "opencode.log"
        log_file.write_text(head + tail, encoding="utf-8")
        detected = ot.scan_opencode_log_for_exhaustion(
            log_path=log_file, max_bytes=len(tail.encode("utf-8"))
        )
        assert [event["providerID"] for event in detected] == ["tailp"]
        assert not ot.is_provider_exhausted("headp")
        assert ot.is_provider_exhausted("tailp")

    def test_scan_opencode_log_ignores_non_exhaustion_errors(self, tmp_path: Path) -> None:
        log_file = tmp_path / "opencode.log"
        log_file.write_text(
            'timestamp=2026-09-17T10:40:31.387Z level=ERROR run=db234658 message="stream error" '
            'providerID=zai modelID=glm-5.3 session.id=ses_test123 '
            'error.error="Connection refused by peer"\n',
            encoding="utf-8",
        )
        assert ot.scan_opencode_log_for_exhaustion(log_path=log_file) == []
        assert not ot.is_provider_exhausted("zai")

    def test_get_available_models(self) -> None:
        cfg = {
            "model": "deepseek/deepseek-v4-pro",
            "provider": {
                "zai": {"models": {"glm-5.3": {}}},
                "deepseek": {"models": {"deepseek-v4-pro": {}}},
            },
        }
        with patch.object(ot, "get_instance_config", return_value=cfg):
            models = ot.get_available_models("http://127.0.0.1:4101")
        assert len(models) == 2
        assert models[0] == {"providerID": "deepseek", "modelID": "deepseek-v4-pro"}
        assert models[1] == {"providerID": "zai", "modelID": "glm-5.3"}

    def test_resolve_active_terminal_model_failover(self) -> None:
        cfg = {
            "model": "zai/glm-5.3",
            "provider": {
                "zai": {"models": {"glm-5.3": {}}},
                "deepseek": {"models": {"deepseek-v4-pro": {}}},
            },
        }
        with patch.object(ot, "get_instance_config", return_value=cfg):
            chosen, failover = ot.resolve_active_terminal_model(
                "http://127.0.0.1:4101",
                requested_model={"providerID": "zai", "modelID": "glm-5.3"},
            )
            assert chosen == {"providerID": "zai", "modelID": "glm-5.3"}
            assert failover is None

            ot.mark_provider_exhausted("zai", ttl_seconds=600.0)
            chosen, failover = ot.resolve_active_terminal_model(
                "http://127.0.0.1:4101",
                requested_model={"providerID": "zai", "modelID": "glm-5.3"},
            )
            assert chosen == {"providerID": "deepseek", "modelID": "deepseek-v4-pro"}
            assert failover == {
                "from": "zai",
                "to": "deepseek",
                "model": "deepseek-v4-pro",
            }

    def test_terminal_prompt_auto_failover_retry(self, tmp_path: Path) -> None:
        cfg = {
            "model": "zai/glm-5.3",
            "provider": {
                "zai": {"models": {"glm-5.3": {}}},
                "deepseek": {"models": {"deepseek-v4-pro": {}}},
            },
        }
        entry = {
            "id": "proc-4101",
            "url": "http://127.0.0.1:4101",
            "pid": 1234,
            "managed": False,
            "auto_answer": True,
        }
        calls = []

        def fake_send(url, session_id, text, model=None, agent=None):
            calls.append(model)
            if model and model.get("providerID") == "zai":
                raise urllib.error.HTTPError(
                    url, 429, "Rate limit reached", {}, None
                )
            return {"ok": True}

        with (
            patch.object(ot, "_find_instance", return_value=entry),
            patch.object(ot, "get_instance_config", return_value=cfg),
            patch.object(ot, "send_prompt", side_effect=fake_send),
            patch.object(ot, "scan_opencode_log_for_exhaustion", return_value=[]),
        ):
            res = ot.terminal_prompt(
                tmp_path,
                {
                    "iid": "proc-4101",
                    "session_id": "ses_1",
                    "text": "do something",
                    "model": {"providerID": "zai", "modelID": "glm-5.3"},
                },
            )
        assert res["ok"] is True
        assert "failover" in res
        assert res["failover"]["from"] == "zai"
        assert res["failover"]["to"] == "deepseek"
        assert ot.is_provider_exhausted("zai")

    def test_supervisor_steers_on_stream_error(self, tmp_path: Path) -> None:
        cfg = {
            "model": "deepseek/deepseek-v4-pro",
            "provider": {
                "zai": {"models": {"glm-5.3": {}}},
                "deepseek": {"models": {"deepseek-v4-pro": {}}},
            },
        }
        entry = {
            "id": "proc-4101",
            "url": "http://127.0.0.1:4101",
            "pid": 1234,
            "managed": False,
            "auto_answer": True,
            "healthy": True,
        }
        log_events = [
            {
                "run": "r1",
                "providerID": "zai",
                "modelID": "glm-5.3",
                "sessionID": "ses_stuck",
                "error": "Usage limit reached",
            }
        ]
        prompts_sent = []

        def fake_prompt(url, sid, text, model=None, agent=None):
            prompts_sent.append((url, sid, text, model))
            return {"ok": True}

        with (
            patch.object(ocs, "discover_instances", return_value=[entry]),
            patch.object(ocs, "pending_requests", return_value={"permissions": [], "questions": []}),
            patch.object(ocs, "list_sessions", return_value=[{"id": "ses_stuck"}]),
            patch.object(ocs, "scan_opencode_log_for_exhaustion", return_value=log_events),
            patch.object(ot, "get_instance_config", return_value=cfg),
            patch.object(ocs, "send_prompt", side_effect=fake_prompt),
        ):
            stats = ocs.supervise_once(tmp_path, log=lambda m: None)

        assert stats["failovers"] == 1
        assert len(prompts_sent) == 1
        assert prompts_sent[0][1] == "ses_stuck"
        assert prompts_sent[0][3] == {"providerID": "deepseek", "modelID": "deepseek-v4-pro"}


class TestTemplate:
    @staticmethod
    def _html() -> str:
        path = (
            Path(__file__).resolve().parent.parent
            / "src" / "koruapi" / "dashboard_template.html"
        )
        return path.read_text(encoding="utf-8")

    def test_terminals_tab_registered(self) -> None:
        html = self._html()
        assert '["terminals", "Terminals"]' in html
        assert "renderTerminalsPanel()" in html

    def test_terminals_endpoints_used(self) -> None:
        html = self._html()
        for ep in ("/api/terminals", "/api/terminals/detail",
                   "/api/terminals/messages", "/api/terminals/spawn",
                   "/api/terminals/reply", "/api/terminals/prompt"):
            assert ep in html

    def test_terminals_fast_paint(self) -> None:
        html = self._html()
        assert 'state.tab === "terminals"' in html

    def test_terminals_renders_opencode_parts_shape(self) -> None:
        html = self._html()
        # Raw {info, parts} messages must render — the bug showed "?".
        assert "m.parts" in html
        assert "info.role" in html

    def test_terminals_cards_show_ticket_project_model_api(self) -> None:
        html = self._html()
        for marker in ("active_ticket", "project_dirs", "providers",
                       "s.ticket", "s.model"):
            assert marker in html
