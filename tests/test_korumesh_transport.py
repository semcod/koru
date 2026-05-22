from __future__ import annotations

import asyncio

import pytest

from korumesh.codec import envelope_from_wire, envelope_to_wire
from korumesh.envelope import sign_envelope, verify_envelope
from korumesh.transport import _relay_client, publish_envelope

websockets = pytest.importorskip("websockets")


def test_envelope_wire_roundtrip() -> None:
    key = b"wire-roundtrip-key-32-bytes!!!"
    envelope = sign_envelope(
        peer_from="a",
        peer_to="b",
        topic="vision/frame",
        mime="image/png",
        payload=b"\x89PNG",
        key=key,
    )
    restored = envelope_from_wire(envelope_to_wire(envelope))
    assert verify_envelope(restored, key)


def test_relay_forwards_signed_envelope() -> None:
    key = b"relay-test-key-32-bytes-long!!"
    received: list = []

    async def listener(url: str) -> None:
        async with websockets.connect(url) as ws:
            raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            received.append(envelope_from_wire(str(raw)))

    async def run() -> None:
        peers: set = set()
        async with websockets.serve(
            lambda ws: _relay_client(ws, key=key, peers=peers, on_frame=None),
            "127.0.0.1",
            0,
        ) as server:
            port = server.sockets[0].getsockname()[1]
            url = f"ws://127.0.0.1:{port}"
            envelope = sign_envelope(
                peer_from="host-a",
                peer_to="*",
                topic="mesh/ping",
                mime="text/plain",
                payload=b"hello",
                key=key,
            )
            listen_task = asyncio.create_task(listener(url))
            await asyncio.sleep(0.05)
            await publish_envelope(url, envelope, recv_timeout=0.2)
            await asyncio.wait_for(listen_task, timeout=2.0)

    asyncio.run(run())
    assert received
    assert received[0].topic == "mesh/ping"
    assert verify_envelope(received[0], key)
