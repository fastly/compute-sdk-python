# Logging API Design

## Overview

Design for the Logging API, allowing Compute services to send logs to configured Fastly log endpoints.

## WIT Interface Reference

```wit
interface log {
  use types.{error, open-error};

  /// A logging endpoint.
  resource endpoint {
    /// Tries to get an endpoint by name.
    open: static func(name: string) -> result<endpoint, open-error>;

    /// Writes a data to the given endpoint.
    write: func(msg: list<u8>);
  }
}
```

Generated stubs: `stubs/wit_world/imports/log.py`

## API Design

```python
from typing import Optional
import logging

class LogEndpoint:
    """A Fastly logging endpoint."""
    
    @classmethod
    def open(cls, name: str) -> 'LogEndpoint': pass
    
    def write(self, msg: bytes | str) -> None: pass
    
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): pass

class FastlyLogHandler(logging.Handler):
    """A logging handler that sends logs to a Fastly endpoint."""
    
    def __init__(self, endpoint_name: str, level=logging.NOTSET):
        """Initialize the handler with an endpoint name."""
        pass
        
    def emit(self, record: logging.LogRecord):
        """Emit a record to the Fastly logging endpoint."""
        pass
```

## Usage Examples

```python
# Direct usage
from fastly_compute import LogEndpoint

endpoint = LogEndpoint.open("my_logs")
endpoint.write("Hello from Fastly Compute!")

# Using Python standard logging
import logging
from fastly_compute import FastlyLogHandler

logger = logging.getLogger("my_app")
logger.setLevel(logging.INFO)
logger.addHandler(FastlyLogHandler("my_logs"))

logger.info("Structured log message", extra={"user_id": 123})
```

## Deferred Features

- **Async Logging**: The underlying API is synchronous. Async wrappers could be added later if needed.
- **Log Formatting**: Users can use standard Python formatters with the handler.

## Implementation Notes

1. **Error Handling**: `open()` should raise specific exceptions for missing endpoints.
2. **Encoding**: `write()` should handle both bytes and strings (UTF-8 encoding).
3. **Resource Management**: Endpoints are resources but don't strictly require closing; however, context manager support is good practice.
