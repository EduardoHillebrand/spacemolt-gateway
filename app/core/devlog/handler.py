"""Non-blocking logging.Handler that feeds log records into the LogBus.

The standard logging system can call emit() from any thread. To avoid
blocking the asyncio event loop (or blocking the calling thread waiting
for the loop), we:
  1. Put records into an asyncio.Queue (thread-safe via call_soon_threadsafe).
  2. A dedicated asyncio Task drains the queue and calls bus.publish().
  3. When the queue is full we drop the *oldest* record so logging can
     never stall the application.
"""

from __future__ import annotations

import asyncio
import logging

from app.core.devlog.bus import LogBus

_QUEUE_MAX = 256  # drop oldest when full


class DevLogHandler(logging.Handler):
    """Logging handler that publishes records to a LogBus without blocking."""

    def __init__(self, bus: LogBus, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__()
        self._bus = bus
        self._loop = loop
        self._queue: asyncio.Queue[logging.LogRecord] = asyncio.Queue(maxsize=_QUEUE_MAX)
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        """Start the drain task. Must be called from within the event loop."""
        self._task = self._loop.create_task(self._drain())

    def stop(self) -> None:
        """Cancel the drain task."""
        if self._task:
            self._task.cancel()

    def emit(self, record: logging.LogRecord) -> None:
        """Called by the logging system (possibly from another thread)."""
        try:
            self._loop.call_soon_threadsafe(self._enqueue, record)
        except RuntimeError:
            # Loop is closed or not running — silently drop.
            pass

    def _enqueue(self, record: logging.LogRecord) -> None:
        """Enqueue a record, dropping the oldest if the queue is full."""
        if self._queue.full():
            try:
                self._queue.get_nowait()  # discard oldest
            except asyncio.QueueEmpty:
                pass
        try:
            self._queue.put_nowait(record)
        except asyncio.QueueFull:
            pass  # race condition safety net

    async def _drain(self) -> None:
        """Continuously drain the queue and publish to the bus."""
        while True:
            record = await self._queue.get()
            try:
                self._bus.publish(record)
            except Exception:
                pass  # logging must never crash the app
