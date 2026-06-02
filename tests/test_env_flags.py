"""Tests for koru.env_flags — central env-variable parsing utilities."""

from __future__ import annotations

import pytest

from koru.env_flags import env_disabled, env_int, env_truthy


# ---------------------------------------------------------------------------
# env_truthy
# ---------------------------------------------------------------------------


class TestEnvTruthy:
    def test_unset_returns_false_by_default(self, monkeypatch):
        monkeypatch.delenv("KORU_TEST_FLAG", raising=False)
        assert env_truthy("KORU_TEST_FLAG") is False

    def test_unset_returns_custom_default(self, monkeypatch):
        monkeypatch.delenv("KORU_TEST_FLAG", raising=False)
        assert env_truthy("KORU_TEST_FLAG", default=True) is True

    @pytest.mark.parametrize("value", ["1", "true", "True", "TRUE", "yes", "YES", "on", "ON", "auto", "AUTO", "y", "Y"])
    def test_truthy_values(self, monkeypatch, value):
        monkeypatch.setenv("KORU_TEST_FLAG", value)
        assert env_truthy("KORU_TEST_FLAG") is True

    @pytest.mark.parametrize("value", ["0", "false", "False", "no", "off", "", "  ", "random"])
    def test_non_truthy_values_return_false(self, monkeypatch, value):
        monkeypatch.setenv("KORU_TEST_FLAG", value)
        assert env_truthy("KORU_TEST_FLAG") is False

    def test_strips_whitespace(self, monkeypatch):
        monkeypatch.setenv("KORU_TEST_FLAG", "  1  ")
        assert env_truthy("KORU_TEST_FLAG") is True

    def test_default_true_overridden_by_false_value(self, monkeypatch):
        monkeypatch.setenv("KORU_TEST_FLAG", "0")
        assert env_truthy("KORU_TEST_FLAG", default=True) is False


# ---------------------------------------------------------------------------
# env_disabled
# ---------------------------------------------------------------------------


class TestEnvDisabled:
    def test_unset_returns_false(self, monkeypatch):
        monkeypatch.delenv("KORU_TEST_FLAG", raising=False)
        assert env_disabled("KORU_TEST_FLAG") is False

    @pytest.mark.parametrize("value", ["0", "false", "False", "FALSE", "no", "NO", "off", "OFF"])
    def test_disabled_values(self, monkeypatch, value):
        monkeypatch.setenv("KORU_TEST_FLAG", value)
        assert env_disabled("KORU_TEST_FLAG") is True

    @pytest.mark.parametrize("value", ["1", "true", "yes", "on", "", "  ", "random"])
    def test_non_disabled_values_return_false(self, monkeypatch, value):
        monkeypatch.setenv("KORU_TEST_FLAG", value)
        assert env_disabled("KORU_TEST_FLAG") is False

    def test_strips_whitespace(self, monkeypatch):
        monkeypatch.setenv("KORU_TEST_FLAG", "  false  ")
        assert env_disabled("KORU_TEST_FLAG") is True


# ---------------------------------------------------------------------------
# env_int
# ---------------------------------------------------------------------------


class TestEnvInt:
    def test_unset_returns_default(self, monkeypatch):
        monkeypatch.delenv("KORU_TEST_INT", raising=False)
        assert env_int("KORU_TEST_INT", 42) == 42

    def test_empty_string_returns_default(self, monkeypatch):
        monkeypatch.setenv("KORU_TEST_INT", "")
        assert env_int("KORU_TEST_INT", 99) == 99

    def test_valid_integer(self, monkeypatch):
        monkeypatch.setenv("KORU_TEST_INT", "7")
        assert env_int("KORU_TEST_INT", 0) == 7

    def test_invalid_value_returns_default(self, monkeypatch):
        monkeypatch.setenv("KORU_TEST_INT", "notanumber")
        assert env_int("KORU_TEST_INT", 5) == 5

    def test_strips_whitespace(self, monkeypatch):
        monkeypatch.setenv("KORU_TEST_INT", "  8  ")
        assert env_int("KORU_TEST_INT", 0) == 8

    def test_negative_integer(self, monkeypatch):
        monkeypatch.setenv("KORU_TEST_INT", "-3")
        assert env_int("KORU_TEST_INT", 0) == -3
