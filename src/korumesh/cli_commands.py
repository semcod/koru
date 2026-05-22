"""Command handlers for ``koru mesh``."""

from __future__ import annotations

import argparse
import asyncio
import sys

from korumesh.envelope import sign_envelope
from korumesh.keys import load_mesh_key, write_mesh_key
from korumesh.store import remember_envelope
from korumesh.transport import publish_envelope, run_relay


def mesh_init(args: argparse.Namespace) -> int:
    from koru.configurator import load_project_config

    saved = load_project_config(args.project)
    mesh = saved.get("mesh") if isinstance(saved.get("mesh"), dict) else {}
    key_path = args.project / str(mesh.get("psk_path") or ".koru/keys/mesh.hmac")
    path = write_mesh_key(key_path, force=args.force)
    print(f"koru mesh: key ready at {path}")
    return 0


def mesh_relay(args: argparse.Namespace, key: bytes) -> int:
    try:
        asyncio.run(run_relay(host=args.host, port=args.port, key=key, on_frame=remember_envelope))
    except KeyboardInterrupt:
        return 0
    except RuntimeError as exc:
        print(f"koru mesh relay: {exc}", file=sys.stderr)
        return 2
    return 0


def mesh_publish(args: argparse.Namespace, key: bytes) -> int:
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
