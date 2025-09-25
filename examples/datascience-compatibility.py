"""
Data Science Library Compatibility Example

This example demonstrates compatibility with popular Python data science libraries
in the Fastly Compute environment. Some libraries may not work due to:
- Native dependencies not available in WASM
- Missing system libraries
- File system access limitations
- Memory constraints

This serves as a compatibility test and demonstration of what works vs what doesn't.
"""

import json
import traceback
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from bottle import Bottle
from wit_world.imports import compute_runtime

from fastly_compute.wsgi import WsgiHttpIncoming

# Top-level imports for componentize-py compatibility
# These will fail gracefully if not available in WASM
try:
    import numpy as np
    NUMPY_AVAILABLE = True
    NUMPY_VERSION = np.__version__
    NUMPY_IMPORT_ERROR = None
except ImportError as e:
    NUMPY_AVAILABLE = False
    NUMPY_VERSION = None
    NUMPY_IMPORT_ERROR = {
        "error_type": type(e).__name__,
        "error_message": str(e),
        "traceback": traceback.format_exc()
    }
except Exception as e:
    NUMPY_AVAILABLE = False
    NUMPY_VERSION = None
    NUMPY_IMPORT_ERROR = {
        "error_type": type(e).__name__,
        "error_message": f"Unexpected error during NumPy import: {str(e)}",
        "traceback": traceback.format_exc()
    }

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
    PANDAS_VERSION = pd.__version__
    PANDAS_IMPORT_ERROR = None
except ImportError as e:
    PANDAS_AVAILABLE = False
    PANDAS_VERSION = None
    PANDAS_IMPORT_ERROR = {
        "error_type": type(e).__name__,
        "error_message": str(e),
        "traceback": traceback.format_exc()
    }
except Exception as e:
    PANDAS_AVAILABLE = False
    PANDAS_VERSION = None
    PANDAS_IMPORT_ERROR = {
        "error_type": type(e).__name__,
        "error_message": f"Unexpected error during Pandas import: {str(e)}",
        "traceback": traceback.format_exc()
    }

try:
    import scipy
    from scipy import stats
    SCIPY_AVAILABLE = True
    SCIPY_VERSION = scipy.__version__
    SCIPY_IMPORT_ERROR = None
except ImportError as e:
    SCIPY_AVAILABLE = False
    SCIPY_VERSION = None
    SCIPY_IMPORT_ERROR = {
        "error_type": type(e).__name__,
        "error_message": str(e),
        "traceback": traceback.format_exc()
    }
except Exception as e:
    SCIPY_AVAILABLE = False
    SCIPY_VERSION = None
    SCIPY_IMPORT_ERROR = {
        "error_type": type(e).__name__,
        "error_message": f"Unexpected error during SciPy import: {str(e)}",
        "traceback": traceback.format_exc()
    }

try:
    import sklearn
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import train_test_split
    SKLEARN_AVAILABLE = True
    SKLEARN_VERSION = sklearn.__version__
    SKLEARN_IMPORT_ERROR = None
except ImportError as e:
    SKLEARN_AVAILABLE = False
    SKLEARN_VERSION = None
    SKLEARN_IMPORT_ERROR = {
        "error_type": type(e).__name__,
        "error_message": str(e),
        "traceback": traceback.format_exc()
    }
except Exception as e:
    SKLEARN_AVAILABLE = False
    SKLEARN_VERSION = None
    SKLEARN_IMPORT_ERROR = {
        "error_type": type(e).__name__,
        "error_message": f"Unexpected error during scikit-learn import: {str(e)}",
        "traceback": traceback.format_exc()
    }

try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-GUI backend
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
    MATPLOTLIB_VERSION = matplotlib.__version__
    MATPLOTLIB_IMPORT_ERROR = None
except ImportError as e:
    MATPLOTLIB_AVAILABLE = False
    MATPLOTLIB_VERSION = None
    MATPLOTLIB_IMPORT_ERROR = {
        "error_type": type(e).__name__,
        "error_message": str(e),
        "traceback": traceback.format_exc()
    }
