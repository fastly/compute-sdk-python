from typing import Any


class FastlyError(Exception):
    """Base class for all Fastly Compute exceptions."""

    def __init__(self, message: str, wit_error: Any | None = None):
        super().__init__(message)
        self.wit_error = wit_error


class ResourceError(FastlyError):
    """Resource open/access errors."""

    pass


class ResourceOpenError(ResourceError):
    """Error opening a resource."""

    pass


class ResourceNotFound(ResourceError):
    """Resource not found."""

    pass


class ResourceLimitExceeded(ResourceError):
    """Quotas or limits exceeded."""

    pass


class BackendError(FastlyError):
    """Backend communication errors."""

    pass


class BadRequestError(FastlyError):
    """Bad Request."""

    pass


class RateLimitExceeded(FastlyError):
    """Rate limit exceeded."""

    pass


# KV Store Specific
class KVStoreError(FastlyError):
    pass


class KVKeyFound(KVStoreError):
    pass


class KVPreconditionFailed(KVStoreError):
    pass


class KVPayloadTooLarge(KVStoreError):
    pass


# ACL Specific
class ACLError(FastlyError):
    pass
