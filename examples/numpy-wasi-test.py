"""
NumPy WASI Test - Testing just NumPy with WASI wheels

This is a minimal test to see if we can get NumPy working with WASI wheels
before trying the full pandas integration.
"""

import json
import traceback
from dataclasses import dataclass
from typing import Any, Dict, Optional

from bottle import Bottle
from wit_world.imports import compute_runtime

from fastly_compute.wsgi import WsgiHttpIncoming

# Test WASI NumPy import
try:
    import numpy as np
    NUMPY_WASI_AVAILABLE = True
    NUMPY_VERSION = np.__version__
    NUMPY_IMPORT_ERROR = None
except Exception as e:
    NUMPY_WASI_AVAILABLE = False
    NUMPY_VERSION = None
    NUMPY_IMPORT_ERROR = {
        "error_type": type(e).__name__,
        "error_message": str(e),
        "traceback": traceback.format_exc()
    }

app = Bottle()


@dataclass
class NumPyTest:
    """Simple NumPy test result."""
    operation: str
    success: bool
    result: Any
    error: Optional[str] = None


@app.route("/")
def index():
    """Root endpoint."""
    return {
        "service": "numpy-wasi-test",
        "numpy_available": NUMPY_WASI_AVAILABLE,
        "numpy_version": NUMPY_VERSION,
        "import_error": NUMPY_IMPORT_ERROR,
        "endpoints": ["/", "/test-basic", "/test-advanced", "/test-all"]
    }


@app.route("/test-basic")
def test_basic():
    """Test basic NumPy operations."""
    if not NUMPY_WASI_AVAILABLE:
        return {"error": "NumPy not available", "import_error": NUMPY_IMPORT_ERROR}

    tests = []

    try:
        # Basic array creation
        arr = np.array([1, 2, 3, 4, 5])
        tests.append(NumPyTest("array_creation", True, arr.tolist()))

        # Basic math
        result = np.sum(arr)
        tests.append(NumPyTest("sum", True, int(result)))

        # Array operations
        squared = arr ** 2
        tests.append(NumPyTest("element_wise_power", True, squared.tolist()))

    except Exception as e:
        tests.append(NumPyTest("basic_operations", False, None, str(e)))

    return {"tests": [t.__dict__ for t in tests]}


@app.route("/test-advanced")
def test_advanced():
    """Test advanced NumPy operations."""
    if not NUMPY_WASI_AVAILABLE:
        return {"error": "NumPy not available"}

    tests = []

    try:
        # Matrix operations
        matrix = np.array([[1, 2], [3, 4]])
        det = np.linalg.det(matrix)
        tests.append(NumPyTest("determinant", True, float(det)))

        # Random numbers
        np.random.seed(42)
        random_arr = np.random.rand(5)
        tests.append(NumPyTest("random", True, random_arr.tolist()))

        # Statistics
        data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        mean_val = np.mean(data)
        std_val = np.std(data)
        tests.append(NumPyTest("statistics", True, {"mean": float(mean_val), "std": float(std_val)}))

    except Exception as e:
        tests.append(NumPyTest("advanced_operations", False, None, str(e)))

    return {"tests": [t.__dict__ for t in tests]}


@app.route("/test-all")
def test_all():
    """Run all NumPy tests."""
    vcpu_start = compute_runtime.get_vcpu_ms()

    basic_result = test_basic()
    advanced_result = test_advanced()

    vcpu_end = compute_runtime.get_vcpu_ms()

    return {
        "numpy_wasi_status": {
            "available": NUMPY_WASI_AVAILABLE,
            "version": NUMPY_VERSION,
            "import_error": NUMPY_IMPORT_ERROR
        },
        "basic_tests": basic_result,
        "advanced_tests": advanced_result,
        "execution_time_ms": vcpu_end - vcpu_start,
        "breakthrough": "🎉 NumPy working in WebAssembly!" if NUMPY_WASI_AVAILABLE else None
    }


# Create the HTTP handler
HttpIncoming = WsgiHttpIncoming(app)