"""
WASI-Enabled Data Science Example

This example demonstrates using REAL numpy and pandas libraries in the Fastly Compute
environment via WASI wheels. This is a breakthrough - actual data science libraries
running in WebAssembly at the edge!

WASI wheels provide pre-compiled WebAssembly versions of popular Python packages
that normally wouldn't work in WASM environments due to native dependencies.
"""

import json
import traceback
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from bottle import Bottle
from wit_world.imports import compute_runtime

from fastly_compute.wsgi import WsgiHttpIncoming

# Top-level imports of WASI wheels
# These should succeed with the WASI-compiled versions
try:
    import numpy as np
    NUMPY_WASI_AVAILABLE = True
    NUMPY_VERSION = np.__version__
    NUMPY_IMPORT_ERROR = None
except ImportError as e:
    NUMPY_WASI_AVAILABLE = False
    NUMPY_VERSION = None
    NUMPY_IMPORT_ERROR = {
        "error_type": type(e).__name__,
        "error_message": str(e),
        "traceback": traceback.format_exc()
    }
except Exception as e:
    NUMPY_WASI_AVAILABLE = False
    NUMPY_VERSION = None
    NUMPY_IMPORT_ERROR = {
        "error_type": type(e).__name__,
        "error_message": f"Unexpected error during NumPy WASI import: {str(e)}",
        "traceback": traceback.format_exc()
    }

try:
    import pandas as pd
    PANDAS_WASI_AVAILABLE = True
    PANDAS_VERSION = pd.__version__
    PANDAS_IMPORT_ERROR = None
except ImportError as e:
    PANDAS_WASI_AVAILABLE = False
    PANDAS_VERSION = None
    PANDAS_IMPORT_ERROR = {
        "error_type": type(e).__name__,
        "error_message": str(e),
        "traceback": traceback.format_exc()
    }
except Exception as e:
    PANDAS_WASI_AVAILABLE = False
    PANDAS_VERSION = None
    PANDAS_IMPORT_ERROR = {
        "error_type": type(e).__name__,
        "error_message": f"Unexpected error during Pandas WASI import: {str(e)}",
        "traceback": traceback.format_exc()
    }


@dataclass
class WASILibraryTest:
    """Result of testing a WASI library."""

    name: str
    version: Optional[str]
    wasi_available: bool
    operations_successful: bool
    error_message: Optional[str]
    import_error: Optional[Dict[str, Any]] = None
    test_results: Optional[Dict[str, Any]] = None


app = Bottle()


def test_numpy_wasi() -> WASILibraryTest:
    """Test NumPy WASI wheel functionality."""
    result = WASILibraryTest(
        name="NumPy (WASI)",
        version=NUMPY_VERSION,
        wasi_available=NUMPY_WASI_AVAILABLE,
        operations_successful=False,
        error_message=None,
        import_error=NUMPY_IMPORT_ERROR
    )

    if not result.wasi_available:
        return result

    try:
        # Test basic array operations
        arr = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

        # Mathematical operations
        mean_val = np.mean(arr)
        std_val = np.std(arr)
        sum_val = np.sum(arr)

        # Array manipulations
        reshaped = arr.reshape(2, 5)
        transposed = reshaped.T

        # Linear algebra
        matrix = np.array([[1, 2], [3, 4]])
        det = np.linalg.det(matrix)

        # Random operations
        np.random.seed(42)
        random_array = np.random.rand(5)

        result.operations_successful = True
        result.test_results = {
            "basic_stats": {
                "mean": float(mean_val),
                "std": float(std_val),
                "sum": int(sum_val)
            },
            "array_operations": {
                "original_shape": arr.shape,
                "reshaped": reshaped.shape,
                "transposed": transposed.shape
            },
            "linear_algebra": {
                "determinant": float(det)
            },
            "random_sample": random_array.tolist()[:3]  # First 3 elements
        }

    except Exception as e:
        result.error_message = f"NumPy operations failed: {str(e)}"
        result.test_results = {"traceback": traceback.format_exc()}

    return result


