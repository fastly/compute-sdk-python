"""A requests-compatible response object for Fastly Compute."""

import json
from http import HTTPStatus
from typing import Any, override

from fastly_compute._bindings import async_io, http_resp

from ..utils import create_body_reader
from .exceptions import HTTPError


class FastlyResponse:
    """A requests.Response-compatible response object.

    This class wraps WIT response objects to provide the familiar
    requests.Response interface.
    """

    def __init__(
        self,
        wit_response: http_resp.Response,
        response_body: async_io.Pollable,
        url: str,
    ):
        """Initialize FastlyResponse.

        :arg wit_response: The WIT response object
        :arg response_body: The WIT response body
        :arg url: The final URL that was requested
        """
        self._wit_response: http_resp.Response = wit_response
        self._response_body: async_io.Pollable = response_body
        self._url: str = url
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
                header_names, next_cursor = self._wit_response.get_header_names(
                    4096, cursor
                )
                if not header_names:
                    break

                # Split header names (they're null-separated)
                names = header_names.split("\0")[:-1]  # Remove empty last element

                for name in names:
                    if name:  # Skip empty names
                        value = self._wit_response.get_header_value(name, 4096)
                        if value:
                            # Convert to string and store with lowercase key for case-insensitive access
                            self._headers[name.lower()] = value.decode(
                                "utf-8", errors="replace"
                            )

                if not next_cursor:
                    break
                cursor = next_cursor

        return self._headers

    @property
    def content(self) -> bytes:
        """Response body as bytes."""
        if self._content is None:
            reader = create_body_reader(self._response_body)
            self._content = reader.read()
        return self._content

    @property
    def text(self) -> str:
        """Response body as unicode string."""
        if self._text is None:
            content = self.content

            # Try to determine encoding from headers
            encoding = self._parse_charset() or "utf-8"

            try:
                self._text = content.decode(encoding)
            except UnicodeDecodeError:
                # Fallback to utf-8 with error replacement
                self._text = content.decode("utf-8", errors="replace")

        return self._text

    def json(self, **kwargs: Any) -> Any:
        """Parse response body as JSON.

        :arg kwargs: Additional arguments passed to json.loads()
        :return: Parsed JSON data
        :raise json.JSONDecodeError: If response is not valid JSON
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

        :raise HTTPError: If response status indicates an error
        """
        if not self.ok:
            raise HTTPError(
                f"{self.status_code} Client Error: {self.reason} for url: {self.url}",
                response=self,
            )

    @property
    def reason(self) -> str:
        """HTTP status reason phrase."""
        try:
            return HTTPStatus(self.status_code).phrase
        except ValueError:
            # Status code not in HTTPStatus enum
            return "Unknown"

    def _parse_charset(self) -> str | None:
        """Parse charset from Content-Type header."""
        content_type = self.headers.get("content-type", "")
        if "charset=" in content_type:
            try:
                return content_type.split("charset=")[1].split(";")[0].strip()
            except (IndexError, ValueError):
                pass
        return None

    @property
    def encoding(self) -> str | None:
        """Response encoding."""
        return self._parse_charset()

    def __bool__(self) -> bool:
        """Boolean evaluation returns ok status."""
        return self.ok

    @override
    def __repr__(self) -> str:
        """String representation of the response."""
        return f"<FastlyResponse [{self.status_code}]>"
