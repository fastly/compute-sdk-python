"""Tests for Fastly Compute"""

import sys
from pathlib import Path

# If we are not operating inside a WebAssembly host, make the WIT stubs
# importable.
#
# This allows us to have compatible definitions around for testing and
# typechecking.
try:
    from componentize_py_types import Err  # noqa
except ImportError:
    sys.path.append(str(Path(__file__).parent.parent.parent / "stubs"))
else:
    del Err
