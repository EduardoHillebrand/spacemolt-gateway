"""Log level definitions and delivery rule for the dev-log channel.

Reuses Python's logging level integers:
  INFO    = 20
  WARNING = 30
  ERROR   = 40

A subscriber sets a threshold. They receive every record at that level
or above.
"""

import logging

INFO = logging.INFO        # 20
WARNING = logging.WARNING  # 30
ERROR = logging.ERROR      # 40

LEVEL_NAMES: dict[str, int] = {
    "info": INFO,
    "warning": WARNING,
    "error": ERROR,
}


def should_deliver(record_level: int, sub_threshold: int) -> bool:
    """Return True if a log record should be delivered to a subscriber.

    Args:
        record_level: The level of the incoming log record.
        sub_threshold: The minimum level the subscriber wants to receive.

    Examples:
        should_deliver(ERROR, WARNING)  -> True   (error >= warning)
        should_deliver(INFO,  WARNING)  -> False  (info < warning)
    """
    return record_level >= sub_threshold
