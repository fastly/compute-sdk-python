"""Logging API for Fastly Compute.

This module provides access to Fastly logging endpoints, allowing you to send
logs to configured Real-Time Log Streaming endpoints.

Example::

    from fastly_compute import LogEndpoint

    # Direct usage
    endpoint = LogEndpoint.open("my_logs")
    endpoint.write("Hello from Fastly Compute!")

    # Using Python standard logging
    import logging
    from fastly_compute import FastlyLogHandler

    logger = logging.getLogger("my_app")
    logger.setLevel(logging.INFO)
    logger.addHandler(FastlyLogHandler("my_logs"))

    logger.info("Request processed", extra={"user_id": 123})
"""

import logging
from collections.abc import Callable

from fastly_compute._bindings.log import Endpoint as _Endpoint


class LogEndpoint(_Endpoint):
    """Interface to a Fastly logging endpoint.

    Logging endpoints send log data to configured Real-Time Log Streaming
    destinations. Configure endpoints through the Fastly web interface or API.

    Example::

        with LogEndpoint.open("my_logs") as endpoint:
            endpoint.write("Application started")
            endpoint.write(b"Binary log data")
    """

    def write(self, msg: bytes | str) -> None:
        """Write data to the logging endpoint.

        Each call to write() with a non-empty message produces a single log event.

        :arg msg: The message to write (bytes or string). Strings are UTF-8 encoded.

        Example::

            endpoint = LogEndpoint.open("my_logs")
            endpoint.write("Text message")
            endpoint.write(b"Binary data")
        """
        if isinstance(msg, str):
            msg = msg.encode("utf-8")
        self._wit_resource.write(msg)


class FastlyLogHandler(logging.Handler):
    """A logging handler that sends logs to a Fastly endpoint.

    This handler integrates with Python's standard logging framework,
    allowing you to use familiar logging patterns with Fastly's
    Real-Time Log Streaming.

    The handler supports routing logs from different loggers to different
    endpoints using an endpoint_mapper function.

    Example::

        import logging
        from fastly_compute import FastlyLogHandler

        # Simple: single endpoint for all loggers
        handler = FastlyLogHandler("my_logs")
        logger = logging.getLogger("my_app")
        logger.addHandler(handler)

        # Advanced: route different loggers to different endpoints
        def route_logs(logger_name: str) -> str:
            if logger_name.startswith("api"):
                return "api-logs"
            elif logger_name.startswith("worker"):
                return "worker-logs"
            return "app-logs"  # default

        handler = FastlyLogHandler(endpoint_mapper=route_logs)

        # Or use a dict for simple mappings
        endpoint_map = {"api": "api-logs", "worker": "worker-logs"}
        handler = FastlyLogHandler(
            "default",
            endpoint_mapper=lambda name: endpoint_map.get(name, "app-logs")
        )

        # Use logger
        logger.info("Request received", extra={"user_id": 123})
        logger.error("Error processing request", exc_info=True)
    """

    def __init__(
        self,
        default_endpoint: str | None,
        endpoint_mapper: Callable[[str], str | None] | None = None,
        level=logging.NOTSET,
    ):
        """Initialize the handler.

        :arg default_endpoint: The default endpoint name (used when no mapper provided)
        :arg endpoint_mapper: Optional callable that maps logger name to endpoint name.
            Signature: (logger_name: str) -> endpoint_name: str
        :arg level: Minimum logging level to handle (default: NOTSET)
        :raise ValueError: If neither default_endpoint nor endpoint_mapper is provided

        Example::

            # Simple: single endpoint
            handler = FastlyLogHandler("my_logs")

            # Advanced: route by logger name
            handler = FastlyLogHandler(
                endpoint_mapper=lambda name: f"{name}-logs"
            )

            # With fallback
            handler = FastlyLogHandler(
                default_endpoint="app-logs",
                endpoint_mapper=lambda name: "api-logs" if "api" in name else None
            )
        """
        super().__init__(level)

        if default_endpoint is None and endpoint_mapper is None:
            raise ValueError(
                "Either default_endpoint or endpoint_mapper must be provided"
            )

        self._default_endpoint: str | None = default_endpoint
        self._endpoint_mapper: Callable[[str], str | None] | None = endpoint_mapper
        self._endpoints: dict[str, LogEndpoint] = {}  # Cache opened endpoints

    def _get_endpoint(self, logger_name: str) -> LogEndpoint:
        """Get or create an endpoint for the given logger name.

        :arg logger_name: Name of the logger
        :return: LogEndpoint instance
        """
        # Determine which endpoint to use
        endpoint_name: str | None
        if self._endpoint_mapper is not None:
            endpoint_name = self._endpoint_mapper(logger_name)
            # If mapper returns None, fall back to default
            if endpoint_name is None:
                endpoint_name = self._default_endpoint
        else:
            endpoint_name = self._default_endpoint

        if endpoint_name is None:
            raise ValueError(
                f"No endpoint determined for logger '{logger_name}' "
                "(mapper returned None and no default_endpoint set)"
            )

        # Return cached endpoint if available
        if endpoint_name in self._endpoints:
            return self._endpoints[endpoint_name]

        # Open new endpoint and cache it
        endpoint = LogEndpoint.open(endpoint_name)
        self._endpoints[endpoint_name] = endpoint
        return endpoint

    def emit(self, record: logging.LogRecord):
        """Emit a record to the Fastly logging endpoint.

        This method is called automatically by the logging framework.
        You should not need to call it directly.

        The endpoint is determined by calling endpoint_mapper with the
        logger name, or using the default_endpoint.

        :arg record: The log record to emit
        """
        try:
            endpoint = self._get_endpoint(record.name)
            msg = self.format(record)
            endpoint.write(msg)
        except Exception:
            # Handler errors should not propagate to the application; this should
            # rare but we would rather log a deferred format problem or similar as an error
            # rather than crashing the application.
            self.handleError(record)

    def close(self):
        """Close the handler and release all endpoint resources.

        This is called automatically when the handler is garbage collected
        or when logging.shutdown() is called.
        """
        try:
            # Close all cached endpoints
            for endpoint in self._endpoints.values():
                endpoint.close()
            self._endpoints.clear()
        finally:
            super().close()
