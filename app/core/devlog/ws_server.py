"""WebSocket server that exposes the log bus to external clients.

Clients connect to:
  ws://localhost:PORT/?level=<level>

where <level> is one of: info, warning, error  (default: info)

Uses the websockets >= 14 asyncio API (ServerConnection).
"""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import parse_qs, urlparse

from websockets.asyncio.server import ServerConnection, serve

from app.core.devlog.bus import LogBus, Subscriber
from app.core.devlog.levels import LEVEL_NAMES, INFO

log = logging.getLogger(__name__)


async def _handle_client(websocket: ServerConnection, bus: LogBus) -> None:
    """Handle one WebSocket connection: subscribe, stream, unsubscribe."""
    path = websocket.request.path if websocket.request else "/"
    qs = parse_qs(urlparse(path).query)
    level_str = qs.get("level", ["info"])[0].lower()
    threshold = LEVEL_NAMES.get(level_str, INFO)

    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=256)

    def enqueue(message: str) -> None:
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            pass

    subscriber = Subscriber(threshold=threshold, send=enqueue)
    bus.subscribe(subscriber)
    log.info("devlog client connected (level=%s threshold=%d)", level_str, threshold)

    try:
        while True:
            message = await queue.get()
            await websocket.send(message)
    except Exception:
        pass
    finally:
        bus.unsubscribe(subscriber)
        log.info("devlog client disconnected")


async def start_ws_server(bus: LogBus, port: int) -> None:
    """Start the WebSocket log server and run until cancelled."""

    async def handler(ws: ServerConnection) -> None:
        await _handle_client(ws, bus)

    async with serve(handler, "localhost", port):
        log.info("devlog WebSocket server listening on ws://localhost:%d", port)
        await asyncio.Future()  # run forever
