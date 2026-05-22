"""Loopback WebSocket relay for signed mesh envelopes."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any

from korumesh.codec import envelope_from_wire, envelope_to_wire
from korumesh.envelope import Envelope, verify_envelope


def _require_websockets():
    try:
        import websockets
    except ImportError as exc:
        msg = "Install mesh support with: pip install 'koru[mesh]'"
        raise RuntimeError(msg) from exc
    return websockets


async def _relay_client(
    websocket: Any,
    *,
    key: bytes,
    peers: set[Any],
    on_frame: Callable[[Envelope], None] | None,
) -> None:
    peers.add(websocket)
    try:
        async for raw in websocket:
            try:
                envelope = envelope_from_wire(str(raw))
            except (TypeError, ValueError, KeyError, json.JSONDecodeError):
                continue
            if not verify_envelope(envelope, key):
                continue
            if on_frame is not None:
                on_frame(envelope)
            wire = envelope_to_wire(envelope)
            stale: list[Any] = []
            for peer in peers:
                if peer is websocket:
                    continue
                try:
                    await peer.send(wire)
                except Exception:
                    stale.append(peer)
            for peer in stale:
                peers.discard(peer)
    finally:
        peers.discard(websocket)


async def run_relay(
    *,
    host: str,
    port: int,
    key: bytes,
    on_frame: Callable[[Envelope], None] | None = None,
) -> None:
    websockets = _require_websockets()
    peers: set[Any] = set()
    async with websockets.serve(
        lambda ws: _relay_client(ws, key=key, peers=peers, on_frame=on_frame),
        host,
        port,
    ):
        await asyncio.Future()


async def publish_envelope(url: str, envelope: Envelope, *, recv_timeout: float = 2.0) -> list[Envelope]:
    websockets = _require_websockets()
    received: list[Envelope] = []

    async with websockets.connect(url) as websocket:
        await websocket.send(envelope_to_wire(envelope))
        try:
            while True:
                raw = await asyncio.wait_for(websocket.recv(), timeout=recv_timeout)
                try:
                    received.append(envelope_from_wire(str(raw)))
                except (TypeError, ValueError, KeyError):
                    continue
        except TimeoutError:
            return received
    return received
