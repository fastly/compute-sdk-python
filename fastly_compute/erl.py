"""Edge Rate Limiting API for Fastly Compute

This module provides access to Fastly's Edge Rate Limiting (ERL) feature,
which allows you to count requests and enforce rate limits at the edge.

For more information about Edge Rate Limiting, see the
`Fastly ERL documentation <https://docs.fastly.com/products/edge-rate-limiting>`_.

Example::

    from fastly_compute.erl import RateCounter, PenaltyBox

    # Basic rate limiting
    with RateCounter.open("api-counter") as counter:
        with PenaltyBox.open("api-penalty") as penalty:
            is_limited = counter.check_rate(
                entry="192.168.1.1",
                delta=1,
                window=10,
                limit=100,
                penalty_box=penalty,
                ttl=300
            )
            if is_limited:
                # Client exceeded rate limit
                return Response("Rate limited", status=429)

    # Standalone usage
    with RateCounter.open("tracker") as counter:
        counter.increment("client-ip", delta=1)
        current_rate = counter.lookup_rate("client-ip", window=60)

    with PenaltyBox.open("blocklist") as penalty:
        penalty.add("abusive-ip", ttl=600)
        if "abusive-ip" in penalty:
            return Response("Blocked", status=403)
"""

from __future__ import annotations

from typing import Self

from wit_world.imports import erl as wit_erl


class RateCounter:
    """Interface to Fastly Edge Rate Limiter counter.

    Rate counters track request counts and calculate rates for rate limiting
    decisions.

    Example::

        with RateCounter.open("api-counter") as counter:
            counter.increment("192.168.1.1", delta=1)
            rate = counter.lookup_rate("192.168.1.1", window=60)
    """

    def __init__(self, counter: wit_erl.RateCounter):
        """Private constructor. Use RateCounter.open() instead."""
        self._counter = counter

    @classmethod
    def open(cls, name: str) -> Self:
        """Open a rate counter by name.

        :param name: The name of the rate counter
        :return: RateCounter instance
        :raises ~fastly_compute.exceptions.types.open_error.NotFound: If the rate counter doesn't exist
        :raises ~fastly_compute.exceptions.types.open_error.InvalidSyntax: If the name is invalid
        :raises ~fastly_compute.exceptions.types.open_error.NameTooLong: If the name is too long

        Example::

            counter = RateCounter.open("my-counter")
        """
        counter = wit_erl.RateCounter.open(name)
        return cls(counter)

    def get_name(self) -> str:
        """Return the name of this rate counter.

        :return: The name of the rate counter
        """
        return self._counter.get_name()

    def check_rate(
        self,
        entry: str,
        delta: int,
        window: int,
        limit: int,
        penalty_box: PenaltyBox,
        ttl: int,
    ) -> bool:
        """Check if entry exceeds rate limit and penalize if necessary.

        Increments the counter for the entry and checks if the average requests
        per second (RPS) over the specified window exceeds the limit. If the
        limit is exceeded, the entry is added to the penalty box for the
        specified time-to-live.

        :param entry: Identifier for the client (e.g., IP address)
        :param delta: Amount to increment the counter by
        :param window: Time window in seconds for rate calculation. The host validates
                       this parameter; consult Fastly documentation for valid values.
        :param limit: Maximum requests per second allowed
        :param penalty_box: Penalty box to add entry to if rate limited
        :param ttl: Time-to-live in seconds for penalty box entry. The host validates
                    this parameter and rounds to the nearest minute; consult Fastly
                    documentation for valid range.
        :return: True if the entry is rate limited, False otherwise
        :raises ~fastly_compute.exceptions.types.error.InvalidArgument: If parameters are invalid
        :raises ~fastly_compute.exceptions.types.error.GenericError: If an unexpected error occurs

        Example::

            with RateCounter.open("api-limiter") as counter:
                with PenaltyBox.open("api-penalty") as penalty:
                    # Check 100 req/sec over 10 second window
                    is_limited = counter.check_rate(
                        entry="192.168.1.1",
                        delta=1,
                        window=10,
                        limit=100,
                        penalty_box=penalty,
                        ttl=300
                    )
        """
        return self._counter.check_rate(
            entry, delta, window, limit, penalty_box._box, ttl
        )

    def increment(self, entry: str, delta: int) -> None:
        """Increment the counter for an entry.

        :param entry: Identifier to increment (e.g., IP address)
        :param delta: Amount to increment the counter by
        :raises ~fastly_compute.exceptions.types.error.InvalidArgument: If parameters are invalid
        :raises ~fastly_compute.exceptions.types.error.GenericError: If an unexpected error occurs

        Example::

            with RateCounter.open("tracker") as counter:
                counter.increment("192.168.1.1", delta=1)
        """
        self._counter.increment(entry, delta)

    def lookup_rate(self, entry: str, window: int) -> int:
        """Get the current rate for an entry over a time window.

        :param entry: Identifier to look up
        :param window: Time window in seconds. The host validates this parameter;
                       consult Fastly documentation for valid values.
        :return: Current rate (requests per second) for the entry
        :raises ~fastly_compute.exceptions.types.error.InvalidArgument: If parameters are invalid
        :raises ~fastly_compute.exceptions.types.error.GenericError: If an unexpected error occurs

        Example::

            with RateCounter.open("tracker") as counter:
                rate = counter.lookup_rate("192.168.1.1", window=60)
        """
        return self._counter.lookup_rate(entry, window)

    def lookup_count(self, entry: str, duration: int) -> int:
        """Get the total count for an entry over a duration.

        :param entry: Identifier to look up
        :param duration: Duration in seconds. The host validates this parameter;
                         consult Fastly documentation for valid values.
        :return: Total count for the entry over the duration
        :raises ~fastly_compute.exceptions.types.error.InvalidArgument: If parameters are invalid
        :raises ~fastly_compute.exceptions.types.error.GenericError: If an unexpected error occurs

        Example::

            with RateCounter.open("tracker") as counter:
                count = counter.lookup_count("192.168.1.1", duration=30)
        """
        return self._counter.lookup_count(entry, duration)

    def close(self) -> None:
        """Explicitly close the rate counter, releasing its resources.

        This is called automatically when using the rate counter as a context
        manager. If not called explicitly, resources will eventually be freed
        by the garbage collector.

        Note: Attempting to use the rate counter after it is closed will result
        in a trap.
        """
        self._counter.__exit__(None, None, None)

    def __enter__(self) -> Self:
        """Context manager entry.

        Allows use of RateCounter in a 'with' statement.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit.

        Use of the context manager will free up the underlying host resource on
        exit. Referencing the resource after context manager exit will result in
        a trap.
        """
        self.close()


