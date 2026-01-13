# Cache API Design

## Overview

Design for the Core Cache API, providing access to Fastly's advanced caching capabilities including request collapsing, stale-while-revalidate, and streaming.

## WIT Interface Reference

```wit
interface cache {
  use types.{error};
  use http-body.{body};
  use http-req.{request};

  resource entry {
    lookup: static func(key: list<u8>, options: lookup-options) -> result<entry, error>;
    transaction-lookup: static func(key: list<u8>, options: lookup-options) -> result<entry, error>;
    transaction-insert: func(options: write-options) -> result<body, error>;
    transaction-update: func(options: write-options) -> result<_, error>;
    
    get-state: func() -> result<lookup-state, error>;
    get-user-metadata: func(max-len: u64) -> result<option<list<u8>>, error>;
    get-body: func(options: get-body-options) -> result<body, error>;
    get-length: func() -> result<option<object-length>, error>;
    get-max-age-ns: func() -> result<option<duration-ns>, error>;
    get-stale-while-revalidate-ns: func() -> result<option<duration-ns>, error>;
    get-age-ns: func() -> result<option<duration-ns>, error>;
    get-hits: func() -> result<option<cache-hit-count>, error>;
    transaction-cancel: func() -> result<_, error>;
  }

  record lookup-options {
    request-headers: option<borrow<request>>,
    always-use-requested-range: bool,
    extra: option<borrow<extra-lookup-options>>,
  }

  record write-options {
    max-age-ns: duration-ns,
    request: borrow<request>,
    vary: list<string>,
    initial-age-ns: duration-ns,
    stale-while-revalidate-ns: duration-ns,
    surrogate-keys: list<string>,
    length: object-length,
    user-metadata: list<u8>,
    sensitive-data: bool,
  }
}
```

Generated stubs: `stubs/wit_world/imports/cache.py`

## API Design

```python
from typing import Optional, List, Any
from dataclasses import dataclass
from enum import Enum

class LookupState(Enum):
    FOUND = "found"
    USABLE = "usable"
    STALE = "stale"
    MUST_INSERT_OR_UPDATE = "must-insert-or-update"

@dataclass
class LookupOptions:
    request_headers: Optional['Request'] = None
    
@dataclass
class WriteOptions:
    max_age_ns: int
    request: 'Request'
    vary: List[str]
    initial_age_ns: int = 0
    stale_while_revalidate_ns: int = 0
    surrogate_keys: List[str] = None
    length: int = 0
    user_metadata: bytes = b""
    sensitive_data: bool = False

class CacheEntry:
    """Represents a handle to a cache entry or transaction."""
    
    @staticmethod
    def lookup(key: str | bytes, options: Optional[LookupOptions] = None) -> 'CacheEntry': pass
    
    @staticmethod
    def transaction_lookup(key: str | bytes, options: Optional[LookupOptions] = None) -> 'CacheEntry': pass
    
    def insert(self, options: WriteOptions) -> 'Body':
        """Insert an object into the cache. Returns a writable body stream."""
        pass
    
    def update(self, options: WriteOptions) -> None:
        """Update metadata without changing the body."""
        pass
    
    def get_state(self) -> LookupState: pass
    
    def get_body(self) -> 'Body': pass
    
    @property
    def length(self) -> Optional[int]: pass
    
    @property
    def hits(self) -> Optional[int]: pass
    
    @property
    def age_ns(self) -> Optional[int]: pass
    
    def cancel(self) -> None: pass
    
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): pass

class SimpleCache:
    """Simplified synchronous cache API."""
    
    @staticmethod
    def get(key: str) -> Optional[bytes]: pass
    
    @staticmethod
    def set(key: str, value: bytes, ttl: int) -> None: pass
    
    @staticmethod
    def get_stream(key: str) -> Optional['Body']: pass
```

## Usage Examples

```python
from fastly_compute import CacheEntry, WriteOptions, LookupOptions

# Simple Lookup
entry = CacheEntry.lookup("my-key")
if entry.get_state() == "found":
    body = entry.get_body()
    data = body.read()

# Transaction (Read-Through Caching)
entry = CacheEntry.transaction_lookup("my-key")
if entry.get_state() == "must-insert-or-update":
    # Cache miss - fetch and insert
    backend_resp = fetch_from_backend(...)
    
    options = WriteOptions(
        max_age_ns=60_000_000_000, # 60s
        request=req,
        vary=[]
    )
    writer = entry.insert(options)
    writer.write(backend_resp.body.read())
    writer.close()
    
    # Return newly cached body
    return Response(body=entry.get_body())
else:
    # Cache hit
    return Response(body=entry.get_body())
```

## Deferred Features

- **Async Cache API**: `transaction-lookup-async` and other async variants are deferred for initial release.
- **Partial Updates**: Not supported by core API currently.

## Implementation Notes

1. **State Management**: `CacheEntry` encapsulates the state returned by `get-state`.
2. **Body Integration**: Uses the standard SDK `Body` class for streaming I/O.
3. **Strings/Bytes**: Keys can be string or bytes (auto-encoded).