def test_pandas_wasi() -> WASILibraryTest:
    """Test Pandas WASI wheel functionality."""
    result = WASILibraryTest(
        name="Pandas (WASI)",
        version=PANDAS_VERSION,
        wasi_available=PANDAS_WASI_AVAILABLE,
        operations_successful=False,
        error_message=None,
        import_error=PANDAS_IMPORT_ERROR
    )

    if not result.wasi_available:
        return result

    # Pandas requires NumPy
    if not NUMPY_WASI_AVAILABLE:
        result.error_message = "Pandas requires NumPy which is not available"
        return result

    try:
        # Create DataFrame
        data = {
            'name': ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve'],
            'age': [25, 30, 35, 28, 32],
            'score': [85.5, 92.0, 78.5, 88.0, 95.5],
            'city': ['NYC', 'LA', 'Chicago', 'Houston', 'Phoenix']
        }
        df = pd.DataFrame(data)

        # Basic operations
        mean_age = df['age'].mean()
        max_score = df['score'].max()

        # Filtering
        high_scorers = df[df['score'] > 85]

        # Grouping and aggregation
        city_stats = df.groupby('city').agg({'age': 'mean', 'score': 'sum'})

        # Data manipulation
        df['age_category'] = df['age'].apply(lambda x: 'Young' if x < 30 else 'Mature')

        result.operations_successful = True
        result.test_results = {
            "dataframe_info": {
                "shape": df.shape,
                "columns": list(df.columns),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()}
            },
            "statistics": {
                "mean_age": float(mean_age),
                "max_score": float(max_score),
                "high_scorers_count": len(high_scorers)
            },
            "sample_data": df.head(3).to_dict('records'),
            "groupby_results": city_stats.to_dict()
        }

    except Exception as e:
        result.error_message = f"Pandas operations failed: {str(e)}"
        result.test_results = {"traceback": traceback.format_exc()}

    return result


def test_numpy_pandas_integration() -> WASILibraryTest:
    """Test NumPy and Pandas working together."""
    result = WASILibraryTest(
        name="NumPy + Pandas Integration (WASI)",
        version=f"numpy={NUMPY_VERSION}, pandas={PANDAS_VERSION}",
        wasi_available=NUMPY_WASI_AVAILABLE and PANDAS_WASI_AVAILABLE,
        operations_successful=False,
        error_message=None
    )

    if not result.wasi_available:
        if not NUMPY_WASI_AVAILABLE:
            result.error_message = "NumPy WASI not available"
        elif not PANDAS_WASI_AVAILABLE:
            result.error_message = "Pandas WASI not available"
        return result

    try:
        # Create NumPy arrays
        np.random.seed(42)
        x = np.linspace(0, 10, 50)
        y = 2 * x + 1 + np.random.normal(0, 1, 50)

        # Create DataFrame from NumPy arrays
        df = pd.DataFrame({'x': x, 'y': y})

        # Use pandas with numpy operations
        df['y_squared'] = np.square(df['y'])
        df['moving_avg'] = df['y'].rolling(window=5).mean()

        # Statistical analysis
        correlation = np.corrcoef(df['x'].values, df['y'].values)[0, 1]

        # Linear regression using numpy
        coeffs = np.polyfit(df['x'].values, df['y'].values, 1)

        result.operations_successful = True
        result.test_results = {
            "dataset_info": {
                "rows": len(df),
                "correlation": float(correlation),
                "linear_fit": {
                    "slope": float(coeffs[0]),
                    "intercept": float(coeffs[1])
                }
            },
            "sample_results": df.head(5).to_dict('records'),
            "summary_stats": {
                "x_mean": float(df['x'].mean()),
                "y_mean": float(df['y'].mean()),
                "y_squared_mean": float(df['y_squared'].mean())
            }
        }

    except Exception as e:
        result.error_message = f"Integration test failed: {str(e)}"
        result.test_results = {"traceback": traceback.format_exc()}

    return result


@app.route("/")
def index():
    """Root endpoint showing WASI data science capabilities."""
    vcpu_time = compute_runtime.get_vcpu_ms()

    return {
        "service": "fastly-compute-datascience-wasi",
        "status": "ok",
        "vcpu_time_ms": vcpu_time,
        "description": "WASI-enabled data science with real numpy and pandas!",
        "wasi_status": {
            "numpy": {
                "available": NUMPY_WASI_AVAILABLE,
                "version": NUMPY_VERSION
            },
            "pandas": {
                "available": PANDAS_WASI_AVAILABLE,
                "version": PANDAS_VERSION
            }
        },
        "endpoints": [
            "/ - This info page",
            "/wasi-status - Detailed WASI library status",
            "/test-numpy-wasi - Test NumPy WASI functionality",
            "/test-pandas-wasi - Test Pandas WASI functionality",
            "/test-integration - Test NumPy + Pandas integration",
            "/test-all-wasi - Run all WASI tests",
            "/benchmark - Performance comparison"
        ],
        "breakthrough": "🎉 Real data science libraries running in WebAssembly!"
    }