class PenaltyBox:
    """Interface to Fastly Edge Rate Limiter penalty box.

    Penalty boxes maintain a set of blocked entries (e.g., IP addresses).

    Example::

        with PenaltyBox.open("blocklist") as penalty:
            penalty.add("192.168.1.1", ttl=600)
            if "192.168.1.1" in penalty:
                return Response("Blocked", status=403)
    """

    def __init__(self, box: wit_erl.PenaltyBox):
        """Private constructor. Use PenaltyBox.open() instead."""
        self._box = box

    @classmethod
    def open(cls, name: str) -> Self:
        """Open a penalty box by name.

        :param name: The name of the penalty box
        :return: PenaltyBox instance
        :raises ~fastly_compute.exceptions.types.open_error.NotFound: If the penalty box doesn't exist
        :raises ~fastly_compute.exceptions.types.open_error.InvalidSyntax: If the name is invalid
        :raises ~fastly_compute.exceptions.types.open_error.NameTooLong: If the name is too long

        Example::

            penalty = PenaltyBox.open("my-penalty-box")
        """
        box = wit_erl.PenaltyBox.open(name)
        return cls(box)

    def get_name(self) -> str:
        """Return the name of this penalty box.

        :return: The name of the penalty box
        """
        return self._box.get_name()

    def add(self, entry: str, ttl: int) -> None:
        """Add entry to the penalty box.

        :param entry: Identifier to block (e.g., IP address)
        :param ttl: Time-to-live in seconds. The host validates this parameter
                    and rounds to the nearest minute; consult Fastly documentation
                    for valid range.
        :raises ~fastly_compute.exceptions.types.error.InvalidArgument: If parameters are invalid
        :raises ~fastly_compute.exceptions.types.error.GenericError: If an unexpected error occurs

        Example::

            with PenaltyBox.open("blocklist") as penalty:
                penalty.add("192.168.1.1", ttl=600)  # Block for 10 minutes
        """
        self._box.add(entry, ttl)

    def __contains__(self, entry: str) -> bool:
        """Check if entry is in the penalty box using the 'in' operator.

        :param entry: Identifier to check
        :return: True if the entry is blocked, False otherwise
        :raises ~fastly_compute.exceptions.types.error.InvalidArgument: If parameters are invalid
        :raises ~fastly_compute.exceptions.types.error.GenericError: If an unexpected error occurs

        Example::

            with PenaltyBox.open("blocklist") as penalty:
                if "192.168.1.1" in penalty:
                    return Response("Blocked", status=403)
        """
        return self._box.has(entry)

    def close(self) -> None:
        """Explicitly close the penalty box, releasing its resources.

        This is called automatically when using the penalty box as a context
        manager. If not called explicitly, resources will eventually be freed
        by the garbage collector.

        Note: Attempting to use the penalty box after it is closed will result
        in a trap.
        """
        self._box.__exit__(None, None, None)

    def __enter__(self) -> Self:
        """Context manager entry.

        Allows use of PenaltyBox in a 'with' statement.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit.

        Use of the context manager will free up the underlying host resource on
        exit. Referencing the resource after context manager exit will result in
        a trap.
        """
        self.close()


