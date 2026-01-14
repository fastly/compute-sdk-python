"""Show (and test) some motivating examples of how the ``nice_exceptions``
decorator makes WIT's ``result``-driven errors more Pythonic."""

import sys
from pathlib import Path

# Bring in stubs for local testing:
sys.path.append(str(Path(__file__).parent.parent / "stubs"))

from wit_world.imports.types import Error_BufferLen
from wit_world.types import Err

from fastly_compute.exceptions import (
    FastlyError,
    UnexpectedFastlyError,
    nice_exceptions,
)


class BufferTooShortError(FastlyError):
    def __init__(self, wit_error: Error_BufferLen):
        self.length = wit_error.value

    # Freed of the generated skeletal dataclasses, we can add niceties like good
    # error messages.
    def __str__(self):
        return f"Buffer was too short to hold the result. At least {self.length} is needed."


class NegativeHeightError(FastlyError):
    def __init__(self, height: int):
        self.height = height


def test_primitive():
    """Show that a primitive type can be mapped to a meaningful exception."""

    @nice_exceptions({int: NegativeHeightError})
    def raise_int() -> Err:
        """Raise a primitive value, which is expected and gets wrapped in a descriptive exception."""
        raise Err(value=-3)

    try:
        raise_int()
    except NegativeHeightError as e:
        assert e.height == -3


def test_unexpected():
    """For unexpected error types, an UnexpectedFastlyError should be raised.

    This preserves the value of the original error and the ability for customers
    to catch all Fastly API errors by catching FastlyError. It also keeps them
    insulated from componentize-py's Err class, lest we move away from it
    someday.
    """

    @nice_exceptions()
    def raise_int_by_surprise() -> Err:
        """Raise a primitive value, which is a type we didn't expect."""
        raise Err(value=-3)

    try:
        raise_int_by_surprise()
    except UnexpectedFastlyError as e:
        assert e.value == -3


def test_variant():
    """Show how a WIT variant case can be concisely mapped into a more idiomatic exception."""

    @nice_exceptions({Error_BufferLen: BufferTooShortError})
    def raise_variant() -> Err:
        """Raise an Err whose value is a case of our generic ``error`` variant."""
        raise Err(value=Error_BufferLen(64))

    try:
        raise_variant()
    except BufferTooShortError as e:
        assert e.length == 64
