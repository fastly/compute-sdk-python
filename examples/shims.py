"""WASI compatibility shims for common Python modules.

This module provides minimal implementations of native modules that
aren't available in WASI but are required by popular frameworks.
"""

import sys


class ZlibShim:
    """Minimal zlib implementation for WASI compatibility."""

    # Constants that frameworks might expect
    DEFLATED = 8
    MAX_WBITS = 15
    DEF_BUF_SIZE = 16384

    def adler32(self, data, value=1):
        raise NotImplementedError("shim")

    def compress(self, data, level=6):
        raise NotImplementedError("shim")

    def decompress(self, data):
        raise NotImplementedError("shim")

    def crc32(self, data, value=0):
        raise NotImplementedError("shim")

    def compressobj(
        self, level=6, method=None, wbits=None, memLevel=None, strategy=None
    ):
        return CompressObj()

    def decompressobj(self, wbits=None):
        return DecompressObj()


class CompressObj:
    """Mock compression object."""

    def compress(self, data):
        raise NotImplementedError("shim")

    def flush(self):
        raise NotImplementedError("shim")


class DecompressObj:
    """Mock decompression object."""

    def decompress(self, data):
        raise NotImplementedError("shim")

    def flush(self):
        raise NotImplementedError("shim")


def install_shims():
    """Install all WASI compatibility shims."""
    # Install zlib shim
    sys.modules["zlib"] = ZlibShim()

    # Install idna encoding shim
    import codecs

    def idna_encode(input, errors="strict"):
        """Simple IDNA encoder - just return ASCII for basic domains."""
        if isinstance(input, str):
            # For basic ASCII domains, just encode to bytes
            try:
                return input.encode("ascii"), len(input)
            except UnicodeEncodeError:
                # For non-ASCII, try to handle basic cases
                # This is a very simplified implementation
                return input.encode("utf-8"), len(input)
        return input, len(input)

    def idna_decode(input, errors="strict"):
        """Simple IDNA decoder."""
        if isinstance(input, bytes):
            return input.decode("ascii", errors), len(input)
        return input, len(input)

    def idna_search(name):
        """Search function for IDNA codec."""
        if name in ("idna", "idna-2003", "idna-2008"):
            return codecs.CodecInfo(
                name="idna",
                encode=idna_encode,
                decode=idna_decode,
            )
        return None

    # Register the IDNA codec
    codecs.register(idna_search)

    # Add other shims as needed
    # sys.modules['_ssl'] = SSLShim()  # Future
    # sys.modules['_socket'] = SocketShim()  # Future
