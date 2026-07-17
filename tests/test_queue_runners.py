from __future__ import annotations

import sys
from pathlib import Path

from koru.queue.runners import run_process


def test_run_process_falls_back_to_preferred_encoding(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("koru.queue.runners.locale.getpreferredencoding", lambda _do_setlocale: "cp1250")

    result = run_process(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "sys.stdout.buffer.write('fóó'.encode('cp1250')); "
                "sys.stderr.buffer.write('błąd'.encode('cp1250'))"
            ),
        ],
        tmp_path,
    )

    assert result.returncode == 0
    assert result.stdout == "fóó"
    assert result.stderr == "błąd"


def test_run_process_prefers_utf8_before_locale_fallback(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("koru.queue.runners.locale.getpreferredencoding", lambda _do_setlocale: "cp1250")

    result = run_process(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "sys.stdout.buffer.write('żółw'.encode('utf-8')); "
                "sys.stderr.buffer.write('zażółć'.encode('utf-8'))"
            ),
        ],
        tmp_path,
    )

    assert result.returncode == 0
    assert result.stdout == "żółw"
    assert result.stderr == "zażółć"
