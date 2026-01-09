"""Backend resolution logic for fastly_compute.requests.

Handles the logic for determining whether to use static or dynamic backends
based on URL patterns and backend availability.
"""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from typing import TYPE_CHECKING

from wit_world.imports import backend as wit_backend
from wit_world.imports.types import OpenError
from wit_world.types import Err

from .exceptions import MissingSchema, RequestException

if TYPE_CHECKING:
    from .timeout import TimeoutConfig

# global (per instance) set of registered dynamic backends
_dynamic_backends: set[str] = set()


@dataclass
class BackendResolution:
    """Result of a successful backend resolution."""

    url_parsed: urllib.parse.ParseResult
    backend: wit_backend.Backend


def resolve_backend(
    url: str,
    fastly_backend: str | None = None,
    timeout_config: TimeoutConfig | None = None,
) -> BackendResolution:
    """Resolve backend name and final URL for a request.

    Args:
        url: The URL to request (can be path-only or full URL)
        fastly_backend: Optional static backend name
        timeout_config: Optional timeout configuration for dynamic backends

    Returns:
        ResolutionResult containing backend and updated parsed url

    Raises:
        RequestException: If backend resolution fails
        MissingSchema: If URL is missing scheme (subclass of RequestException)
    """
    parsed = urllib.parse.urlparse(url)

    backend_obj: wit_backend.Backend
    if fastly_backend is not None:
        # Check if backend exists by trying to open it
        try:
            backend_obj = wit_backend.Backend.open(fastly_backend)
        except Err as e:
            # Check if this is an OpenError (backend not found)
            if isinstance(e.value, OpenError):
                raise RequestException(
                    f"Static backend '{fastly_backend}' does not exist"
                ) from e
            # Re-raise if it's a different error
            raise
    else:
        if not parsed.scheme or not parsed.netloc:
            raise MissingSchema(
                f"Invalid URL {url!r}: No scheme supplied. "
                f"Perhaps you meant https://{url}?"
            )

        # Register dynamic backend if not already registered
        backend_name = _sanitize_backend_name(parsed)
        timeout_config = timeout_config or TimeoutConfig()
        if backend_name not in _dynamic_backends:
            backend_obj = _register_dynamic_backend(
                backend_name, parsed, timeout_config
            )
            _dynamic_backends.add(backend_name)
        else:
            # Open the already-registered backend
            backend_obj = wit_backend.Backend.open(backend_name)

        if parsed.netloc == "":
            host = backend_obj.get_host(1024)
            parsed = parsed._replace(netloc=host)

    return BackendResolution(url_parsed=parsed, backend=backend_obj)


def _register_dynamic_backend(
    backend_name: str,
    parsed_url: urllib.parse.ParseResult,
    timeout_config: TimeoutConfig,
) -> wit_backend.Backend:
    options = wit_backend.DynamicBackendOptions()

    # Configure TLS for HTTPS
    if parsed_url.scheme == "https":
        options.use_tls(True)
        # Set SNI to the hostname for proper certificate validation
        options.sni_hostname(parsed_url.hostname or parsed_url.netloc)

    # Set timeouts from configuration (convert to milliseconds)
    options.connect_timeout(timeout_config.connect_ms)
    options.first_byte_timeout(timeout_config.first_byte_ms)
    options.between_bytes_timeout(timeout_config.between_bytes_ms)

    # Register the backend
    try:
        return wit_backend.register_dynamic_backend(
            prefix=backend_name, target=parsed_url.netloc, options=options
        )
    except Err as e:
        raise RequestException.from_wit_error(e, "register_dynamic_backend") from e


def _sanitize_backend_name(parsed: urllib.parse.ParseResult) -> str:
    # Replace dots, colons, and other special chars with underscores
    # Keep only alphanumeric chars and underscores
    sanitized = ""
    for char in parsed.netloc.lower():
        if char.isalnum():
            sanitized += char
        elif char in ".-:":
            sanitized += "_"

    # Remove multiple consecutive underscores if present
    while "__" in sanitized:
        sanitized = sanitized.replace("__", "_")

    # Remove leading/trailing underscores
    sanitized = sanitized.strip("_")
    assert sanitized, "Generated an errant empty backend name!"

    return sanitized
