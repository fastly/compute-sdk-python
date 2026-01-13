# Idiomatic Exceptions Design

## Overview

Design for a Pythonic exception hierarchy and a mechanism to map low-level WIT errors to these exceptions via automated codegen.

## Exception Hierarchy

```python
class FastlyError(Exception):
    """Base class for all Fastly Compute exceptions."""
    def __init__(self, message: str, wit_error: Optional[Any] = None):
        super().__init__(message)
        self.wit_error = wit_error

class ResourceError(FastlyError):
    """Resource open/access errors."""
    pass

class ResourceNotFound(ResourceError):
    """Resource not found (e.g. KV store name invalid)."""
    pass

class ResourceLimitExceeded(ResourceError):
    """Quotas or limits exceeded."""
    pass

class BackendError(FastlyError):
    """Backend communication errors."""
    pass

# KV Store Specific
class KVStoreError(FastlyError): pass
class KVKeyFound(KVStoreError): pass
class KVPreconditionFailed(KVStoreError): pass
class KVPayloadTooLarge(KVStoreError): pass
```

## Mapping Strategy: Automated Decorators

We use a code generation tool (`tools/codegen.py`) to produce "safe" wrappers for all WIT functions. These wrappers use a decorator (`map_wit_error`) to handle exception translation automatically.

### 1. The Decorator

```python
def map_wit_error(mapping: Dict[str, Type[FastlyError]], default: Type[FastlyError]):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Err as e:
                # Map error string (variant name) to Exception class
                variant = str(e.value)
                if variant in mapping:
                    raise mapping[variant](variant) from e
                raise default(f"Generic error: {e.value}") from e
        return wrapper
    return decorator
```

### 2. Generated Code

The codegen tool parses the WIT definitions to determine which errors a function can raise and generates the appropriate mapping dictionary and wrapped function.

```python
# fastly_compute/wit/imports/kv_store.py (Generated)

_KV_ERROR_MAP = {
    'bad-request': BadRequestError,
    'precondition-failed': KVPreconditionFailed,
    # ...
}

@map_wit_error(_KV_ERROR_MAP, default=KVStoreError)
def insert(key, body, options):
    return _raw.insert(key, body, options)
```

## Benefits

1.  **Zero Boilerplate**: SDK developers use `fastly_compute.wit.imports.kv_store` which behaves like a normal Python module but raises proper exceptions.
2.  **Consistency**: Exception mapping is derived directly from the WIT source of truth.
3.  **Maintainability**: Regenerating bindings updates all mappings instantly.