except Exception as e:
    MATPLOTLIB_AVAILABLE = False
    MATPLOTLIB_VERSION = None
    MATPLOTLIB_IMPORT_ERROR = {
        "error_type": type(e).__name__,
        "error_message": f"Unexpected error during Matplotlib import: {str(e)}",
        "traceback": traceback.format_exc()
    }

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
    JSONSCHEMA_VERSION = jsonschema.__version__
    JSONSCHEMA_IMPORT_ERROR = None
except ImportError as e:
    JSONSCHEMA_AVAILABLE = False
    JSONSCHEMA_VERSION = None
    JSONSCHEMA_IMPORT_ERROR = {
        "error_type": type(e).__name__,
        "error_message": str(e),
        "traceback": traceback.format_exc()
    }
except Exception as e:
    JSONSCHEMA_AVAILABLE = False
    JSONSCHEMA_VERSION = None
    JSONSCHEMA_IMPORT_ERROR = {
        "error_type": type(e).__name__,
        "error_message": f"Unexpected error during jsonschema import: {str(e)}",
        "traceback": traceback.format_exc()
    }


@dataclass
class LibraryTest:
    """Result of testing a library."""

    name: str
    version: Optional[str]
    import_success: bool
    basic_operation_success: bool
    error_message: Optional[str]
    details: Optional[Dict[str, Any]] = None
    import_error: Optional[Dict[str, Any]] = None


app = Bottle()


def create_library_test(name: str, available: bool, version: str = None, import_error: Dict[str, Any] = None) -> LibraryTest:
    """Create a LibraryTest result based on availability."""
    return LibraryTest(
        name=name,
        version=version,
        import_success=available,
        basic_operation_success=False,
        error_message=None if available else f"{name} not available in WASM environment",
        import_error=import_error
    )


def test_numpy() -> LibraryTest:
    """Test NumPy compatibility."""
    result = create_library_test("NumPy", NUMPY_AVAILABLE, NUMPY_VERSION, NUMPY_IMPORT_ERROR)
    if not result.import_success:
        return result

    try:
        # Test basic array operations
        arr = np.array([1, 2, 3, 4, 5])
        mean_val = np.mean(arr)
        std_val = np.std(arr)

        result.basic_operation_success = True
        result.details = {
            "array_creation": "success",
            "basic_stats": {"mean": float(mean_val), "std": float(std_val)},
            "array_shape": arr.shape,
            "dtype": str(arr.dtype)
        }

    except Exception as e:
        result.error_message = f"Basic operations failed: {str(e)}"
        result.details = {"traceback": traceback.format_exc()}

    return result


def test_pandas() -> LibraryTest:
    """Test Pandas compatibility."""
    result = create_library_test("Pandas", PANDAS_AVAILABLE, PANDAS_VERSION, PANDAS_IMPORT_ERROR)
    if not result.import_success:
        return result

    try:
        # Test basic DataFrame operations
        data = {"A": [1, 2, 3], "B": [4, 5, 6], "C": ["x", "y", "z"]}
        df = pd.DataFrame(data)

        result.basic_operation_success = True
        result.details = {
            "dataframe_creation": "success",
            "shape": df.shape,
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "basic_stats": df.describe().to_dict() if len(df.select_dtypes(include="number").columns) > 0 else None
        }

    except Exception as e:
        result.error_message = f"Basic operations failed: {str(e)}"
        result.details = {"traceback": traceback.format_exc()}

    return result


def test_scipy() -> LibraryTest:
    """Test SciPy compatibility."""
    result = create_library_test("SciPy", SCIPY_AVAILABLE, SCIPY_VERSION, SCIPY_IMPORT_ERROR)
    if not result.import_success:
        return result

    try:
        # Test basic statistical functions
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        norm_test = stats.normaltest(data)

        result.basic_operation_success = True
        result.details = {
            "stats_module": "success",
            "normaltest_result": {"statistic": float(norm_test.statistic), "pvalue": float(norm_test.pvalue)}
        }

    except Exception as e:
        result.error_message = f"Basic operations failed: {str(e)}"
        result.details = {"traceback": traceback.format_exc()}

    return result


