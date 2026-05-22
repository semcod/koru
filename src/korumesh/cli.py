"""CLI for ``koru mesh`` (relay + publish)."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from korumesh.envelope import sign_envelope
from korumesh.transport import publish_envelope, run_relay


def load_mesh_key(path: Path) -> bytes:
    raw = path.expanduser().read_bytes()
    key = raw.strip()
    if len(key) < 16:
        msg = f"mesh key too short ({len(key)} bytes): {path}"
        raise ValueError(msg)
    return key


def build_mesh_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="koru mesh", description="Koru mesh relay and peer publish.")
    sub = parser.add_subparsers(dest="command", required=True)

    relay = sub.add_parser("relay", help="Run a WebSocket relay on loopback/LAN.")
    relay.add_argument("--host", default="127.0.0.1", help="Bind host.")
    relay.add_argument("--port", type=int, default=9876, help="Bind port.")
    relay.add_argument("--key-file", type=Path, required=True, help="HMAC key file (>=16 bytes).")

    publish = sub.add_parser("publish", help="Publish one signed envelope to a relay.")
    publish.add_argument("--url", default="ws://127.0.0.1:9876", help="Relay WebSocket URL.")
    publish.add_argument("--from-peer", required=True, dest="peer_from", help="Sender peer id.")
    publish.add_argument("--to-peer", default="*", help="Recipient peer id or *.")
    publish.add_argument("--topic", required=True, help="Envelope topic.")
    publish.add_argument("--mime", default="text/plain", help="Payload MIME type.")
    publish.add_argument("--payload", default="", help="Payload body.")
    publish.add_argument("--key-file", type=Path, required=True, help="HMAC key file.")
    publish.add_argument("--listen-seconds", type=float, default=2.0, help="Listen for relayed frames.")
    return parser


def mesh_main(argv: list[str] | None = None) -> int:
    args = build_mesh_parser().parse_args(argv)
    try:
        key = load_mesh_key(args.key_file)
    except (OSError, ValueError) as exc:
        print(f"koru mesh: {exc}", file=sys.stderr)
        return 2

    if args.command == "relay":
        try:
            asyncio.run(run_relay(host=args.host, port=args.port, key=key))
        except KeyboardInterrupt:
            return 0
        except RuntimeError as exc:
            print(f"koru mesh relay: {exc}", file=sys.stderr)
            return 2
        return 0

    envelope = sign_envelope(
        peer_from=args.peer_from,
        peer_to=args.peer_to,
        topic=args.topic,
        mime=args.mime,
        payload=args.payload.encode("utf-8"),
        key=key,
    )
    try:
        received = asyncio.run(
            publish_envelope(args.url, envelope, recv_timeout=max(0.1, args.listen_seconds))
        )
    except Exception as exc:
        print(f"koru mesh publish: {exc}", file=sys.stderr)
        return 2
    print(f"koru mesh: published topic={envelope.topic} id={envelope.envelope_id}")
    for item in received:
        print(f"  relayed from={item.peer_from} topic={item.topic}")
    return 0
