"""Exceptions for fastly_compute.requests - compatible with requests library."""


class RequestException(Exception):
    """Base exception for all requests-related errors."""

    def __init__(self, message: str, response=None):
        """Initialize RequestException.

        Args:
            message: Error message
            response: Optional response object that caused the error
        """
        super().__init__(message)
        self.response = response


class ConnectionError(RequestException):
    """Exception for connection-related errors."""


class Timeout(RequestException):
    """Exception for timeout errors."""


class HTTPError(RequestException):
    """Exception for HTTP error responses (4xx, 5xx status codes)."""

    def __init__(self, message: str, response=None):
        """Initialize HTTPError.

        Args:
            message: Error message
            response: Response object that caused the error
        """
        super().__init__(message, response)


class TooManyRedirects(RequestException):
    """Exception for too many redirects."""


class InvalidURL(RequestException, ValueError):
    """Exception for invalid URLs."""


class InvalidHeader(RequestException, ValueError):
    """Exception for invalid headers."""


class ChunkedEncodingError(RequestException):
    """Exception for chunked encoding errors."""


class ContentDecodingError(RequestException):
    """Exception for content decoding errors."""


class StreamConsumedError(RequestException, TypeError):
    """Exception for attempting to read a consumed stream."""
