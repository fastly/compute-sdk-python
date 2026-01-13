# ACL API Design

## Overview

Design for interacting with Access Control Lists (ACLs).

## WIT Interface Reference

```wit
interface acl {
  use types.{error, open-error, ip-address};
  use http-body.{body};

  resource acl {
    open: static func(name: string) -> result<acl, open-error>;
    lookup: func(ip-addr: ip-address) -> result<option<body>, acl-error>;
  }

  enum acl-error { too-many-requests, generic-error }
}
```

Generated stubs: `stubs/wit_world/imports/acl.py`

## API Design

```python
from typing import Optional, Any
from ipaddress import IPv4Address, IPv6Address
import json

class ACL:
    """An Access Control List."""
    
    @classmethod
    def open(cls, name: str) -> 'ACL': pass
    
    def lookup(self, ip: str | IPv4Address | IPv6Address) -> Optional[dict]:
        """Look up an IP address in the ACL.
        
        Returns:
            Dictionary of metadata if found, None if not found.
        """
        pass
    
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): pass
```

## Usage Examples

```python
from fastly_compute import ACL

# Open an ACL
blocklist = ACL.open("my-blocklist")

client_ip = "203.0.113.1"

# Check if IP is in the ACL
entry = blocklist.lookup(client_ip)
if entry:
    # IP found in blocklist
    print(f"Blocked: {entry.get('reason', 'no reason')}")
    return Response(status=403, body=b"Access Denied")

# IP not found
return Response(status=200, body=b"OK")
```

## Deferred Features

- **ACL Management**: Creating or updating ACLs via this API is not supported (read-only).
- **Non-IP Lookups**: Currently only IP address lookup is supported.

## Implementation Notes

1. **Body Parsing**: The WIT interface returns a `body` handle on match. The SDK should read and parse this body (assumed JSON) automatically for convenience.
2. **Error Handling**: Map `acl-error` to appropriate Python exceptions.
