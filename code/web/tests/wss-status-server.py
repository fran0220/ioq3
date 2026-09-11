#!/usr/bin/env python3
"""Local TLS transport fixture, NOT an Origin Game admission or Quake server.

Real WebSocket connections exercise compiled WASM transport auth, ready,
reconnect and terminal close callbacks. Credentials are test-only literals.
"""
import argparse
import asyncio
import json
import ssl

from websockets.asyncio.server import serve


async def main(cert, key, port):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    connections = 0

    async def handle(socket):
        nonlocal connections
        connections += 1
        attempt = connections
        auth = json.loads(await socket.recv())
        if auth != {"type": "auth", "token": "local-transport-fixture"}:
            await socket.close(code=1008)
            return
        print(f"PASS auth connection {attempt}: same test-only token", flush=True)
        await asyncio.sleep(3)
        await socket.send(json.dumps({"type": "ready", "sessionId": "local-status-session"}))
        await asyncio.sleep(3)
        code = 1012 if attempt % 2 else 1008
        print(f"Closing connection {attempt} with {code}", flush=True)
        await socket.close(code=code)

    async with serve(handle, "127.0.0.1", port, ssl=context, subprotocols=["og-udp-v1"]):
        await asyncio.Future()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cert", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--port", type=int, default=4175)
    args = parser.parse_args()
    asyncio.run(main(args.cert, args.key, args.port))
