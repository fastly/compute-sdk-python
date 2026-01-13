"""Utility functions for fastly_compute package."""

from wit_world.imports import async_io, http_body
from wit_world.types import Err

from fastly_compute.requests.exceptions import RequestException


def read_response_body(
    response_body: async_io.Pollable, chunk_size: int = 4096
) -> bytes:
    """Read the complete response body from a WIT response body object.

    Args:
        response_body: WIT response body object to read from
        chunk_size: Size of chunks to read at a time (default: 4096)

    Returns:
        Complete response body as bytes

    Raises:
        RequestException: If there is a problem reading the response body.
    """
    body_data: bytes = b""
    while True:
        try:
            chunk = http_body.read(response_body, chunk_size)
        except Err as e:
            raise RequestException.from_wit_error(e, "http_body.read") from e

        if len(chunk) == 0:
            break
        else:
            body_data += chunk

    return body_data
