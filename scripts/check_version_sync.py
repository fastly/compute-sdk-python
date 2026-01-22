#!/usr/bin/env python3
"""Check that version numbers are synchronized across the project.

This script ensures that the version in pyproject.toml matches the version
in crates/fastly-compute-py/Cargo.toml. Both files must be kept in sync
to avoid confusion when releasing new versions.

Exit codes:
    0: Versions are synchronized
    1: Version mismatch detected

Usage:
    python scripts/check_version_sync.py
"""

import sys
import tomllib
from pathlib import Path


def get_pyproject_version() -> str:
    """Get version from pyproject.toml."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def get_cargo_version() -> str:
    """Get version from Cargo.toml."""
    cargo_path = (
        Path(__file__).parent.parent / "crates" / "fastly-compute-py" / "Cargo.toml"
    )
    with open(cargo_path, "rb") as f:
        data = tomllib.load(f)
    return data["package"]["version"]


def main() -> int:
    """Check version consistency and exit with appropriate code."""
    pyproject_version = get_pyproject_version()
    cargo_version = get_cargo_version()

    if pyproject_version == cargo_version:
        print(f"✓ Version numbers are synchronized: {pyproject_version}")
        return 0
    else:
        print("✗ Version mismatch detected:", file=sys.stderr)
        print(f"  pyproject.toml: {pyproject_version}", file=sys.stderr)
        print(
            f"  crates/fastly-compute-py/Cargo.toml: {cargo_version}", file=sys.stderr
        )
        print("\nPlease update both files to use the same version.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