class EdgeRateLimiter:
    """Convenience wrapper for edge rate limiting.

    Combines a :class:`RateCounter` and :class:`PenaltyBox` into a single
    interface for simplified rate limiting operations.

    :param rate_counter: Rate counter to use for counting
    :param penalty_box: Penalty box to use for blocking

    Example::

        counter = RateCounter.open("api-counter")
        penalty = PenaltyBox.open("api-penalty")
        erl = EdgeRateLimiter(counter, penalty)

        is_limited = erl.check_rate(
            entry="192.168.1.1",
            delta=1,
            window=10,
            limit=100,
            ttl=300
        )
    """

    def __init__(self, rate_counter: RateCounter, penalty_box: PenaltyBox):
        """Create an EdgeRateLimiter with a rate counter and penalty box.

        :param rate_counter: Rate counter to use for counting
        :param penalty_box: Penalty box to use for blocking
        """
        self._rate_counter = rate_counter
        self._penalty_box = penalty_box

    def check_rate(
        self, entry: str, delta: int, window: int, limit: int, ttl: int
    ) -> bool:
        """Check if entry exceeds rate limit and penalize if necessary.

        Increments the counter for the entry and checks if the average requests
        per second (RPS) over the specified window exceeds the limit. If the
        limit is exceeded, the entry is added to the penalty box for the
        specified time-to-live.

        :param entry: Identifier for the client (e.g., IP address)
        :param delta: Amount to increment the counter by
        :param window: Time window in seconds for rate calculation. The host validates
                       this parameter; consult Fastly documentation for valid values.
        :param limit: Maximum requests per second allowed
        :param ttl: Time-to-live in seconds for penalty box entry. The host validates
                    this parameter and rounds to the nearest minute; consult Fastly
                    documentation for valid range.
        :return: True if the entry is rate limited, False otherwise
        :raises ~fastly_compute.exceptions.types.error.InvalidArgument: If parameters are invalid
        :raises ~fastly_compute.exceptions.types.error.GenericError: If an unexpected error occurs

        Example::

            counter = RateCounter.open("api-counter")
            penalty = PenaltyBox.open("api-penalty")
            erl = EdgeRateLimiter(counter, penalty)

            is_limited = erl.check_rate(
                entry="192.168.1.1",
                delta=1,
                window=10,
                limit=100,
                ttl=300
            )
        """
        return self._rate_counter.check_rate(
            entry, delta, window, limit, self._penalty_box, ttl
        )
