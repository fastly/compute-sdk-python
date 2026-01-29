"""Decorators used in runtime patching"""

from collections.abc import Callable, Mapping
from enum import Enum
from functools import wraps
from typing import Any

from componentize_py_types import Err

from fastly_compute.exceptions import FastlyError, UnexpectedFastlyError


def remap_wit_errors(
    idiomatic_exceptions: Mapping[Any, type[FastlyError]] | None = None,
) -> Callable:
    """Raise more idiomatic exceptions from a function that returns a WIT ``result``.

    A ``result``s error case is always wrapped in a generic ``Err`` exception by
    componentize-py. Convert that to a more descriptive exception that can be
    selectively caught.

    :arg idiomatic_exceptions: A map of the types of WIT-level ``Err.value``s to
        more informative exception classes. These classes receive the
        ``Err.value`` as a constructor argument. If the value's type is not
        found in the map, wrap it in an ``UnexpectedFastlyError``.

        Enum members may also be used as mapping keys. Exceptions raised based
        on these receive no constructor arguments, since the values of enum
        members are generated and meaningless.

    Goals: Be idiomatic. Be reasonably efficient. Be readable as documentation.
    In that order.

    """
    # Someday, if we need more flexibility than class-by-class mapping, we can
    # take a fallback callable that can do further thinking. Also, only the type
    # signature keeps you from passing along an arbitrary callable that can
    # emit, say, different exception classes for even and odd ints.
    if idiomatic_exceptions is None:
        idiomatic_exceptions = {}

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Err as e:
                error_value = e.value

                # Look up ordinary instances by class but enum fields by value so
                # we can easily give each enum member its own exception class:
                if isinstance(error_value, Enum):
                    key = error_value
                    exc_args = ()
                else:
                    key = type(error_value)
                    exc_args = (error_value,)
                idiomatic_exception = idiomatic_exceptions.get(
                    key, UnexpectedFastlyError
                )
                raise idiomatic_exception(*exc_args) from e

        return wrapper

    return decorator
