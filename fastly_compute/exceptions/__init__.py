"""Top-level exceptions emitted by the Fastly API"""


class FastlyError(Exception):
    """Abstract base class for all errors raised by Fastly APIs

    This allows catching all errors emanating from Fastly APIs at once.
    """


class UnexpectedFastlyError(FastlyError):
    """An error arising from a Fastly API but of an unanticipated kind, such
    that we merely package up the low-level error and send it along.

    Any of these encountered in the wild means we neglected to keep our Python
    wrappers up to date with the WIT.
    """

    def __init__(self, error_value: object):
        """Construct.

        :arg error_value: The ``value`` attr of the raised ``Err``
        """
        self.value = error_value


# I went with the exact verbatim names of the error cases, not appending "Error"
# to the ends of the ones that didn't have it to make them strictly conform to
# Python conventions. "except HttpInvalid" reads fine to me.
