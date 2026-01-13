# WIT Resource Drop Design

## Overview

Design for managing the lifecycle of WIT resources (handles) in Python, ensuring they are properly dropped (released) on the host side.

## Problem

Fastly Compute resources (Bodies, KV Stores, etc.) are backed by host-side handles. If these handles are not explicitly dropped, they leak, potentially causing resource exhaustion or logic errors (e.g. infinite pending requests). Python's Garbage Collection (`__del__`) is non-deterministic and thus insufficient for timely resource release.

## Strategy

1.  **Context Managers**: The primary mechanism for resource management.
2.  **Explicit Close**: `close()` methods on all resource wrappers.
3.  **Owner Ownership**: Parent objects own child resources (e.g. Response owns Body).

## API Design

```python
class Resource:
    """Base class for WIT resource wrappers."""
    
    def __init__(self, handle):
        self._handle = handle
        self._closed = False
        
    def close(self):
        """Release the underlying WIT resource."""
        if not self._closed:
            # Call WIT drop function
            self._handle.drop() 
            self._closed = True
            
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def __del__(self):
        """Last-resort cleanup."""
        if not self._closed:
            # Warning: __del__ behavior is tricky in Python, 
            # but better than nothing for leaks.
            self.close()
```

## Specific Resources

### Body
- Must close to signal EOF to reader.
- `__exit__` calls `close()`.

### KV/Config/Secret Stores
- Less critical for immediate closure, but good practice.
- `__enter__`/`__exit__` provided.

### Request/Response
- Ownership of Body is transferred.
- When Request/Response is closed, it should close its Body? Or Body is independent?
    - *Decision*: Body is independent but often accessed via property. If the user accesses `req.body`, they own it. If they don't, the Request wrapper should probably clean it up when the Request is done.

## Implementation Notes

1.  **Componentize-Py**: Ensure `componentize-py` generated bindings expose the `drop` method for resources.
2.  **Validation**: Use `fastly_compute.utils` to validate handle liveness if needed.
