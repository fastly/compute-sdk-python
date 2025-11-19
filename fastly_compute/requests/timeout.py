"""Timeout configuration for Fastly Compute requests.

This module provides timeout configuration classes that support both standard
requests-compatible timeouts and Fastly-specific granular timeout controls.
"""


class TimeoutConfig:
    """Timeout configuration for Fastly backend requests.

    Fastly supports three distinct timeout phases:
    - connect_timeout: Time to establish the initial TCP connection
    - first_byte_timeout: Time between sending request and receiving first response byte
    - between_bytes_timeout: Maximum time between any two consecutive bytes in response

    This provides much more granular control than the standard requests library,
    which only supports a single timeout or (connect, read) tuple.
    """

    def __init__(
        self,
        connect: float = 30.0,
        first_byte: float = 60.0,
        between_bytes: float = 10.0,
    ):
        """Initialize timeout configuration.

        Args:
            connect: Connection timeout in seconds (default: 30.0)
            first_byte: First byte timeout in seconds (default: 60.0)
            between_bytes: Between bytes timeout in seconds (default: 10.0)
        """
        self.connect = connect
        self.first_byte = first_byte
        self.between_bytes = between_bytes

    @property
    def connect_ms(self) -> int:
        """Connection timeout in milliseconds (for WIT API)."""
        return int(self.connect * 1000)

    @property
    def first_byte_ms(self) -> int:
        """First byte timeout in milliseconds (for WIT API)."""
        return int(self.first_byte * 1000)

    @property
    def between_bytes_ms(self) -> int:
        """Between bytes timeout in milliseconds (for WIT API)."""
        return int(self.between_bytes * 1000)

    @classmethod
    def from_requests_timeout(cls, timeout: None | float | tuple) -> "TimeoutConfig":
        """Create TimeoutConfig from requests-compatible timeout parameter.

        Args:
            timeout: Timeout specification in requests-compatible formats:
                - None: Use default timeouts
                - float: Single timeout applied to all phases
                - (connect, read): Tuple with separate connect and read timeouts

        Returns:
            TimeoutConfig object with appropriate timeout values

        Raises:
            ValueError: If timeout format is invalid
        """
        if timeout is None:
            return cls()
        elif isinstance(timeout, int | float):
            # Single timeout - use for all phases
            return cls(connect=timeout, first_byte=timeout, between_bytes=timeout)
        elif isinstance(timeout, tuple) and len(timeout) == 2:
            # (connect, read) - requests-compatible format
            connect, read = timeout
            # Split read timeout between first_byte and between_bytes
            # Use read timeout for first_byte, and half for between_bytes
            return cls(connect=connect, first_byte=read, between_bytes=read / 2)
        else:
            raise ValueError(
                f"Invalid timeout format: {timeout}. Expected None, float, or 2-tuple."
            )

    def __repr__(self) -> str:
        """Return string representation of TimeoutConfig."""
        return f"TimeoutConfig(connect={self.connect}, first_byte={self.first_byte}, between_bytes={self.between_bytes})"
