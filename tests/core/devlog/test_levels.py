"""Tests for devlog/levels.py — the filter rule table from the spec."""

import pytest
from app.core.devlog.levels import should_deliver, INFO, WARNING, ERROR


class TestShouldDeliver:
    """Subscriber level table from the spec."""

    # --- subscribed to ERROR ---
    def test_error_sub_receives_error(self):
        assert should_deliver(ERROR, ERROR) is True

    def test_error_sub_does_not_receive_warning(self):
        assert should_deliver(WARNING, ERROR) is False

    def test_error_sub_does_not_receive_info(self):
        assert should_deliver(INFO, ERROR) is False

    # --- subscribed to WARNING ---
    def test_warning_sub_receives_error(self):
        assert should_deliver(ERROR, WARNING) is True

    def test_warning_sub_receives_warning(self):
        assert should_deliver(WARNING, WARNING) is True

    def test_warning_sub_does_not_receive_info(self):
        assert should_deliver(INFO, WARNING) is False

    # --- subscribed to INFO ---
    def test_info_sub_receives_error(self):
        assert should_deliver(ERROR, INFO) is True

    def test_info_sub_receives_warning(self):
        assert should_deliver(WARNING, INFO) is True

    def test_info_sub_receives_info(self):
        assert should_deliver(INFO, INFO) is True
