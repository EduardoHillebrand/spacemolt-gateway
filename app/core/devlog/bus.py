"""Fan-out bus for the dev-log channel.

The bus holds a set of subscribers and, on each publish, delivers the
log record to every subscriber whose threshold allows it.

Design constraints (from the spec):
- No-op when there are no subscribers (zero overhead on the hot path).
- The bus does not know about WebSocket -- it talks to abstract Subscriber
  objects. This makes it fully testable without any network.
"""

from __future__ import annotations

import json
import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from app.core.devlog.levels import should_deliver


@dataclass(eq=False)
class Subscriber:
    """An abstract destination that receives formatted log lines.

    Uses eq=False so each Subscriber instance is unique by identity,
    which makes it safely hashable for use in a set.

    Args:
        threshold: Minimum log level to deliver (INFO, WARNING, or ERROR).
        send: Callable that accepts a formatted string.
    """

    threshold: int
    send: Callable[[str], None]


@dataclass
class LogBus:
    """Holds subscribers and fans log records out to the right ones."""

    _subscribers: set[Subscriber] = field(default_factory=set)

    def subscribe(self, subscriber: Subscriber) -> None:
        """Add a subscriber to the bus."""
        self._subscribers.add(subscriber)

    def unsubscribe(self, subscriber: Subscriber) -> None:
        """Remove a subscriber from the bus (no-op if not present)."""
        self._subscribers.discard(subscriber)

    def publish(self, record: logging.LogRecord) -> None:
        """Deliver record to every eligible subscriber.

        Returns immediately when there are no subscribers (zero overhead).
        """
        if not self._subscribers:
            return

        message = _format_record(record)
        for sub in self._subscribers:
            if should_deliver(record.levelno, sub.threshold):
                sub.send(message)


def _format_record(record: logging.LogRecord) -> str:
    """Format a LogRecord into a JSON string."""
    payload: dict = {
        "level": record.levelname.lower(),
        "module": record.name,
        "message": record.getMessage(),
        "time": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
    }
    if record.exc_info:
        payload["exc"] = traceback.format_exception(*record.exc_info)
    return json.dumps(payload, ensure_ascii=False)
