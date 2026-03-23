"""Utility functions for fastly_compute package."""

from io import BufferedReader, RawIOBase

from wit_world.imports import async_io, http_body


class _RawBodyReader(RawIOBase):
    """Raw I/O implementation that reads from a Fastly HTTP body.

    This class provides a streaming interface to read from Fastly HTTP bodies
    without buffering the entire body in memory upfront.
    """

    def __init__(self, body_handle: async_io.Pollable, chunk_size: int = 4096):
        """Initialize the reader.

        :param body_handle: Fastly HTTP body handle to read from
        :param chunk_size: Size of chunks to read at a time (default: 4096)
        """
        self._body = body_handle
        self._chunk_size = chunk_size
        self._closed = False

    def readable(self) -> bool:
        """Return whether the stream is readable.

        :return: True if the stream is readable, False otherwise
        """
        return not self._closed

    def readinto(self, b) -> int:
        """Read up to len(b) bytes into writable buffer b.

        :param b: Writable buffer to read into
        :return: Number of bytes read, or 0 on EOF
        """
        if self._closed:
            return 0

        # Read a chunk from host into provided buffer
        chunk_size = min(len(b), self._chunk_size)
        chunk = http_body.read(self._body, chunk_size)

        if not chunk:
            self._closed = True
            return 0

        # Copy chunk into the provided buffer
        n = len(chunk)
        b[:n] = chunk
        return n


def create_body_reader(
    body: async_io.Pollable, chunk_size: int = 4096
) -> BufferedReader:
    """Create a file-like reader for streaming a Fastly HTTP body.

    This function returns a BufferedReader that streams the body on-demand,
    avoiding the need to buffer the entire body in memory. The returned reader
    is compatible with the WSGI InputStream Protocol (PEP 3333).

    The returned reader supports all standard file operations: read(), readline(),
    readlines(), and iteration. Note that seeking is not supported as the body
    is a forward-only stream.

    :param body: Fastly HTTP body handle to read from
    :param chunk_size: Size of chunks to read at a time (default: 4096)
    :return: A BufferedReader that streams the body content (WSGI compatible)

    Example::

        def handle(request, body):
            reader = create_body_reader(body)
            # Read entire body
            full_body = reader.read()
            # Or read line by line
            for line in reader:
                process(line)
    """
    return BufferedReader(_RawBodyReader(body, chunk_size))
