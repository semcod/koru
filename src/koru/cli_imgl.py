"""``koru imgl`` — shell wrapper for vision-guided UI actions."""

from __future__ import annotations

import argparse
import json
import sys


def _add_format_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["auto", "json", "yaml", "markdown"],
        default="auto",
        help="stdout: auto (markdown/yaml/json), or force json|yaml|markdown",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Alias for --format json (legacy)",
    )


def _resolved_format(args: argparse.Namespace) -> str:
    if getattr(args, "json", False):
        return "json"
    return args.output_format


def imgl_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="koru imgl", description="Vision-guided UI via imgl")
    sub = parser.add_subparsers(dest="cmd", required=True)

    doctor = sub.add_parser("doctor", help="Diagnose screenshot (img2nl blank vs real UI)")
    doctor.add_argument("--image", default=None, help="PNG path (default: KORU_IMGL_IMAGE)")
    doctor.add_argument("--locale", default="pl", help="img2nl locale (default: pl)")
    _add_format_arg(doctor)

    execute = sub.add_parser("execute", help="Run NL UI action (TYPE / KEY / CLICK)")
    execute.add_argument("prompt", help='e.g. "wpisz test w Chat input"')
    execute.add_argument("--image", default=None, help="Screenshot PNG (default: capture)")
    execute.add_argument("--window", default=None, help="region-bottom or region-top")
    execute.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan only, do not click/type on desktop",
    )
    execute.add_argument(
        "--execute",
        dest="do_execute",
        action="store_true",
        help="Execute on desktop (default unless --dry-run)",
    )
    execute.add_argument(
        "--no-diagnose",
        action="store_true",
        help="Skip img2nl capture diagnostics",
    )
    _add_format_arg(execute)

    args = parser.parse_args(argv)
    fmt = _resolved_format(args)

    if args.cmd == "doctor":
        from imgl.autodiag import diagnose_capture, render_report
        from koru.integrations.imgl_client import default_image_path, doctor_capture

        image = args.image or str(default_image_path())
        try:
            capture = doctor_capture(image, locale=args.locale) if args.image else doctor_capture(
                locale=args.locale
            )
        except Exception as exc:
            capture = diagnose_capture(image, locale=args.locale)
            capture.setdefault("error", str(exc))
            capture["ok"] = False
            capture["verdict"] = "error"
        print(render_report({"capture": capture, "verdict": capture.get("verdict")}, fmt))
        return (
            0
            if capture.get("verdict") in {"real_ui", "uncertain"} and capture.get("is_fresh", True)
            else 1
        )

    if args.cmd != "execute":
        parser.print_help()
        return 1

    from koruapi.desktop_uri import desktop_uri_imgl_execute

    dry_run = bool(args.dry_run) and not args.do_execute
    if not args.dry_run and not args.do_execute:
        dry_run = False

    payload = desktop_uri_imgl_execute(
        args.prompt,
        image=args.image,
        window=args.window,
        dry_run=dry_run,
        execute=not dry_run,
        with_diagnostics=not args.no_diagnose,
    )

    if fmt in {"json", "yaml", "markdown", "auto"} and payload.get("diagnostics"):
        from imgl.autodiag import render_report

        print(render_report(payload["diagnostics"], fmt))
    elif fmt == "json" or args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        if payload.get("error"):
            print(f"error: {payload['error']}", file=sys.stderr)
        result = payload.get("result") or {}
        if result.get("output"):
            print(result["output"])
        elif result.get("error"):
            print(f"error: {result['error']}", file=sys.stderr)
        elif not payload.get("ok"):
            print(json.dumps(payload, indent=2, ensure_ascii=False))

    diag = payload.get("diagnostics") or {}
    ok = bool(payload.get("ok"))
    checks = diag.get("checks") or {}
    if checks.get("blocked_blank_capture") or checks.get("blocked_stale_capture"):
        ok = False
    return 0 if ok else 1


__all__ = ["imgl_main"]
