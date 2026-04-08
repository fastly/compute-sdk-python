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

from fastly_compute._bindings.erl import PenaltyBox as _PenaltyBox
from fastly_compute._bindings.erl import RateCounter as _RateCounter


class RateCounter(_RateCounter):
    """Interface to Fastly Edge Rate Limiter counter.

    Rate counters track request counts and calculate rates for rate limiting
    decisions.

    Example::

        with RateCounter.open("api-counter") as counter:
            counter.increment("192.168.1.1", delta=1)
            rate = counter.lookup_rate("192.168.1.1", window=60)
    """


class PenaltyBox(_PenaltyBox):
    """Interface to Fastly Edge Rate Limiter penalty box.

    Penalty boxes maintain a set of blocked entries (e.g., IP addresses).

    Example::

        with PenaltyBox.open("blocklist") as penalty:
            penalty.add("192.168.1.1", ttl=600)
            if "192.168.1.1" in penalty:
                return Response("Blocked", status=403)
    """

    def __contains__(self, entry: str) -> bool:
        """Check if entry is in the penalty box using the ``in`` operator.

        :param entry: Identifier to check
        :return: True if the entry is blocked, False otherwise
        :raises ~fastly_compute.exceptions.FastlyError: on invalid inputs or other error conditions.

        Example::

            with PenaltyBox.open("blocklist") as penalty:
                if "192.168.1.1" in penalty:
                    return Response("Blocked", status=403)
        """
        return self.has(entry)


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
        :param window: Time window in seconds for rate calculation
        :param limit: Maximum requests per second allowed
        :param ttl: Time-to-live in seconds for penalty box entry. The host validates
                    this parameter and rounds to the nearest minute; consult Fastly
                    documentation for valid range.
        :return: True if the entry is rate limited, False otherwise
        :raises ~fastly_compute.exceptions.FastlyError

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
