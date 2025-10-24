"""Backend resolution logic for fastly_compute.requests.

Handles the logic for determining whether to use static or dynamic backends
based on URL patterns and backend availability.
"""

import urllib.parse

from wit_world.imports import backend as wit_backend
from wit_world.imports import http_req


class BackendResolver:
    """Resolves backend names and URLs for requests."""

    def __init__(self):
        """Initialize the backend resolver."""
        self._dynamic_backends = set()  # Track registered dynamic backends

    def resolve(self, url: str, backend: str | None = None) -> tuple[str, str]:
        """Resolve backend name and final URL for a request.

        Args:
            url: The URL to request (can be path-only or full URL)
            backend: Optional static backend name

        Returns:
            Tuple of (backend_name, final_url)

        Raises:
            ValueError: If backend resolution fails
        """
        # If explicit backend is provided, use static backend pattern
        if backend is not None:
            return self._resolve_static_backend(url, backend)

        # If URL looks like a full URL, use dynamic backend pattern
        if self._is_full_url(url):
            return self._resolve_dynamic_backend(url)

        # Path-only URL without explicit backend - this is an error
        raise ValueError(
            "Path-only URL requires explicit 'backend' parameter. "
            f"Either provide backend='backend-name' or use full URL like 'https://example.com{url}'"
        )

    def _resolve_static_backend(self, url: str, backend_name: str) -> tuple[str, str]:
        """Resolve a static backend request.

        Args:
            url: URL (can be path-only or full URL)
            backend_name: Name of the static backend

        Returns:
            Tuple of (backend_name, final_url)

        Raises:
            ValueError: If static backend doesn't exist
        """
        # Check if backend exists
        if not wit_backend.exists(backend_name):
            raise ValueError(f"Static backend '{backend_name}' does not exist")

        # For static backends, we typically use path-only URLs
        if self._is_full_url(url):
            # Extract path from full URL for static backend
            parsed = urllib.parse.urlparse(url)
            final_url = parsed.path if parsed.path else "/"
            if parsed.query:
                final_url += "?" + parsed.query
            if parsed.fragment:
                final_url += "#" + parsed.fragment
        else:
            # Already a path, use as-is (ensure it starts with /)
            final_url = url if url.startswith("/") else "/" + url

        return backend_name, final_url

    def _resolve_dynamic_backend(self, url: str) -> tuple[str, str]:
        """Resolve a dynamic backend request.

        Args:
            url: Full URL (must include scheme and host)

        Returns:
            Tuple of (backend_name, final_url)

        Raises:
            ValueError: If URL is invalid for dynamic backend
        """
        if not self._is_full_url(url):
            raise ValueError("Dynamic backend requires full URL with scheme and host")

        parsed = urllib.parse.urlparse(url)

        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL for dynamic backend: {url}")

        # Generate backend name from host
        host = parsed.netloc
        backend_name = f"dynamic_{self._sanitize_backend_name(host)}"

        # Register dynamic backend if not already registered
        if backend_name not in self._dynamic_backends:
            self._register_dynamic_backend(backend_name, parsed.scheme, host)
            self._dynamic_backends.add(backend_name)

        # For dynamic backends, we use the path portion as the URL
        final_url = parsed.path if parsed.path else "/"
        if parsed.query:
            final_url += "?" + parsed.query
        if parsed.fragment:
            final_url += "#" + parsed.fragment

        return backend_name, final_url

    def _register_dynamic_backend(
        self, backend_name: str, scheme: str, host: str
    ) -> None:
        """Register a new dynamic backend.

        Args:
            backend_name: Name for the dynamic backend
            scheme: URL scheme (http or https)
            host: Target host

        Raises:
            Exception: If backend registration fails
        """
        # Create backend options
        options = http_req.DynamicBackendOptions()

        # Configure TLS for HTTPS
        if scheme == "https":
            options.use_tls(True)

        # Set reasonable timeouts (in milliseconds)
        options.connect_timeout(30000)  # 30 seconds
        options.first_byte_timeout(60000)  # 60 seconds
        options.between_bytes_timeout(10000)  # 10 seconds

        # Register the backend
        target = f"{scheme}://{host}"
        http_req.register_dynamic_backend(
            prefix=backend_name, target=target, options=options
        )

    def _is_full_url(self, url: str) -> bool:
        """Check if URL is a full URL with scheme and netloc."""
        parsed = urllib.parse.urlparse(url)
        return bool(parsed.scheme and parsed.netloc)

    def _sanitize_backend_name(self, host: str) -> str:
        """Sanitize hostname for use as backend name.

        Args:
            host: Hostname (may include port)

        Returns:
            Sanitized backend name
        """
        # Replace dots, colons, and other special chars with underscores
        # Keep only alphanumeric chars and underscores
        sanitized = ""
        for char in host.lower():
            if char.isalnum():
                sanitized += char
            elif char in ".-:":
                sanitized += "_"
            # Skip other special characters

        # Remove multiple consecutive underscores
        while "__" in sanitized:
            sanitized = sanitized.replace("__", "_")

        # Remove leading/trailing underscores
        sanitized = sanitized.strip("_")

        # Ensure it's not empty
        if not sanitized:
            sanitized = "unknown_host"

        return sanitized
