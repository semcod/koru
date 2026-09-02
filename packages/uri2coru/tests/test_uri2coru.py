import importlib
import sys

import pytest


def test_legacy_uri_namespace_warns_and_reexports_canonical_symbols() -> None:
    for name in tuple(sys.modules):
        if name == "uri2coru" or name.startswith("uri2coru."):
            sys.modules.pop(name)

    with pytest.warns(DeprecationWarning, match="uri2coru is deprecated"):
        legacy = importlib.import_module("uri2coru")
    canonical = importlib.import_module("uri2koru")

    assert legacy.CORU_SCHEME is canonical.KORU_SCHEME
    assert legacy.ResolvedCoruUri is canonical.ResolvedKoruUri
    assert legacy.best_uri is canonical.best_uri
    assert legacy.is_coru_uri is canonical.is_koru_uri
    assert legacy.nlp2uri is canonical.nlp2uri
    assert legacy.run_uri is canonical.run_uri
    assert legacy.uri_for_block is canonical.uri_for_block
    assert legacy.uri_for_cmd is canonical.uri_for_cmd
    assert legacy.uri_to_dsl is canonical.uri_to_dsl


def test_legacy_uri_modules_and_console_alias_canonical_behavior(capsys) -> None:
    legacy_cli = importlib.import_module("uri2coru.cli")
    canonical_cli = importlib.import_module("uri2koru.cli")
    legacy_decode = importlib.import_module("uri2coru.decode")
    canonical_decode = importlib.import_module("uri2koru.decode")
    legacy_nlp = importlib.import_module("uri2coru.nlp2uri")
    canonical_nlp = importlib.import_module("uri2koru.nlp2uri")
    legacy_run = importlib.import_module("uri2coru.run")
    canonical_run = importlib.import_module("uri2koru.run")
    legacy_uri = importlib.import_module("uri2coru.uri")
    canonical_uri = importlib.import_module("uri2koru.uri")

    assert legacy_cli.main is canonical_cli.main
    assert legacy_decode.uri_to_dsl is canonical_decode.uri_to_dsl
    assert legacy_nlp.ResolvedCoruUri is canonical_nlp.ResolvedKoruUri
    assert legacy_run.run_uri is canonical_run.run_uri
    assert legacy_uri.parse_coru_uri is canonical_uri.parse_koru_uri

    argv = ["decode", "--uri", "koru://cmd/VALIDATE_LANE?ide=auto&instance=default"]
    assert canonical_cli.main(argv) == 0
    canonical_output = capsys.readouterr().out
    assert legacy_cli.main(argv) == 0
    assert capsys.readouterr().out == canonical_output
