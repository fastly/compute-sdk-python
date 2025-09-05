"""
FastlyResponse - A requests-compatible response object for Fastly Compute
"""

import json
from typing import Any

from wit_world.imports import http_body


class FastlyResponse:
    """A requests.Response-compatible response object.

    This class wraps WIT response objects to provide the familiar
    requests.Response interface.
    """

    def __init__(self, wit_response, response_body, url: str):
        """Initialize FastlyResponse.

        Args:
            wit_response: The WIT response object
            response_body: The WIT response body
            url: The final URL that was requested
        """
        self._wit_response = wit_response
        self._response_body = response_body
        self._url = url
        self._content: bytes | None = None
        self._text: str | None = None
        self._headers: dict[str, str] | None = None
        self._json_data: Any | None = None

    @property
    def status_code(self) -> int:
        """HTTP status code."""
        return self._wit_response.get_status()

    @property
    def url(self) -> str:
        """Final URL that was requested."""
        return self._url

    @property
    def headers(self) -> dict[str, str]:
        """Response headers as a case-insensitive dict."""
        if self._headers is None:
            self._headers = {}
            cursor = 0

            # Read all headers using WIT API
            while True:
                try:
                    header_names, next_cursor = self._wit_response.get_header_names(
                        4096, cursor
                    )
                    if not header_names:
                        break

                    # Split header names (they're null-separated)
                    names = header_names.split("\0")[:-1]  # Remove empty last element

                    for name in names:
                        if name:  # Skip empty names
                            try:
                                value = self._wit_response.get_header_value(name, 4096)
                                if value:
                                    # Convert to string and store with lowercase key for case-insensitive access
                                    self._headers[name.lower()] = value.decode(
                                        "utf-8", errors="replace"
                                    )
                            except Exception:
                                # Skip headers that can't be read
                                pass

                    if not next_cursor:
                        break
                    cursor = next_cursor

                except Exception:
                    # If header reading fails, break out of loop
                    break

        return self._headers

    @property
    def content(self) -> bytes:
        """Response body as bytes."""
        if self._content is None:
            self._content = self._read_body()
        return self._content

    @property
    def text(self) -> str:
        """Response body as unicode string."""
        if self._text is None:
            content = self.content

            # Try to determine encoding from headers
            encoding = "utf-8"  # Default encoding
            content_type = self.headers.get("content-type", "")
            if "charset=" in content_type:
                try:
                    encoding = content_type.split("charset=")[1].split(";")[0].strip()
                except (IndexError, ValueError):
                    encoding = "utf-8"

            try:
                self._text = content.decode(encoding)
            except UnicodeDecodeError:
                # Fallback to utf-8 with error replacement
                self._text = content.decode("utf-8", errors="replace")

        return self._text

    def json(self, **kwargs) -> Any:
        """Parse response body as JSON.

        Args:
            **kwargs: Additional arguments passed to json.loads()

        Returns:
            Parsed JSON data

        Raises:
            json.JSONDecodeError: If response is not valid JSON
        """
        if self._json_data is None:
            self._json_data = json.loads(self.text, **kwargs)
        return self._json_data

    @property
    def ok(self) -> bool:
        """True if status code is less than 400."""
        return 200 <= self.status_code < 400

    @property
    def is_redirect(self) -> bool:
        """True if status code is a redirect (3xx)."""
        return 300 <= self.status_code < 400

    @property
    def is_permanent_redirect(self) -> bool:
        """True if status code is a permanent redirect."""
        return self.status_code in (301, 308)

    def raise_for_status(self) -> None:
        """Raise an HTTPError for bad responses.

        Raises:
            HTTPError: If response status indicates an error
        """
        from .exceptions import HTTPError

        if not self.ok:
            raise HTTPError(
                f"{self.status_code} Client Error: {self.reason} for url: {self.url}",
                response=self,
            )

    @property
    def reason(self) -> str:
        """HTTP status reason phrase."""
        # WIT doesn't provide reason phrases, so we'll use standard ones
        status_phrases = {
            200: "OK",
            201: "Created",
            202: "Accepted",
            204: "No Content",
            301: "Moved Permanently",
            302: "Found",
            304: "Not Modified",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            409: "Conflict",
            422: "Unprocessable Entity",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
        }
        return status_phrases.get(self.status_code, "Unknown")

    @property
    def encoding(self) -> str | None:
        """Response encoding."""
        content_type = self.headers.get("content-type", "")
        if "charset=" in content_type:
            try:
                return content_type.split("charset=")[1].split(";")[0].strip()
            except (IndexError, ValueError):
                pass
        return None

    def _read_body(self) -> bytes:
        """Read the complete response body from WIT."""
        body_data = b""
        chunk_size = 4096

        try:
            while True:
                chunk = http_body.read(self._response_body, chunk_size)
                if not chunk:
                    break
                body_data += chunk
        except Exception:
            # If reading fails, return what we have
            pass

        return body_data

    def __bool__(self) -> bool:
        """Boolean evaluation returns ok status."""
        return self.ok

    def __repr__(self) -> str:
        """String representation of the response."""
        return f"<FastlyResponse [{self.status_code}]>"
