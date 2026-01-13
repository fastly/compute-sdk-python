# Trailers API Design

## Overview

Design for handling HTTP Trailers in Request and Response bodies.

## WIT Interface Reference

```wit
interface http-body {
  resource body {
    append-trailer: func(name: string, value: list<u8>) -> result<_, error>;
    get-trailer-names: func(max-len: u64, cursor: u32) -> result<tuple<string, option<u32>>, trailer-error>;
    get-trailer-value: func(name: string, max-len: u64) -> result<option<list<u8>>, trailer-error>;
    get-trailer-values: func(name: string, max-len: u64, cursor: u32) -> result<tuple<list<u8>, option<u32>>, trailer-error>;
  }
  
  variant trailer-error {
    in-progress,
    generic-error
  }
}
```

Generated stubs: `stubs/wit_world/imports/http_body.py`

## API Design

Trailers are attached to the `Body` object.

```python
from typing import Optional, Dict, List

class Body:
    # Existing methods...
    
    def append_trailer(self, name: str, value: str) -> None:
        """Append a trailer to the body."""
        pass
        
    def get_trailer(self, name: str) -> Optional[str]:
        """Get a trailer value."""
        pass
        
    def get_trailers(self) -> Dict[str, str]:
        """Get all trailers."""
        pass
```

## Usage Examples

```python
from fastly_compute import Response, Body

def handle_request(req):
    # Sending trailers
    body = Body()
    body.write(b"Chunk 1")
    body.write(b"Chunk 2")
    body.append_trailer("Server-Timing", "cpu;dur=2.4")
    
    return Response(body=body)

# Reading trailers requires consuming the body
def read_trailers(resp):
    data = resp.body.read() 
    timing = resp.body.get_trailer("Server-Timing")
```

## Deferred Features

- **Async Trailers**: Reading trailers asynchronously while streaming body.

## Implementation Notes

1.  **Trailer Availability**: Trailers are only available after the body has been fully read (for incoming) or before it's closed (for outgoing).
