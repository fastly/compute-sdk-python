# Async Python on Fastly Compute

## Overview

Analysis of asynchronous Python support on Fastly Compute, leveraging the `async-io` host interface.

## Reference Architecture

The **Spin Python SDK** provides a strong reference implementation for running `asyncio` on WASI-based platforms that lack full OS-level socket support but provide pollable host resources.

- **Reference**: `spin_sdk.http.poll_loop`
- **Mechanism**: Custom `asyncio.AbstractEventLoop` backed by host-side polling (`wasi:io/poll` in Spin, `fastly:compute/async-io` in Fastly).

## Fastly Async Primitives

The `compute.wit` defines the `async-io` interface:

```wit
interface async-io {
  resource pollable { ... }
  select: func(handles: list<borrow<pollable>>) -> u32;
  select-with-timeout: func(handles: list<borrow<pollable>>, timeout-ms: u32) -> option<u32>;
}
```

Pollable resources include:
- `pending-response` (from `http-req.send-async`)
- `body` (HTTP bodies for streaming)
- `pending-lookup`, `pending-insert` (KV Store)
- `pending-entry` (Cache)

## Proposed Architecture

### 1. FastlyEventLoop

A custom event loop that implements `asyncio.AbstractEventLoop`.

- **Registry**: Maintains a mapping of `pollable` handles to Python `Future`s (wakers).
- **Run Loop**:
    1. Executed synchronous tasks (`_run_once`).
    2. Collects all active `pollable` handles.
    3. Calls `async_io.select(handles)`.
    4. Wakes up the corresponding Future for the ready handle.
- **Restrictions**: Methods relying on OS sockets (`create_connection`, `add_reader` for file descriptors) will raise `NotImplementedError`.

### 2. Async Primitives

We must provide async-native wrappers for host calls:

```python
async def send_async(request):
    pending = http_req.send_async(request)
    await wait_for(pending)  # Registers with loop and yields
    return pending.wait()
```

## Candidate Features for Async

| Feature | Async Benefit | Status |
| :--- | :--- | :--- |
| **Backend Requests** | **High**. Allows concurrent fetches (fan-out). | `send-async` exists. |
| **KV Store** | **High**. Non-blocking lookups. | `lookup-async` exists. |
| **Cache** | **Medium**. | `transaction-lookup-async` exists. |
| **Body Streaming** | **High**. Non-blocking read/write of streams. | Bodies are pollable. |
| **WebSockets** | **High**. Essential for websocket handling. | Future consideration. |

## ASGI Support

With `FastlyEventLoop`, we can support **ASGI** applications (FastAPI, Starlette, Quart).

- **Adapter**: `AsgiHttpIncoming` (similar to `WsgiHttpIncoming`).
- **Lifecycle**: Manages the ASGI `scope`, `receive`, and `send` channels mapping to Fastly Request/Response/Body.

## Risks & Challenges

1.  **Socket Incompatibility**: Standard Python async libraries (e.g., `asyncpg`, `redis`, `aiohttp`) rely on `selector` based loops and TCP sockets. They **will not work** out of the box. Users must use Fastly-native clients (KV Store, Backend fetch) instead.
2.  **Performance**: The overhead of the Python event loop in Wasm needs measurement.
3.  **Maintenance**: Custom event loops are complex to maintain and ensure correctness against stdlib changes.

## Roadmap

1.  **Phase 1 (PoC)**: Implement `FastlyEventLoop` and a simple `async_sleep` (using `select_with_timeout`).
2.  **Phase 2 (HTTP)**: Implement `AsyncClient` for backend requests.
3.  **Phase 3 (ASGI)**: Prototype a simple ASGI adapter for FastAPI.
