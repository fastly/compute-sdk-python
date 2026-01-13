# Runtime Info API Design

## Overview

Design for accessing Fastly Compute runtime information such as memory usage, vCPU usage, and environment details.

## WIT Interface Reference

```wit
interface compute-runtime {
  type vcpu-ms = u64;
  type memory-mib = u32;

  get-vcpu-ms: func() -> vcpu-ms;
  get-heap-mib: func() -> memory-mib;
  get-sandbox-id: func() -> string;
  
  // Environment variable equivalents
  // FASTLY_HOSTNAME / server.hostname
  // FASTLY_REGION / server.region
  // FASTLY_SERVICE_ID / req.service_id
  // FASTLY_SERVICE_VERSION / req.service_version
  // FASTLY_TRACE_ID / req.trace_id (same as sandbox-id)
}
```

Generated stubs: `stubs/wit_world/imports/compute_runtime.py`

## API Design

```python
class Runtime:
    """Access to Compute runtime information."""
    
    @staticmethod
    def vcpu_ms() -> int:
        """Get vCPU time consumed in milliseconds."""
        pass
        
    @staticmethod
    def heap_usage_mib() -> int:
        """Get current heap usage in MiB."""
        pass
        
    @staticmethod
    def sandbox_id() -> str:
        """Get the unique ID for the current sandbox instance."""
        pass
```

## Usage Examples

```python
from fastly_compute import Runtime

# Log resource usage
print(f"Memory: {Runtime.heap_usage_mib()} MiB")
print(f"CPU: {Runtime.vcpu_ms()} ms")

# Trace correlation
trace_id = Runtime.sandbox_id()
```

## Deferred Features

- **Environment Variables**: Access to other env vars (Service ID, Version, Hostname, Region) is typically done via `os.environ` which is populated by the runtime. We do not need explicit wrappers if standard `os.environ` works.

## Implementation Notes

1.  **Benchmarking**: `vcpu_ms` includes hostcall time and should be used with caution for benchmarking.