def test_scikit_learn() -> LibraryTest:
    """Test scikit-learn compatibility."""
    result = create_library_test("scikit-learn", SKLEARN_AVAILABLE, SKLEARN_VERSION, SKLEARN_IMPORT_ERROR)
    if not result.import_success:
        return result

    try:
        # Need NumPy for sklearn operations
        if not NUMPY_AVAILABLE:
            result.error_message = "scikit-learn requires NumPy which is not available"
            return result

        # Test basic ML operations
        X = np.array([[1], [2], [3], [4], [5]])
        y = np.array([2, 4, 6, 8, 10])

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        model = LinearRegression()
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)

        result.basic_operation_success = True
        result.details = {
            "model_training": "success",
            "coefficients": model.coef_.tolist(),
            "intercept": float(model.intercept_),
            "test_predictions": predictions.tolist()
        }

    except Exception as e:
        result.error_message = f"Basic operations failed: {str(e)}"
        result.details = {"traceback": traceback.format_exc()}

    return result


def test_matplotlib() -> LibraryTest:
    """Test Matplotlib compatibility."""
    result = create_library_test("Matplotlib", MATPLOTLIB_AVAILABLE, MATPLOTLIB_VERSION, MATPLOTLIB_IMPORT_ERROR)
    if not result.import_success:
        return result

    try:
        # Test basic plotting (without saving/displaying)
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3, 4], [1, 4, 2, 3])
        ax.set_title("Test Plot")

        result.basic_operation_success = True
        result.details = {
            "backend": matplotlib.get_backend(),
            "plot_creation": "success"
        }

        plt.close(fig)  # Clean up

    except Exception as e:
        result.error_message = f"Basic operations failed: {str(e)}"
        result.details = {"traceback": traceback.format_exc()}

    return result


def test_json_libraries() -> LibraryTest:
    """Test JSON processing libraries."""
    result = LibraryTest(
        name="JSON Processing",
        version=JSONSCHEMA_VERSION,
        import_success=True,  # stdlib json is always available
        basic_operation_success=False,
        error_message=None,
        import_error=JSONSCHEMA_IMPORT_ERROR  # Only for jsonschema, not stdlib json
    )

    try:
        # Test JSON operations (stdlib)
        data = {"name": "test", "values": [1, 2, 3], "nested": {"key": "value"}}
        json_str = json.dumps(data)
        parsed_data = json.loads(json_str)

        details = {
            "json_stdlib": "success",
            "data_roundtrip": parsed_data == data
        }

        # Test JSON schema validation if available
        if JSONSCHEMA_AVAILABLE:
            schema = {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "values": {"type": "array", "items": {"type": "number"}}
                },
                "required": ["name"]
            }

            jsonschema.validate(parsed_data, schema)
            details["jsonschema"] = "success"
        else:
            details["jsonschema"] = "not_available"

        result.basic_operation_success = True
        result.details = details

    except Exception as e:
        result.error_message = f"JSON operations failed: {str(e)}"
        result.details = {"traceback": traceback.format_exc()}

    return result


@app.route("/")
def index():
    """Root endpoint showing available tests."""
    vcpu_time = compute_runtime.get_vcpu_ms()

    return {
        "service": "fastly-compute-datascience-compatibility",
        "status": "ok",
        "vcpu_time_ms": vcpu_time,
        "description": "Data science library compatibility testing for Fastly Compute",
        "endpoints": [
            "/ - This info page",
            "/import-status - Show import status and errors for all libraries",
            "/test-all - Run all compatibility tests",
            "/test-numpy - Test NumPy compatibility",
            "/test-pandas - Test Pandas compatibility",
            "/test-scipy - Test SciPy compatibility",
            "/test-sklearn - Test scikit-learn compatibility",
            "/test-matplotlib - Test Matplotlib compatibility",
            "/test-json - Test JSON processing libraries",
        ],
        "note": "Many libraries may not work due to WASM environment limitations"
    }


