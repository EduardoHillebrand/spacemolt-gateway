"""One-call setup to wire the dev-log channel into the Python logging system.

Call init_dev_logging(port) from within a running asyncio event loop.
After that, every logging call anywhere in the project flows through the
bus and out to connected WebSocket clients automatically.
"""

from __future__ import annotations

import asyncio
import logging

from app.core.devlog.bus import LogBus
from app.core.devlog.handler import DevLogHandler
from app.core.devlog.ws_server import start_ws_server

_DEV_LOG_PORT = 7788


async def init_dev_logging(port: int = _DEV_LOG_PORT) -> None:
    """Wire logging -> DevLogHandler -> LogBus -> WebSocket.

    Must be called from within a running asyncio event loop
    (e.g. from a FastMCP lifespan context manager).
    """
    loop = asyncio.get_running_loop()
    bus = LogBus()

    handler = DevLogHandler(bus=bus, loop=loop)
    handler.start()

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    asyncio.create_task(start_ws_server(bus, port))

    logging.getLogger(__name__).info(
        "dev-log channel active on ws://localhost:%d", port
    )
