"""Internal base class for Fastly resource wrappers

This module provides an internal generic base class for wrapping WIT binding
resources with consistent lifecycle management and context manager protocol.

**Note**: This module is for internal SDK use only. End users should not
need to import or use these classes directly. Instead, use the public resource
classes like ConfigStore, RateCounter, PenaltyBox, and LogEndpoint.
"""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self


class WitResource(Protocol):
    """Internal protocol for WIT-generated resource types.

    This protocol defines the context manager interface that all WIT resources
    must implement for resource lifecycle management.
    """

    def __enter__(self) -> Self:
        """Enter the context manager."""
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        """Exit the context manager and release resources."""
        ...


class FastlyResource[T: WitResource]:
    """Internal base class for Fastly resource wrappers.

    This generic base class provides consistent context manager protocol and
    resource lifecycle management for all Fastly resource types that wrap
    WIT bindings (e.g., ConfigStore, RateCounter, PenaltyBox, LogEndpoint).

    The type parameter T represents the underlying WIT binding resource type
    and must satisfy the WitResource protocol (context manager support).
    """

    def __init__(self, wit_resource: T):
        """Initialize the resource wrapper with an inner WIT binding.

        :param wit_resource: The underlying WIT binding resource to wrap
        """
        self._wit_resource = wit_resource

    def close(self) -> None:
        """Explicitly close the resource, releasing its resources.

        This is called automatically when using the resource as a context
        manager. If not called explicitly, resources will eventually be freed
        by the garbage collector.

        Note: Attempting to use the resource after it is closed will result
        in a trap.
        """
        self._wit_resource.__exit__(None, None, None)

    def __enter__(self) -> Self:
        """Context manager entry.

        Allows use of the resource in a 'with' statement.

        Example::

            with Resource.open("foo") as foo:
                value = foo.bar("baz")
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit.

        Use of the context manager will free up the underlying host resource on
        exit. Referencing the resource after context manager exit will result in
        a trap.

        Exception information from the context is passed through to the inner
        resource's __exit__ method for proper cleanup.

        :param exc_type: Exception type if an exception occurred, None otherwise
        :param exc_val: Exception value if an exception occurred, None otherwise
        :param exc_tb: Exception traceback if an exception occurred, None otherwise
        """
        self._wit_resource.__exit__(exc_type, exc_val, exc_tb)
