"""Tests for the fastly-compute-py dependencies command.

Verifies that the dependencies subcommand outputs a {"name": "version"} JSON
map that matches what gets injected into fastly_data metadata.
"""

import json
import subprocess
from pathlib import Path

import pytest

BOTTLE_APP_DIR = Path(__file__).parent.parent.parent / "examples" / "bottle-app"


@pytest.fixture(scope="module")
def dependencies_output():
    """Run fastly-compute-py dependencies and return parsed JSON output."""
    result = subprocess.run(
        ["uv", "run", "fastly-compute-py", "dependencies", "--format", "json"],
        cwd=BOTTLE_APP_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_dependencies_includes_bottle(dependencies_output):
    """Verify bottle is present with the correct version."""
    assert dependencies_output.get("bottle") == "0.13.4"


def test_dependencies_local_package_recorded_as_unknown(dependencies_output):
    """Local source-tree dependencies have no version per PEP 751.

    fastly-compute is declared as ``path = "../../", editable = true`` so
    the pylock.toml has no version field for it.  We record "unknown" rather
    than silently omitting the dependency.
    """
    assert dependencies_output.get("fastly-compute") == "unknown"
