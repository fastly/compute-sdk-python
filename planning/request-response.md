# Request & Response API Design

## Overview

Design for comprehensive HTTP Request and Response handling in the Fastly Compute Python SDK.

## WIT Interface Reference

The design is based on `http-req`, `http-resp`, and `http-downstream` interfaces in `wit/deps/fastly/compute.wit`.

## API Design

```python
from typing import Optional, Dict, List, Tuple, Any
from enum import Enum

class HttpVersion(Enum):
    HTTP_09 = "HTTP/0.9"
    HTTP_10 = "HTTP/1.0"
    HTTP_11 = "HTTP/1.1"
    H2 = "HTTP/2"
    H3 = "HTTP/3"

class Request:
    def __init__(self, method: str = "GET", url: str = "", headers: Optional[Dict[str, str]] = None, body: Optional[bytes] = None):
        pass
    
    @property
    def method(self) -> str: pass
    
    @method.setter
    def method(self, value: str) -> None: pass
    
    @property
    def url(self) -> str: pass
    
    @url.setter
    def url(self, value: str) -> None: pass
    
    @property
    def version(self) -> HttpVersion: pass
    
    @version.setter
    def version(self, value: HttpVersion) -> None: pass
    
    @property
    def headers(self) -> 'Headers': pass
    
    @property
    def body(self) -> 'Body': pass
    
    def read(self) -> bytes: pass
    
    def text(self, encoding: str = 'utf-8') -> str: pass
    
    def json(self) -> Any: pass
    
    def set_cache_override(self, ttl: Optional[int] = None, stale_while_revalidate: Optional[int] = None, pci: bool = False, surrogate_key: Optional[str] = None) -> None: pass
    
    def set_auto_decompress(self, gzip: bool = True) -> None: pass
    
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): pass

class DownstreamRequest(Request):
    """Represents a downstream (client) request with additional metadata."""
    
    @property
    def client_ip(self) -> Optional[str]: pass
    
    @property
    def server_ip(self) -> Optional[str]: pass
    
    @property
    def client_request_id(self) -> Optional[str]: pass
    
    @property
    def tls_cipher(self) -> Optional[str]: pass
    
    @property
    def tls_protocol(self) -> Optional[str]: pass
    
    @property
    def tls_client_hello(self) -> Optional[bytes]: pass
    
    @property
    def tls_client_certificate(self) -> Optional[str]: pass
    
    @property
    def tls_server_name(self) -> Optional[str]: pass
    
    @property
    def tls_ja3_md5(self) -> Optional[bytes]: pass
    
    @property
    def tls_ja4(self) -> Optional[str]: pass
    
    @property
    def h2_fingerprint(self) -> Optional[str]: pass
    
    @property
    def header_fingerprint(self) -> Optional[str]: pass
    
    @property
    def ddos_detected(self) -> bool: pass
    
    @property
    def compliance_region(self) -> Optional[str]: pass

class Response:
    def __init__(self, status: int = 200, headers: Optional[Dict[str, str]] = None, body: Optional[bytes] = None):
        pass
    
    @property
    def status(self) -> int: pass
    
    @status.setter
    def status(self, value: int) -> None: pass
    
    @property
    def version(self) -> HttpVersion: pass
    
    @version.setter
    def version(self, value: HttpVersion) -> None: pass
    
    @property
    def headers(self) -> 'Headers': pass
    
    @property
    def body(self) -> 'Body': pass
    
    @property
    def content(self) -> bytes: pass
    
    @property
    def text(self) -> str: pass
    
    def json(self) -> Any: pass
    
    @property
    def remote_ip(self) -> Optional[str]: pass
    
    @property
    def remote_port(self) -> Optional[int]: pass
    
    def send_downstream(self, streaming: bool = False) -> None: pass
    
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): pass

class Headers:
    def __getitem__(self, key: str) -> str: pass
    def __setitem__(self, key: str, value: str) -> None: pass
    def __delitem__(self, key: str) -> None: pass
    def __contains__(self, key: str) -> bool: pass
    def __iter__(self): pass
    def __len__(self) -> int: pass
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]: pass
    def get_all(self, key: str) -> List[str]: pass
    def set_all(self, key: str, values: List[str]) -> None: pass
    def append(self, key: str, value: str) -> None: pass
    def items(self) -> List[Tuple[str, str]]: pass
    def keys(self) -> List[str]: pass
    def values(self) -> List[str]: pass

class Body:
    @classmethod
    def empty(cls) -> 'Body': pass
    
    def read(self, size: Optional[int] = None) -> bytes: pass
    def write(self, data: bytes) -> int: pass
    def write_str(self, text: str, encoding: str = 'utf-8') -> int: pass
    def append(self, other: 'Body') -> None: pass
    def close(self) -> None: pass
    
    @property
    def known_length(self) -> Optional[int]: pass
    
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): self.close()
```

## High-Level API

```python
def send_request(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[bytes] = None,
    backend: str = "default",
    timeout: Optional[int] = None,
) -> Response:
    pass

def get(url: str, **kwargs) -> Response: pass
def post(url: str, body: Optional[bytes] = None, **kwargs) -> Response: pass
def put(url: str, body: Optional[bytes] = None, **kwargs) -> Response: pass
def delete(url: str, **kwargs) -> Response: pass
```

## Deferred Features

- **Streaming Request Body**: Full streaming support for outgoing requests is deferred.
- **WebSocket**: WebSocket upgrade support is deferred.
- **Trailer Support**: Full trailer manipulation is deferred.

## Implementation Plan

### 1. Core Module (`fastly_compute._core`)

Create a new internal module (or `fastly_compute.http` if exposed) to house the canonical implementations of the core HTTP objects. This module will depend directly on the WIT bindings.

- **`Body`**: Wraps `http_body.Body`. Implements streaming read/write.
- **`Headers`**: Wraps header logic. Handles case-insensitivity and multi-value storage.
- **`Request`**: Wraps `http_req.Request`. Can be initialized from WIT handle (incoming) or from scratch (outgoing).
- **`Response`**: Wraps `http_resp.Response`. Can be initialized from WIT handle (incoming from backend) or from scratch (outgoing to client).

### 2. Integration with `fastly_compute.requests`

The existing `requests` facade is valuable and should remain the primary high-level API for making backend requests.

- **Refactor**: Update `fastly_compute.requests.request()` to use the new `fastly_compute.http.Request` object internally for constructing the request.
- **Response Wrapper**: `fastly_compute.requests.FastlyResponse` can either inherit from `fastly_compute.http.Response` or wrap it, adding the specific `requests`-compatible API (like `raise_for_status`, `json()` helper).

### 3. WSGI Adapter Update

Update `fastly_compute.wsgi` to use the new core objects.

- **Incoming Request**: Construct a `fastly_compute.http.Request` from the incoming WIT handle.
- **Outgoing Response**: Construct a `fastly_compute.http.Response` from the WSGI app's output, then send it using `send_downstream`.

### 4. Backward Compatibility

- Ensure `fastly_compute.requests` public API remains unchanged.
- `fastly_compute.wsgi.WsgiHttpIncoming` should remain the entry point for WSGI apps.

