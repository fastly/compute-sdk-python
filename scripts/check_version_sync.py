#!/usr/bin/env python3
"""Check that version numbers are synchronized across the project.

This script ensures that the version in pyproject.toml matches the version
in crates/fastly-compute-py/Cargo.toml. Both files must be kept in sync
to avoid confusion when releasing new versions.

When --tag is passed (or the VERSION environment variable is set), the
in-tree versions are also validated against the expected release version.
The tag is expected to be in the form "vX.Y.Z"; the leading "v" is stripped
before comparison.

Exit codes:
    0: Versions are synchronized (and match the tag, if provided)
    1: Version mismatch detected

Usage:
    # Check file consistency only (used by `make lint`):
    python scripts/check_version_sync.py

    # Also validate against a release tag (used by the release workflow):
    python scripts/check_version_sync.py --tag v1.2.3
    VERSION=v1.2.3 python scripts/check_version_sync.py
"""

import argparse
import os
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


def parse_tag_version(tag: str) -> str:
    """Strip a leading 'v' from a tag to get a bare version string."""
    return tag.lstrip("v")


def main() -> int:
    """Check version consistency and exit with appropriate code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tag",
        metavar="TAG",
        default=os.environ.get("VERSION"),
        help="Expected release tag (e.g. v1.2.3). Also read from $VERSION.",
    )
    args = parser.parse_args()

    pyproject_version = get_pyproject_version()
    cargo_version = get_cargo_version()

    ok = True

    if pyproject_version == cargo_version:
        print(f"✓ pyproject.toml and Cargo.toml are synchronized: {pyproject_version}")
    else:
        print("✗ Version mismatch between pyproject.toml and Cargo.toml:", file=sys.stderr)
        print(f"  pyproject.toml:                    {pyproject_version}", file=sys.stderr)
        print(f"  crates/fastly-compute-py/Cargo.toml: {cargo_version}", file=sys.stderr)
        print("\nUpdate both files to use the same version.", file=sys.stderr)
        ok = False

    if args.tag:
        expected = parse_tag_version(args.tag)
        if pyproject_version == expected and cargo_version == expected:
            print(f"✓ In-tree versions match tag '{args.tag}': {expected}")
        else:
            print(f"✗ In-tree versions do not match tag '{args.tag}':", file=sys.stderr)
            if pyproject_version != expected:
                print(f"  pyproject.toml:                    {pyproject_version} (expected {expected})", file=sys.stderr)
            if cargo_version != expected:
                print(f"  crates/fastly-compute-py/Cargo.toml: {cargo_version} (expected {expected})", file=sys.stderr)
            print("\nBump both files to match the tag before releasing.", file=sys.stderr)
            ok = False

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
