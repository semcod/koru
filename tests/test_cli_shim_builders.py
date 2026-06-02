from __future__ import annotations

import argparse

from koru.cli_shim_builders import build_main_delegate, build_parser_delegate


def test_build_parser_delegate_returns_parser_from_impl() -> None:
    def _builder() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog="koru demo")
        parser.add_argument("--flag", action="store_true")
        return parser

    delegated = build_parser_delegate(_builder)
    parser = delegated()

    assert isinstance(parser, argparse.ArgumentParser)
    assert parser.prog == "koru demo"


def test_build_main_delegate_passes_argv_and_returns_code() -> None:
    captured: list[list[str]] = []

    def _main(argv: list[str]) -> int:
        captured.append(list(argv))
        return 7

    delegated = build_main_delegate(_main)
    rc = delegated(["--x", "1"])

    assert rc == 7
    assert captured == [["--x", "1"]]
