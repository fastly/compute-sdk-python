"""Show (and test) some motivating examples of how the ``remap_wit_errors``
decorator makes WIT's ``result``-driven errors more Pythonic."""

import sys
from pathlib import Path

from pytest import raises

# Bring in stubs for local testing:
sys.path.append(str(Path(__file__).parent.parent / "stubs"))

from wit_world.imports.types import Error_BufferLen, OpenError
from wit_world.types import Err

from fastly_compute.exceptions import (
    FastlyError,
    UnexpectedFastlyError,
    remap_wit_errors,
)


class BufferTooShortError(FastlyError):
    # A "nice" version of a WIT exception takes the WIT error as the sole arg of
    # its constructor. While it would make the exception class more
    # constructable by customer code if we took, for example, simply an int here
    # and added a from_wit_error() class method, this would complicate the
    # calling contract of remap_wit_errors() for "escape-hatch" callables which
    # conditionally choose exception mappings. It remains to be seen if we ever
    # need those.
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

    @remap_wit_errors({int: NegativeHeightError})
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

    @remap_wit_errors()
    def raise_int_by_surprise() -> Err:
        """Raise a primitive value, which is a type we didn't expect."""
        raise Err(value=-3)

    try:
        raise_int_by_surprise()
    except UnexpectedFastlyError as e:
        assert e.value == -3


def test_variant():
    """Show how a WIT variant case can be concisely mapped into a more idiomatic exception."""

    @remap_wit_errors({Error_BufferLen: BufferTooShortError})
    def raise_variant() -> Err:
        """Raise an Err whose value is a case of our generic ``error`` variant."""
        raise Err(value=Error_BufferLen(64))

    try:
        raise_variant()
    except BufferTooShortError as e:
        assert e.length == 64


def test_enum():
    """Show how we can also map individual enum cases to exception classes."""

    class InvalidSyntaxError(FastlyError):
        pass

    class NotFoundError(FastlyError):
        pass

    enum_map = {
        OpenError.INVALID_SYNTAX: InvalidSyntaxError,
        OpenError.NOT_FOUND: NotFoundError,
    }

    @remap_wit_errors(enum_map)
    def raise_one_enum() -> Err:
        raise Err(value=OpenError.INVALID_SYNTAX)

    @remap_wit_errors(enum_map)
    def raise_other_enum() -> Err:
        raise Err(value=OpenError.NOT_FOUND)

    try:
        raise_one_enum()
    except InvalidSyntaxError as e:
        assert len(e.args) == 0, (
            "Exceptions raised based on enum members should receive no constructor args."
        )

    with raises(NotFoundError):
        raise_other_enum()