@app.route("/wasi-status")
def wasi_status():
    """Detailed status of WASI libraries."""
    return {
        "wasi_libraries": {
            "numpy": {
                "available": NUMPY_WASI_AVAILABLE,
                "version": NUMPY_VERSION,
                "import_error": NUMPY_IMPORT_ERROR
            },
            "pandas": {
                "available": PANDAS_WASI_AVAILABLE,
                "version": PANDAS_VERSION,
                "import_error": PANDAS_IMPORT_ERROR
            }
        },
        "environment": {
            "python_version": "3.12+",
            "platform": "wasm32-wasi",
            "runtime": "fastly-compute",
            "wasi_wheels_source": "github.com/dicej/wasi-wheels"
        },
        "capabilities": {
            "numpy_arrays": NUMPY_WASI_AVAILABLE,
            "pandas_dataframes": PANDAS_WASI_AVAILABLE,
            "data_science_stack": NUMPY_WASI_AVAILABLE and PANDAS_WASI_AVAILABLE
        }
    }


@app.route("/test-numpy-wasi")
def test_numpy_endpoint():
    """Test NumPy WASI wheel."""
    result = test_numpy_wasi()
    return {"test": "numpy-wasi", "result": result.__dict__}


@app.route("/test-pandas-wasi")
def test_pandas_endpoint():
    """Test Pandas WASI wheel."""
    result = test_pandas_wasi()
    return {"test": "pandas-wasi", "result": result.__dict__}


@app.route("/test-integration")
def test_integration_endpoint():
    """Test NumPy + Pandas integration."""
    result = test_numpy_pandas_integration()
    return {"test": "integration", "result": result.__dict__}


@app.route("/test-all-wasi")
def test_all_wasi():
    """Run all WASI library tests."""
    vcpu_start = compute_runtime.get_vcpu_ms()

    tests = [
        ("numpy-wasi", test_numpy_wasi),
        ("pandas-wasi", test_pandas_wasi),
        ("integration", test_numpy_pandas_integration)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append({
                "test_name": test_name,
                "result": result.__dict__
            })
        except Exception as e:
            results.append({
                "test_name": test_name,
                "result": {
                    "name": test_name,
                    "wasi_available": False,
                    "operations_successful": False,
                    "error_message": f"Test function failed: {str(e)}",
                    "test_results": {"traceback": traceback.format_exc()}
                }
            })

    vcpu_end = compute_runtime.get_vcpu_ms()

    # Summary statistics
    total_tests = len(results)
    available_count = sum(1 for r in results if r["result"].get("wasi_available", False))
    successful_count = sum(1 for r in results if r["result"].get("operations_successful", False))

    return {
        "summary": {
            "total_tests": total_tests,
            "wasi_available": available_count,
            "operations_successful": successful_count,
            "success_rate": f"{successful_count/total_tests*100:.1f}%",
            "execution_time_ms": vcpu_end - vcpu_start
        },
        "results": results,
        "milestone": "🚀 First working data science stack in Fastly Compute!" if successful_count > 1 else None
    }


@app.route("/benchmark")
def benchmark():
    """Simple performance benchmark of WASI libraries."""
    if not (NUMPY_WASI_AVAILABLE and PANDAS_WASI_AVAILABLE):
        return {
            "error": "Both NumPy and Pandas WASI required for benchmarking",
            "available": {
                "numpy": NUMPY_WASI_AVAILABLE,
                "pandas": PANDAS_WASI_AVAILABLE
            }
        }

    vcpu_start = compute_runtime.get_vcpu_ms()

    try:
        # NumPy benchmark
        np.random.seed(42)
        large_array = np.random.rand(1000, 100)
        matrix_mult = np.dot(large_array, large_array.T)
        eigenvals = np.linalg.eigvals(matrix_mult[:50, :50])  # Smaller for speed

        vcpu_numpy = compute_runtime.get_vcpu_ms()

        # Pandas benchmark
        df = pd.DataFrame(large_array[:1000, :10])
        df_processed = df.groupby(df.columns[0] > 0.5).agg('mean')
        correlation_matrix = df.corr()

        vcpu_pandas = compute_runtime.get_vcpu_ms()

        return {
            "benchmark_results": {
                "numpy_operations": {
                    "array_size": large_array.shape,
                    "matrix_multiplication": "completed",
                    "eigenvalues_computed": len(eigenvals),
                    "time_ms": vcpu_numpy - vcpu_start
                },
                "pandas_operations": {
                    "dataframe_size": df.shape,
                    "groupby_aggregation": "completed",
                    "correlation_matrix": correlation_matrix.shape,
                    "time_ms": vcpu_pandas - vcpu_numpy
                },
                "total_time_ms": vcpu_pandas - vcpu_start
            },
            "performance_note": "Running in WebAssembly with WASI wheels!"
        }

    except Exception as e:
        return {
            "benchmark_error": str(e),
            "traceback": traceback.format_exc(),
            "time_ms": compute_runtime.get_vcpu_ms() - vcpu_start
        }


# Create the HTTP handler
HttpIncoming = WsgiHttpIncoming(app)