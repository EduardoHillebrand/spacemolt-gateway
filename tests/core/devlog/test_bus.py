"""Tests for devlog/bus.py — fan-out logic."""

import logging
import pytest

from app.core.devlog.bus import LogBus, Subscriber
from app.core.devlog.levels import INFO, WARNING, ERROR


def make_record(level: int, message: str = "test") -> logging.LogRecord:
    return logging.LogRecord(
        name="test.module",
        level=level,
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None,
    )


class TestBusNoSubscribers:
    def test_publish_with_no_subscribers_does_not_raise(self):
        bus = LogBus()
        bus.publish(make_record(INFO))  # should be a no-op, no exception

    def test_publish_with_no_subscribers_calls_nothing(self):
        called = []
        bus = LogBus()
        # No subscriber registered — called list stays empty
        bus.publish(make_record(ERROR))
        assert called == []


class TestBusSingleSubscriber:
    def test_subscriber_receives_matching_level(self):
        received = []
        bus = LogBus()
        sub = Subscriber(threshold=WARNING, send=received.append)
        bus.subscribe(sub)

        bus.publish(make_record(WARNING))
        assert len(received) == 1

    def test_subscriber_receives_higher_level(self):
        received = []
        bus = LogBus()
        sub = Subscriber(threshold=WARNING, send=received.append)
        bus.subscribe(sub)

        bus.publish(make_record(ERROR))
        assert len(received) == 1

    def test_subscriber_does_not_receive_lower_level(self):
        received = []
        bus = LogBus()
        sub = Subscriber(threshold=WARNING, send=received.append)
        bus.subscribe(sub)

        bus.publish(make_record(INFO))
        assert received == []


class TestBusTwoSubscribers:
    def test_each_subscriber_gets_only_what_it_should(self):
        info_received = []
        error_received = []
        bus = LogBus()

        sub_info = Subscriber(threshold=INFO, send=info_received.append)
        sub_error = Subscriber(threshold=ERROR, send=error_received.append)
        bus.subscribe(sub_info)
        bus.subscribe(sub_error)

        bus.publish(make_record(INFO))
        bus.publish(make_record(WARNING))
        bus.publish(make_record(ERROR))

        assert len(info_received) == 3    # info sub sees everything
        assert len(error_received) == 1   # error sub sees only error


class TestBusUnsubscribe:
    def test_unsubscribed_subscriber_receives_nothing(self):
        received = []
        bus = LogBus()
        sub = Subscriber(threshold=INFO, send=received.append)
        bus.subscribe(sub)
        bus.unsubscribe(sub)

        bus.publish(make_record(ERROR))
        assert received == []

    def test_unsubscribe_nonexistent_does_not_raise(self):
        bus = LogBus()
        sub = Subscriber(threshold=INFO, send=lambda _: None)
        bus.unsubscribe(sub)  # never subscribed — should be a no-op


class TestBusMessageFormat:
    def test_published_message_contains_level(self):
        received = []
        bus = LogBus()
        bus.subscribe(Subscriber(threshold=INFO, send=received.append))

        bus.publish(make_record(ERROR, "boom"))
        assert "error" in received[0]

    def test_published_message_contains_message_text(self):
        received = []
        bus = LogBus()
        bus.subscribe(Subscriber(threshold=INFO, send=received.append))

        bus.publish(make_record(INFO, "hello world"))
        assert "hello world" in received[0]
