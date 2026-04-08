"""Integration tests for Edge Rate Limiting functionality."""

import pytest

from fastly_compute.erl import EdgeRateLimiter, PenaltyBox, RateCounter
from fastly_compute.exceptions.types.open_error import NotFound
from fastly_compute.testing import AutoViceroyTestBase, on_viceroy


class TestRateCounter(AutoViceroyTestBase):
    """Rate counter integration tests."""

    VICEROY_CONFIG = {
        "local_server": {
            "rate_counters": {"test-counter": {}},
            "penalty_boxes": {"test-penalty": {}},
        }
    }

    @on_viceroy
    def rate_counter_increment(cls, counter_name, entry, delta):
        """Increment a counter and return None (no error)."""
        with RateCounter.open(counter_name) as counter:
            counter.increment(entry, delta)

    @on_viceroy
    def rate_counter_lookup_rate(cls, counter_name, entry, window):
        """Lookup rate for an entry."""
        with RateCounter.open(counter_name) as counter:
            return counter.lookup_rate(entry, window)

    @on_viceroy
    def rate_counter_lookup_count(cls, counter_name, entry, duration):
        """Lookup count for an entry."""
        with RateCounter.open(counter_name) as counter:
            return counter.lookup_count(entry, duration)

    @on_viceroy
    def rate_counter_check_rate(
        cls, counter_name, penalty_name, entry, delta, window, limit, ttl
    ):
        """Check rate with penalty box."""
        with RateCounter.open(counter_name) as counter:
            with PenaltyBox.open(penalty_name) as penalty:
                return counter.check_rate(entry, delta, window, limit, penalty, ttl)

    @on_viceroy
    def penalty_box_add(cls, penalty_name, entry, ttl):
        """Add entry to penalty box."""
        with PenaltyBox.open(penalty_name) as penalty:
            penalty.add(entry, ttl)
            return None

    @on_viceroy
    def penalty_box_contains(cls, penalty_name, entry):
        """Check if entry is in penalty box using __contains__."""
        with PenaltyBox.open(penalty_name) as penalty:
            return entry in penalty

    @on_viceroy
    def edge_rate_limiter_check_rate(
        cls, counter_name, penalty_name, entry, delta, window, limit, ttl
    ):
        """Check rate using EdgeRateLimiter convenience wrapper."""
        counter = RateCounter.open(counter_name)
        penalty = PenaltyBox.open(penalty_name)
        erl = EdgeRateLimiter(counter, penalty)
        return erl.check_rate(entry, delta, window, limit, ttl)

    @pytest.mark.xfail(
        reason="Viceroy's ERL implementation does not validate resource existence"
    )
    def test_open_nonexistent_counter(self):
        """Test opening a non-existent rate counter raises error."""
        with pytest.raises(NotFound):
            self.rate_counter_increment("nonexistent", "192.168.1.1", 1)

    def test_increment(self):
        """Test incrementing a counter."""
        result = self.rate_counter_increment("test-counter", "192.168.1.1", 1)
        assert result is None  # No error

    def test_lookup_rate(self):
        """Test looking up rate."""
        # Viceroy returns 0, but we verify the API works
        rate = self.rate_counter_lookup_rate("test-counter", "192.168.1.1", 60)
        assert rate == 0  # Viceroy stub returns 0

    def test_lookup_count(self):
        """Test looking up count."""
        # Viceroy returns 0, but we verify the API works
        count = self.rate_counter_lookup_count("test-counter", "192.168.1.1", 30)
        assert count == 0  # Viceroy stub returns 0

    def test_check_rate(self):
        """Test checking rate with penalty box."""
        # Viceroy returns False, but we verify the API works
        is_limited = self.rate_counter_check_rate(
            "test-counter", "test-penalty", "192.168.1.1", 1, 10, 100, 300
        )
        assert is_limited is False  # Viceroy stub returns False

    @pytest.mark.xfail(
        reason="Viceroy's ERL implementation does not validate resource existence"
    )
    def test_open_nonexistent_penalty_box(self):
        """Test opening a non-existent penalty box raises error."""
        with pytest.raises(NotFound):
            self.penalty_box_add("nonexistent", "192.168.1.1", 600)

    def test_pb_add(self):
        """Test adding entry to penalty box."""
        result = self.penalty_box_add("test-penalty", "192.168.1.1", 600)
        assert result is None  # No error

    def test_pb_contains(self):
        """Test checking if entry is in penalty box using 'in' operator."""
        # Viceroy returns False, but we verify the API works
        is_blocked = self.penalty_box_contains("test-penalty", "192.168.1.1")
        assert is_blocked is False  # Viceroy stub always returns False

    def test_edge_rate_limiter_check_rate(self):
        """Test EdgeRateLimiter convenience wrapper."""
        # Viceroy returns False, but we verify the API works
        is_limited = self.edge_rate_limiter_check_rate(
            "test-counter", "test-penalty", "192.168.1.1", 1, 10, 100, 300
        )
        assert is_limited is False  # Viceroy stub always returns False
