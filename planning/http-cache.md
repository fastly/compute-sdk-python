# HTTP Cache API Design

## Overview

Design for the HTTP Cache API, which allows caching of full HTTP responses (transactional caching). This is distinct from the Core Cache API which caches byte streams.

## WIT Interface Reference

```wit
interface http-cache {
  use http-req.{request};
  use http-resp.{response, response-with-body};
  use http-body.{body};

  resource entry {
    transaction-lookup: static func(
      req-handle: borrow<request>,
      options: lookup-options,
    ) -> result<entry, error>;

    transaction-insert: func(
      resp-handle: response,
      options: write-options,
    ) -> result<body, error>;

    transaction-insert-and-stream-back: func(
      resp-handle: response,
      options: write-options,
    ) -> result<tuple<body, entry>, error>;

    transaction-update: func(
      resp-handle: response,
      options: write-options,
    ) -> result<_, error>;
  }
}
```

Generated stubs: `stubs/wit_world/imports/http_cache.py`

## API Design

```python
from typing import Optional
from dataclasses import dataclass

@dataclass
class HttpCacheOptions:
    max_age_ns: int = 0
    # ... other options similar to Core Cache but for HTTP

class HttpCacheEntry:
    """Transaction handle for HTTP Cache."""
    
    @staticmethod
    def lookup(request: 'Request', options: Optional[HttpCacheOptions] = None) -> 'HttpCacheEntry':
        pass
        
    def insert(self, response: 'Response', options: Optional[HttpCacheOptions] = None) -> 'Body':
        """Insert response into cache and return a body stream for writing the payload."""
        pass
        
    def insert_and_stream_back(self, response: 'Response') -> tuple['Body', 'HttpCacheEntry']:
        pass
```

## Usage Examples

```python
from fastly_compute import HttpCacheEntry, Request

req = Request("GET", "https://example.com/api")
entry = HttpCacheEntry.lookup(req)

if entry.state == "must-insert-or-update":
    # Fetch from backend
    backend_resp = fetch(req)
    
    # Insert into cache
    writer = entry.insert(backend_resp)
    writer.write(backend_resp.body.read())
    writer.close()
    
    return Response(body=entry.get_body())
```

## Deferred Features

- **Complex Updates**: Advanced transaction update scenarios.

## Implementation Notes

1.  **Response Handling**: The `insert` method consumes the `Response` object (its headers/metadata) but returns a `Body` for the data.
