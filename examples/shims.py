"""WASI compatibility shims for common Python modules.

This module provides minimal implementations of native modules that
aren't available in WASI but are required by popular frameworks.
"""


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
