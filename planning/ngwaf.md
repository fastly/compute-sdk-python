# NGWAF (Security) API Design

## Overview

Design for the Next-Gen WAF (Security) API, providing request inspection using the NGWAF lookaside service.

## WIT Interface Reference

```wit
interface security {
  use http-req.{request, body, ip-address, error};

  /// Inspects request HTTP traffic using the [NGWAF] lookaside service.
  ///
  /// Returns a JSON-encoded string.
  ///
  /// [NGWAF]: https://docs.fastly.com/en/ngwaf/
  inspect: func(
    request: borrow<request>,
    body: borrow<body>,
    options: inspect-options,
    max-len: u64
  ) -> result<string, error>;

  record inspect-options {
    corp: option<string>,
    workspace: option<string>,
    override-client-ip: option<ip-address>,
    extra: option<borrow<extra-inspect-options>>,
  }

  resource extra-inspect-options {}
}
```

Generated stubs: `stubs/wit_world/imports/security.py`

## API Design

```python
from typing import Optional, Dict, Any
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv6Address

@dataclass
class InspectOptions:
    corp: Optional[str] = None
    workspace: Optional[str] = None
    override_client_ip: Optional[str | IPv4Address | IPv6Address] = None

class Security:
    """Interface to Fastly NGWAF (Security)."""
    
    @staticmethod
    def inspect(
        request: 'Request',
        body: 'Body',
        options: Optional[InspectOptions] = None
    ) -> Dict[str, Any]:
        """Inspect request traffic using NGWAF.
        
        Returns:
            Dictionary containing inspection results (tags, signals, etc).
        """
        pass
```

## Usage Examples

```python
from fastly_compute import Security, InspectOptions

def handle_request(req):
    # Basic inspection
    result = Security.inspect(req, req.body)
    
    if result.get("action") == "block":
        return Response(status=403, body=b"Blocked by NGWAF")
    
    # Inspection with options
    options = InspectOptions(
        corp="my-corp",
        workspace="production",
        override_client_ip="1.2.3.4"
    )
    result = Security.inspect(req, req.body, options)
```

## Implementation Notes

1.  **JSON Response**: The `inspect` function returns a JSON string. The SDK should parse this into a Python dict.
2.  **Body Handling**: Note that `inspect` takes a `borrow<body>`. It does not consume the body, allowing it to be read later.
