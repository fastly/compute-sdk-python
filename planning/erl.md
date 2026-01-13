# Edge Rate Limiting (ERL) API Design

## Overview

Design for Edge Rate Limiting, providing rate counters and penalty boxes to control traffic.

## WIT Interface Reference

```wit
interface erl {
  use types.{error, open-error};

  resource rate-counter {
    open: static func(name: string) -> result<rate-counter, open-error>;
    get-name: func() -> string;
    check-rate: func(
      entry: string,
      delta: u32,
      window: u32,
      limit: u32,
      penalty-box: borrow<penalty-box>,
      ttl: u32,
    ) -> result<bool, error>;
    increment: func(entry: string, delta: u32) -> result<_, error>;
    lookup-rate: func(entry: string, window: u32) -> result<u32, error>;
    lookup-count: func(entry: string, duration: u32) -> result<u32, error>;
  }

  resource penalty-box {
    open: static func(name: string) -> result<penalty-box, open-error>;
    get-name: func() -> string;
    add: func(entry: string, ttl: u32) -> result<_, error>;
    has: func(entry: string) -> result<bool, error>;
  }
}
```

Generated stubs: `stubs/wit_world/imports/erl.py`

## API Design

```python
from typing import Optional

class PenaltyBox:
    """A penalty box for temporarily blocking entries."""
    
    @classmethod
    def open(cls, name: str) -> 'PenaltyBox': pass
    
    @property
    def name(self) -> str: pass
    
    def add(self, entry: str, ttl: int) -> None:
        """Add an entry to the penalty box for a duration (in minutes)."""
        pass
    
    def has(self, entry: str) -> bool:
        """Check if an entry is in the penalty box."""
        pass
    
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): pass

class RateCounter:
    """A counter for tracking request rates."""
    
    @classmethod
    def open(cls, name: str) -> 'RateCounter': pass
    
    @property
    def name(self) -> str: pass
    
    def check_rate(
        self,
        entry: str,
        delta: int,
        window: int,
        limit: int,
        penalty_box: PenaltyBox,
        ttl: int
    ) -> bool:
        """Check rate and potentially add to penalty box.
        
        Args:
            entry: The key to check (e.g., IP address)
            delta: Amount to increment by
            window: Time window in seconds (10 or 60)
            limit: Request limit
            penalty_box: Penalty box to add to if limit exceeded
            ttl: Duration to penalize in minutes
            
        Returns:
            True if penalized, False otherwise
        """
        pass
    
    def increment(self, entry: str, delta: int = 1) -> None:
        """Increment the counter for an entry."""
        pass
    
    def lookup_rate(self, entry: str, window: int) -> int:
        """Look up current rate (RPS) for a window."""
        pass
    
    def lookup_count(self, entry: str, duration: int) -> int:
        """Look up total count for a duration."""
        pass
    
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): pass
```

## Usage Examples

```python
from fastly_compute import RateCounter, PenaltyBox

# Open resources
rc = RateCounter.open("requests")
pb = PenaltyBox.open("abuse")

client_ip = "192.0.2.1"

# check_rate atomically increments and checks against limit
# If rate > 100 rps over 60s window, add to penalty box for 10 minutes
is_blocked = rc.check_rate(
    entry=client_ip,
    delta=1,
    window=60,
    limit=100,
    penalty_box=pb,
    ttl=10
)

if is_blocked:
    return Response(status=429, body=b"Rate limit exceeded")

# Check penalty box directly (e.g. for previously blocked clients)
if pb.has(client_ip):
    return Response(status=429, body=b"You are in the penalty box")
```

## Deferred Features

- **Async Support**: Operations are synchronous.
- **Complex Policies**: The SDK provides low-level primitives; higher-level policies (e.g., sliding window logic) are left to user implementation if not covered by `check_rate`.

## Implementation Notes

1. **TTL Units**: Note that TTLs for `check_rate` and `add` are in **minutes**, while windows are in **seconds**.
2. **Window Limits**: Valid windows are typically 1s, 10s, 60s depending on platform configuration.