@app.route("/import-status")
def import_status():
    """Show import status and detailed error information for all libraries."""
    libraries = [
        {
            "name": "NumPy",
            "available": NUMPY_AVAILABLE,
            "version": NUMPY_VERSION,
            "import_error": NUMPY_IMPORT_ERROR
        },
        {
            "name": "Pandas",
            "available": PANDAS_AVAILABLE,
            "version": PANDAS_VERSION,
            "import_error": PANDAS_IMPORT_ERROR
        },
        {
            "name": "SciPy",
            "available": SCIPY_AVAILABLE,
            "version": SCIPY_VERSION,
            "import_error": SCIPY_IMPORT_ERROR
        },
        {
            "name": "scikit-learn",
            "available": SKLEARN_AVAILABLE,
            "version": SKLEARN_VERSION,
            "import_error": SKLEARN_IMPORT_ERROR
        },
        {
            "name": "Matplotlib",
            "available": MATPLOTLIB_AVAILABLE,
            "version": MATPLOTLIB_VERSION,
            "import_error": MATPLOTLIB_IMPORT_ERROR
        },
        {
            "name": "jsonschema",
            "available": JSONSCHEMA_AVAILABLE,
            "version": JSONSCHEMA_VERSION,
            "import_error": JSONSCHEMA_IMPORT_ERROR
        }
    ]

    available_count = sum(1 for lib in libraries if lib["available"])
    total_count = len(libraries)

    return {
        "summary": {
            "total_libraries": total_count,
            "available_libraries": available_count,
            "unavailable_libraries": total_count - available_count,
            "availability_rate": f"{available_count/total_count*100:.1f}%"
        },
        "libraries": libraries,
        "note": "Import errors contain detailed information about why libraries failed to load"
    }


@app.route("/test-all")
def test_all_libraries():
    """Run all compatibility tests."""
    vcpu_start = compute_runtime.get_vcpu_ms()

    tests = [
        test_numpy,
        test_pandas,
        test_scipy,
        test_scikit_learn,
        test_matplotlib,
        test_json_libraries,
    ]

    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result.__dict__)
        except Exception as e:
            results.append({
                "name": test_func.__name__.replace("test_", ""),
                "version": None,
                "import_success": False,
                "basic_operation_success": False,
                "error_message": f"Test function failed: {str(e)}",
                "details": {"traceback": traceback.format_exc()}
            })

    vcpu_end = compute_runtime.get_vcpu_ms()

    # Summary statistics
    total_tests = len(results)
    import_successes = sum(1 for r in results if r["import_success"])
    operation_successes = sum(1 for r in results if r["basic_operation_success"])

    return {
        "summary": {
            "total_tests": total_tests,
            "import_successes": import_successes,
            "operation_successes": operation_successes,
            "import_success_rate": f"{import_successes/total_tests*100:.1f}%",
            "operation_success_rate": f"{operation_successes/total_tests*100:.1f}%",
        },
        "execution_time_ms": vcpu_end - vcpu_start,
        "results": results,
        "environment_info": {
            "python_version": "3.12+",
            "platform": "wasm32-wasi",
            "runtime": "fastly-compute"
        }
    }


@app.route("/test-numpy")
def test_numpy_endpoint():
    """Test NumPy compatibility."""
    result = test_numpy()
    return {"test": "numpy", "result": result.__dict__}


@app.route("/test-pandas")
def test_pandas_endpoint():
    """Test Pandas compatibility."""
    result = test_pandas()
    return {"test": "pandas", "result": result.__dict__}


@app.route("/test-scipy")
def test_scipy_endpoint():
    """Test SciPy compatibility."""
    result = test_scipy()
    return {"test": "scipy", "result": result.__dict__}


@app.route("/test-sklearn")
def test_sklearn_endpoint():
    """Test scikit-learn compatibility."""
    result = test_scikit_learn()
    return {"test": "scikit-learn", "result": result.__dict__}


@app.route("/test-matplotlib")
def test_matplotlib_endpoint():
    """Test Matplotlib compatibility."""
    result = test_matplotlib()
    return {"test": "matplotlib", "result": result.__dict__}




@app.route("/test-json")
def test_json_endpoint():
    """Test JSON processing libraries."""
    result = test_json_libraries()
    return {"test": "json-processing", "result": result.__dict__}


# Create the HTTP handler
HttpIncoming = WsgiHttpIncoming(app)