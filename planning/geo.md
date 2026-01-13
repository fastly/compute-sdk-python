# Geo API Design

## Overview

Design for the Geo API, providing geographic and network intelligence based on IP addresses.

## WIT Interface Reference

```wit
/// [Geographic data] for IP addresses.
///
/// [Geographic data]: https://www.fastly.com/blog/improve-performance-and-gain-better-end-user-intelligence-geoip-geography-detection
interface geo {
  use types.{error, ip-address};

  /// Looks up the geographic data associated with a particular IP address.
  ///
  /// Returns a list of bytes containing JSON-encoded geographic data. See [here] for descriptions
  /// of the JSON fields.
  ///
  /// [here]: https://www.fastly.com/documentation/reference/vcl/variables/geolocation/
  lookup: func(ip-addr: ip-address, max-len: u64) -> result<string, error>;
}
```

Generated stubs: `stubs/wit_world/imports/geo.py`

## API Design

```python
from typing import Optional, Any
from dataclasses import dataclass, field
from ipaddress import IPv4Address, IPv6Address, ip_address

@dataclass
class Geo:
    """Geographic and network information for an IP address.
    
    Provides strongly-typed access to geographic data.
    """
    # Location
    city: str = ""
    country_code: str = ""  # ISO 3166-1 alpha-2
    country_code3: str = ""  # ISO 3166-1 alpha-3
    country_name: str = ""
    continent_code: str = ""
    region: Optional[str] = None  # ISO 3166-2 region code
    postal_code: str = ""
    
    # Coordinates
    latitude: float = 0.0
    longitude: float = 0.0
    metro_code: int = 0
    
    # Network
    as_number: int = 0  # Autonomous System Number
    as_name: str = ""   # Autonomous System Name
    conn_speed: str = ""  # e.g., "broadband", "mobile"
    conn_type: str = ""   # e.g., "wired", "wireless"
    
    # Proxy detection
    proxy_type: str = ""  # e.g., "anonymous", "transparent"
    proxy_description: str = ""
    
    # Time zone
    utc_offset: int = 0  # Offset in seconds
    
    # Raw JSON data for forward compatibility
    _raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict) -> 'Geo':
        """Create Geo instance from dictionary."""
        # Helper to safely get values with correct types
        def get_float(k):
            v = data.get(k)
            return float(v) if v is not None else 0.0
            
        def get_int(k):
            v = data.get(k)
            return int(v) if v is not None else 0
            
        return cls(
            city=data.get("city", ""),
            country_code=data.get("country_code", "") or data.get("country.code", ""),
            country_code3=data.get("country_code3", "") or data.get("country.code3", ""),
            country_name=data.get("country_name", "") or data.get("country.name", ""),
            continent_code=data.get("continent_code", "") or data.get("continent", ""),
            region=data.get("region"),
            postal_code=data.get("postal_code", "") or data.get("postal.code", ""),
            latitude=get_float("latitude"),
            longitude=get_float("longitude"),
            metro_code=get_int("metro_code") or get_int("metro.code"),
            as_number=get_int("as_number") or get_int("as.number"),
            as_name=data.get("as_name", "") or data.get("as.name", ""),
            conn_speed=data.get("conn_speed", "") or data.get("conn.speed", ""),
            conn_type=data.get("conn_type", "") or data.get("conn.type", ""),
            proxy_type=data.get("proxy_type", "") or data.get("proxy.type", ""),
            proxy_description=data.get("proxy_description", "") or data.get("proxy.description", ""),
            utc_offset=get_int("utc_offset") or get_int("utc.offset"),
            _raw=data
        )

def lookup(ip: str | IPv4Address | IPv6Address) -> Optional[Geo]:
    """Look up geographic information for an IP address.
    
    Args:
        ip: IP address as string or ipaddress object
        
    Returns:
        Geo object if lookup succeeds, None otherwise (e.g. private IP)
    """
    pass

def lookup_client(request: 'Request') -> Optional[Geo]:
    """Look up geographic information for the client IP.
    
    Convenience method that extracts the client IP from the
    request and performs a lookup.
    """
    pass
```

## Usage Examples

```python
from fastly_compute import geo

# Basic lookup
location = geo.lookup("203.0.113.42")
if location:
    print(f"Location: {location.city}, {location.country_name}")
    print(f"Coordinates: {location.latitude}, {location.longitude}")
    print(f"AS Number: {location.as_number}")

# Look up client IP from request
def handle_request(request):
    client_geo = geo.lookup_client(request)
    if client_geo:
        # Customize response based on location
        if client_geo.country_code == "US":
            return Response(body=b"Hello from the US!")
        elif client_geo.continent_code == "EU":
            return Response(
                body=b"Hello from Europe!",
                headers={"Content-Language": "en-GB"}
            )
    
    return Response(body=b"Hello, World!")
```

## Deferred Features

- **Complex Enums**: Unlike Rust/Go, we use strings for enums (ConnType, ProxyType, etc.) for simplicity.
- **Advanced Caching**: Built-in caching is out of scope; users can implement their own if needed.
- **IP Parsing**: We rely on standard library `ipaddress` rather than implementing custom parsing logic.
