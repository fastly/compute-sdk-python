"""Utility functions for fastly_compute package."""

from wit_world.imports import http_body


def read_response_body(response_body, chunk_size: int = 4096) -> bytes:
    """Read the complete response body from a WIT response body object.

    Args:
        response_body: WIT response body object to read from
        chunk_size: Size of chunks to read at a time (default: 4096)

    Returns:
        Complete response body as bytes
    """
    body_data = b""

    try:
        while True:
            chunk = http_body.read(response_body, chunk_size)
            if not chunk:
                break
            body_data += chunk
    except Exception:
        # If reading fails, return what we have so far
        pass

    return body_data
