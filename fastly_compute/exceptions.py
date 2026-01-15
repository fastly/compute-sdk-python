"""Top-level exceptions emitted by the Fastly API"""

from collections.abc import Callable, Mapping
from enum import Enum
from functools import wraps
from typing import Any

from wit_world.imports.types import Err


class FastlyError(Exception):
    """Abstract base class for all errors raised by Fastly APIs

    This allows catching all errors emanating from Fastly APIs at once.
    """


class UnexpectedFastlyError(FastlyError):
    """An error arising from a Fastly API but of an unanticipated kind, such
    that we merely package up the low-level error and send it along.

    Any of these encountered in the wild means we neglected to keep our Python
    wrappers up to date with the WIT.
    """

    def __init__(self, error_value: object):
        """Construct.

        :arg error_value: The ``value`` attr of the raised ``Err``
        """
        self.value = error_value


# TODO: Move to somewhere more private once it becomes clear where.
def nice_exceptions(
    nice_classes: Mapping[Any, type[FastlyError]] | None = None,
) -> Callable:
    """Raise more idiomatic exceptions from a function that returns a WIT ``result``.

    A ``result``s error case is always wrapped in a generic ``Err`` exception by
    componentize-py. Convert that to a more descriptive exception that can be
    selectively caught.

    :arg nice_classes: A map of the types of WIT-level ``Err.value``s to more
        informative exception classes. These classes receive the ``Err.value``
        as a constructor argument. If the value's type is not found in the map,
        wrap it in an ``UnexpectedFastlyError``.

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
    if nice_classes is None:
        nice_classes = {}

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
                idiomatic_class = nice_classes.get(key, UnexpectedFastlyError)
                raise idiomatic_class(*exc_args) from e

        return wrapper

    return decorator
