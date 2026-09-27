"""CLI entrypoint for koru voice and koru nlp commands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from koru.voice.dispatcher import VoiceDispatcher
from koru.voice.executor import VoiceCommandExecutor


def build_parser(prog: str = "koru voice") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Natural language and voice command bridge for Koru loops and Planfile queue.",
    )
    parser.add_argument(
        "phrase",
        nargs="*",
        help="Voice transcription or NL text to execute (e.g. 'zatrzymaj pętlę', 'status kolejki').",
    )
    parser.add_argument(
        "-t",
        "--text",
        dest="text_override",
        default=None,
        help="Explicit command text (alternative to positional arguments).",
    )
    parser.add_argument(
        "-j",
        "--json",
        action="store_true",
        help="Output structured JSON response for programmatic / WebSocket clients.",
    )
    parser.add_argument(
        "-p",
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Target project directory (defaults to current working directory).",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Run interactive voice / NL shell session.",
    )
    return parser


def dispatch_and_run(phrase: str, project: Path, output_json: bool) -> int:
    dispatcher = VoiceDispatcher()
    executor = VoiceCommandExecutor(project_root=project)
    parsed = dispatcher.parse(phrase)
    result = executor.execute(parsed)

    if output_json:
        payload = result.to_dict()
        payload["parsed"] = {
            "intent": parsed.intent.value,
            "raw": parsed.raw_text,
            "normalized": parsed.normalized_text,
            "arguments": parsed.arguments,
            "confidence": parsed.confidence,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(result.message)

    return 0 if result.success else 1


def _run_interactive(project: Path, output_json: bool) -> int:
    print("Koru Voice / NLP Interactive Shell. Type 'exit' or 'q' to quit.\n")
    while True:
        try:
            line = input("koru-voice> ").strip()
            if not line:
                continue
            if line.lower() in ("exit", "quit", "q"):
                print("Do widzenia!")
                break
            dispatch_and_run(line, project, output_json)
            print()
        except (KeyboardInterrupt, EOFError):
            print("\nDo widzenia!")
            break
    return 0


def voice_main(argv: list[str]) -> int:
    """Main CLI function for 'koru voice'."""
    parser = build_parser(prog="koru voice")
    args = parser.parse_args(argv)

    if args.interactive:
        return _run_interactive(args.project, args.json)

    phrase_parts = args.phrase or []
    full_phrase = args.text_override or " ".join(phrase_parts).strip()

    if not full_phrase:
        if sys.stdin.isatty():
            return _run_interactive(args.project, args.json)
        # Read from stdin pipe if available
        full_phrase = sys.stdin.read().strip()
        if not full_phrase:
            parser.print_help()
            return 2

    return dispatch_and_run(full_phrase, args.project, args.json)


def nlp_main(argv: list[str]) -> int:
    """Main CLI function for 'koru nlp'."""
    parser = build_parser(prog="koru nlp")
    args = parser.parse_args(argv)

    if args.interactive:
        return _run_interactive(args.project, args.json)

    phrase_parts = args.phrase or []
    full_phrase = args.text_override or " ".join(phrase_parts).strip()

    if not full_phrase:
        if sys.stdin.isatty():
            return _run_interactive(args.project, args.json)
        full_phrase = sys.stdin.read().strip()
        if not full_phrase:
            parser.print_help()
            return 2

    return dispatch_and_run(full_phrase, args.project, args.json)
