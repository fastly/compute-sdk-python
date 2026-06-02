#!/usr/bin/env python3
"""Bump version numbers across the project for a new release.

Updates the version in:
  - pyproject.toml
  - crates/fastly-compute-py/Cargo.toml

And then runs `cargo metadata` to update Cargo.lock and
`uv lock` in the base and for all examples.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def update_file_version(file_path: Path, pattern: str, replacement: str) -> None:
    """Read a file, replace a version pattern, and write it back."""
    content = file_path.read_text()
    new_content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)
    if count == 0:
        raise ValueError(f"Could not find version pattern in {file_path}")
    file_path.write_text(new_content, encoding="utf-8")
    print(f"✓ Updated version in {file_path.relative_to(file_path.parents[1])}")


def main() -> int:
    """Parse arguments, validate the version, and update all configuration files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "version",
        help="The new version string (e.g., 0.2.0 or 0.1.1)",
    )
    args = parser.parse_args()

    # Validate version format (semantic versioning: X.Y.Z)
    new_version = args.version.lstrip("v")
    if not re.match(r"^\d+\.\d+\.\d+(?:-\w+)?$", new_version):
        print(
            f"Error: version '{args.version}' is not a valid semantic version",
            file=sys.stderr,
        )
        return 1

    root_dir = Path(__file__).parent.parent
    pyproject_path = root_dir / "pyproject.toml"
    cargo_path = root_dir / "crates" / "fastly-compute-py" / "Cargo.toml"

    # pyrpoject.toml: Matches `version = "X.Y.Z"` under [project]
    update_file_version(pyproject_path, r'(?<=^version = ")[^"]+', new_version)

    # Cargo.toml: Matches `version = "X.Y.Z"` under [package]
    update_file_version(cargo_path, r'(?<=^version = ")[^"]+', new_version)

    # Update Cargo.lock
    print("Updating Cargo.lock...")
    subprocess.check_call(
        ["cargo", "metadata", "--format-version=1"], stdout=subprocess.DEVNULL
    )
    print("✓ Updated Cargo.lock")

    # Update workspace uv.lock
    print("Updating workspace uv.lock...")
    subprocess.check_call(["uv", "lock"])
    print("✓ Updated workspace uv.lock")

    # Update example uv.lock files
    print("Updating example uv.lock files...")
    examples_dir = root_dir / "examples"
    for example_path in examples_dir.iterdir():
        if example_path.is_dir() and (example_path / "pyproject.toml").exists():
            print(f"  - Updating {example_path.name}/uv.lock...")
            subprocess.check_call(["uv", "lock"], cwd=example_path)
            print("✓ Updated all example uv.lock files")

    print(f"\nSuccessfully bumped version to {new_version} across the project!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
