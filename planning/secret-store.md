# Secret Store API Design

## Overview

Design for the Secret Store API, providing secure access to sensitive credentials and secrets at the edge.

## WIT Interface Reference

```wit
interface secret-store {
  use types.{error, open-error};

  resource secret {
    from-bytes: static func(bytes: list<u8>) -> result<secret, error>;
    plaintext: func(max-len: u64) -> result<list<u8>, error>;
  }

  resource store {
    open: static func(name: string) -> result<store, open-error>;
    get: func(key: string) -> result<option<secret>, error>;
  }
}
```

Generated stubs: `stubs/wit_world/imports/secret_store.py`

## API Design

```python
from typing import Optional

class Secret:
    """A secret value retrieved from Secret Store."""
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'Secret':
        """Create a secret from raw bytes (not recommended for production)."""
        pass
    
    def plaintext(self) -> bytes:
        """Get the plaintext value of this secret."""
        pass
    
    def plaintext_str(self, encoding: str = 'utf-8') -> str:
        """Get the plaintext value as a string."""
        return self.plaintext().decode(encoding)
    
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): pass
    
    # Prevent accidental exposure
    def __str__(self) -> str: return "<Secret>"
    def __repr__(self) -> str: return "<Secret>"

class SecretStore:
    """Interface to a Fastly Secret Store."""
    
    @classmethod
    def open(cls, name: str) -> 'SecretStore': pass
    
    def get(self, key: str) -> Optional[Secret]: pass
    
    # Dict-like interface
    def __getitem__(self, key: str) -> Secret: pass
    def __contains__(self, key: str) -> bool: pass
    
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): pass
```

## Usage Examples

```python
from fastly_compute import SecretStore

# Open a secret store
secrets = SecretStore.open("production-secrets")

# Retrieve a secret
if "api-key" in secrets:
    api_key_secret = secrets["api-key"]
    # Use api_key...

# Use with backend client certificates
from fastly_compute import Backend

cert = secrets["client-cert"].plaintext_str()
key = secrets["client-key"]  # Keep as Secret!

backend = Backend.register_dynamic(
    "secure-backend",
    "api.example.com:443",
    client_cert=cert,
    client_key=key  # Pass Secret directly
)
```

## Deferred Features

- **Secret Management**: Creating or updating secrets via the API is not supported by the underlying platform.
- **Async Access**: Secret store operations are currently synchronous only.

## Implementation Notes

1. **WIT Resource Wrapping**: Properly wrap WIT secret resource handles
2. **Memory Safety**: Ensure plaintext secrets are cleared from memory when possible
3. **String Representation**: Override __str__ and __repr__ to prevent accidental logging
4. **API Integration**: Ensure Secret objects work with Backend and other APIs expecting secrets

### Comparison with Other SDKs

- **Rust SDK**: The `Secret` object design is very similar:
  - Wraps a handle
  - Lazy plaintext access
  - `from_bytes` exists but warns about usage
  - Returns `Bytes` (copy-on-write ref counting) to avoid unnecessary copies
- **Python SDK**: Matches this pattern, ensuring a consistent security model across SDKs.