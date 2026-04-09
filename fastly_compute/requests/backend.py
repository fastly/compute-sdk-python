"""Backend resolution logic for fastly_compute.requests.

Handles the logic for determining whether to use static or dynamic backends
based on URL patterns and backend availability.
"""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastly_compute.backend import Backend, DynamicBackendOptions
from fastly_compute.backend import (
    register_dynamic_backend as _register_dynamic_backend_wit,
)
from fastly_compute.exceptions.types.error import Error
from fastly_compute.exceptions.types.open_error import OpenError

from .exceptions import MissingSchema, RequestException

if TYPE_CHECKING:
    from .timeout import TimeoutConfig

# global (per instance) set of registered dynamic backends
_dynamic_backends: set[str] = set()


@dataclass
class BackendResolution:
    """Result of a successful backend resolution."""

    url_parsed: urllib.parse.ParseResult
    backend: Backend


def resolve_backend(
    url: str,
    fastly_backend: str | None = None,
    timeout_config: TimeoutConfig | None = None,
) -> BackendResolution:
    """Resolve backend name and final URL for a request.

    This function determines which Fastly backend to use for a request:
    - If `fastly_backend` is provided, attempts to open that pre-configured static backend
    - Otherwise, registers/reuses a dynamic backend based on the URL's netloc

    Static backends must already be configured in the Fastly service.
    Dynamic backends are automatically registered on first use and cached for reuse.

    :arg url: The URL to request (must be full with scheme and netloc for dynamic backends)
    :arg fastly_backend: Optional static backend name
    :arg timeout_config: Optional timeout configuration for dynamic backends
    :return: ResolutionResult containing backend and updated parsed url
    :raise RequestException: If backend resolution fails
    :raise MissingSchema: If URL is missing scheme (subclass of RequestException)
    """
    parsed = urllib.parse.urlparse(url)
    backend_obj: Backend

    # static backend
    if fastly_backend is not None:
        try:
            backend_obj = Backend.open(fastly_backend)
        except OpenError as e:
            raise RequestException(
                f"Static backend '{fastly_backend}' does not exist"
            ) from e
    else:
        # dynamic backend
        if not parsed.scheme or not parsed.netloc:
            raise MissingSchema(
                f"Invalid URL {url!r}: No scheme supplied. Perhaps you meant https://{url}?"
            )

        backend_name = parsed.netloc.lower()
        timeout_config = timeout_config or TimeoutConfig()
        if backend_name not in _dynamic_backends:
            backend_obj = _register_dynamic_backend(
                backend_name, parsed, timeout_config
            )
            _dynamic_backends.add(backend_name)
        else:
            backend_obj = Backend.open(backend_name)

    return BackendResolution(parsed, backend_obj)


def _register_dynamic_backend(
    backend_name: str,
    parsed_url: urllib.parse.ParseResult,
    timeout_config: TimeoutConfig,
) -> Backend:
    options = DynamicBackendOptions.new()

    # Configure TLS for HTTPS
    if parsed_url.scheme == "https":
        options.use_tls(True)
        # Set SNI to the hostname for proper certificate validation
        options.sni_hostname(parsed_url.hostname or parsed_url.netloc)

    # Set timeouts from configuration (convert to milliseconds)
    options.connect_timeout(timeout_config.connect_ms)
    options.first_byte_timeout(timeout_config.first_byte_ms)
    options.between_bytes_timeout(timeout_config.between_bytes_ms)

    try:
        return _register_dynamic_backend_wit(
            prefix=backend_name, target=parsed_url.netloc, options=options
        )
    except Error as e:
        raise RequestException.from_fastly_error(e, "register_dynamic_backend") from e
