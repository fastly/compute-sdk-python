"""Tests for Wasm producers metadata embedded in the built component.

Verifies that all top-level producers section fields written by
inject_fastly_metadata() are present and correct:

  - language: Python 3.14
  - sdk: fastly-compute-py 0.1.0
  - processed-by: componentize-py 0.22.1
  - processed-by: fastly-compute-py 0.1.0

The language version is also cross-checked against the libpython*.so name
embedded in the component tree to catch version drift when upgrading
componentize-py.
"""

import json
import re
import subprocess
from pathlib import Path

import pytest

WASM_PATH = Path("build/bottle-app.composed.wasm")

# NOTE: these will need to be updated at times but serves as a sanity check
FASTLY_COMPUTE_PY_VERSION = "0.1.0"
COMPONENTIZE_PY_VERSION = "0.22.1"
PYTHON_VERSION = "3.14"


@pytest.fixture(scope="module")
def metadata():
    """Return the parsed wasm-tools metadata JSON for the built component."""
    if not WASM_PATH.exists():
        pytest.fail(f"Built wasm not found at {WASM_PATH}; run `make` first")

    result = subprocess.run(
        ["wasm-tools", "metadata", "show", "--json", str(WASM_PATH)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


@pytest.fixture(scope="module")
def producers(metadata):
    """Return the top-level producers as a {field: {name: version}} dict."""
    raw = metadata["component"]["metadata"]["producers"]
    return dict(raw) if raw else {}


def _libpython_version(metadata) -> str | None:
    """Return the version from the first libpython*.so module name in the tree."""
    nodes = [metadata]
    while nodes:
        node = nodes.pop()
        kind = next(iter(node))
        data = node[kind]
        if kind == "module":
            name = data.get("name")  # may be None or ""
            if name:
                m = re.match(r"libpython(\d+\.\d+)\.so", name)
                if m:
                    return m.group(1)
        else:
            nodes.extend(data.get("children", []))


def test_language_python(producers):
    assert producers.get("language", {}).get("Python") == PYTHON_VERSION


def test_language_python_version_matches_libpython(producers, metadata):
    """Declared Python version must match the libpython*.so embedded by componentize-py.

    If this fails, update PYTHON_VERSION in this file and the hardcoded version
    in crates/fastly-compute-py/src/lib.rs.  This is designed to keep us honest
    and ensure that we don't end up injecting the wrong version as it is
    not trivial to extract this from compnentize-py directly.
    """
    embedded = _libpython_version(metadata)
    assert embedded is not None, "No libpython*.so module found in component tree"
    assert producers["language"]["Python"] == embedded, (
        f"language: Python {producers['language']['Python']!r} does not match "
        f"embedded libpython{embedded}.so — update PYTHON_VERSION in this file "
        "and the hardcoded version in crates/fastly-compute-py/src/lib.rs"
    )


def test_sdk_fastly_compute_py(producers):
    assert (
        producers.get("sdk", {}).get("fastly-compute-py") == FASTLY_COMPUTE_PY_VERSION
    )


def test_processed_by_componentize_py(producers):
    assert (
        producers.get("processed-by", {}).get("componentize-py")
        == COMPONENTIZE_PY_VERSION
    )


def test_processed_by_fastly_compute_py(producers):
    assert (
        producers.get("processed-by", {}).get("fastly-compute-py")
        == FASTLY_COMPUTE_PY_VERSION
    )
