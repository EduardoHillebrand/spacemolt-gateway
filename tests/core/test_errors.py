"""Tests for app.core.errors."""

import pytest

from app.core.errors import PreconditionError


def test_precondition_error_is_exception() -> None:
    assert issubclass(PreconditionError, Exception)


def test_precondition_error_message_is_preserved() -> None:
    err = PreconditionError("missing mining laser")
    assert str(err) == "missing mining laser"


def test_precondition_error_can_be_raised_and_caught() -> None:
    with pytest.raises(PreconditionError, match="cargo is full"):
        raise PreconditionError("cargo is full")
