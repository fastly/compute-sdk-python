# Device Detection API Design

## Overview

Design for the Device Detection API, allowing lookup of device capabilities based on User-Agent strings.

## WIT Interface Reference

```wit
interface device-detection {
  use types.{error};

  /// Looks up the data associated with a particular User-Agent string.
  ///
  /// Returns a list of bytes containing JSON-encoded device data.
  lookup: func(user-agent: string, max-len: u64) -> result<option<string>, error>;
}
```

Generated stubs: `stubs/wit_world/imports/device_detection.py`

## API Design

```python
from typing import Optional, Dict, Any

class DeviceDetection:
    """Interface for device detection lookups."""
    
    @staticmethod
    def lookup(user_agent: str) -> Optional[Dict[str, Any]]:
        """Look up device information for a User-Agent string.
        
        Returns:
            Dictionary containing device data (brand, model, is_mobile, etc) 
            if found, None otherwise.
        """
        pass
```

## Usage Examples

```python
from fastly_compute import DeviceDetection

user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)..."
device = DeviceDetection.lookup(user_agent)

if device:
    if device.get("is_mobile"):
        # Serve mobile content
        pass
    print(f"Device: {device.get('brand')} {device.get('model')}")
```

## Implementation Notes

1.  **JSON Parsing**: The SDK parses the JSON response into a dict.
2.  **Field Names**: Preserves field names as returned by the platform.
