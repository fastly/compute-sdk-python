# Cache Purge API Design

## Overview

Design for programmatically purging content from the Fastly cache.

## WIT Interface Reference

```wit
interface purge {
  use types.{error};

  record purge-options {
    soft-purge: bool,
    extra: option<borrow<extra-purge-options>>,
  }

  purge-surrogate-key: func(
    surrogate-keys: string,
    purge-options: purge-options,
  ) -> result<_, error>;

  purge-surrogate-key-verbose: func(
    surrogate-keys: string,
    purge-options: purge-options,
    max-len: u64,
  ) -> result<string, error>;
}
```

Generated stubs: `stubs/wit_world/imports/purge.py`

## API Design

```python
from typing import Optional

def purge_surrogate_key(surrogate_key: str, soft: bool = False) -> None:
    """Purge content associated with a surrogate key.
    
    Args:
        surrogate_key: Key to purge (space-separated for multiple)
        soft: If True, mark as stale rather than removing (Soft Purge)
    """
    pass

def purge_surrogate_key_verbose(surrogate_key: str, soft: bool = False) -> str:
    """Purge content and return a purge ID.
    
    Returns:
        JSON string containing purge ID (e.g. {"1234-1234..."})
    """
    pass
```

## Usage Examples

```python
from fastly_compute import purge_surrogate_key

# Hard purge
purge_surrogate_key("product:123")

# Soft purge (mark as stale)
purge_surrogate_key("catalog", soft=True)

# Multiple keys
purge_surrogate_key("product:123 category:electronics")
```

## Deferred Features

- **URL Purge**: Not supported by this interface (Surrogate Key purge is best practice).
- **Global Purge**: `purge_all` is not exposed here.

## Implementation Notes

1. **Surrogate Keys**: Fastly supports space-separated keys in a single string.
2. **Error Handling**: Raises exception on failure.
