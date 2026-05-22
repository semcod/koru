"""Argparse helpers for ``koru mesh``."""

from __future__ import annotations

import argparse
from pathlib import Path


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
    publish.add_argument("--to-peer", default="*", dest="peer_to", help="Recipient peer id or *.")
    publish.add_argument("--topic", required=True, help="Envelope topic.")
    publish.add_argument("--mime", default="text/plain", help="Payload MIME type.")
    publish.add_argument("--payload", default="", help="Payload body.")
    publish.add_argument("--key-file", type=Path, required=True, help="HMAC key file.")
    publish.add_argument("--listen-seconds", type=float, default=2.0, help="Listen for relayed frames.")

    init = sub.add_parser("init", help="Create .koru/keys/mesh.hmac if missing.")
    init.add_argument("--project", type=Path, default=Path.cwd(), help="Project root.")
    init.add_argument("--force", action="store_true", help="Overwrite an existing key file.")
    return parser
