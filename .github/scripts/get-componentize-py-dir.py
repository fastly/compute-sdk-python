#!/usr/bin/env python3
"""Get the active directory of the componentize-py cargo dependency."""

import json
import subprocess
import sys
from pathlib import Path


def main():
    try:
        # Run cargo metadata to query current dependencies
        metadata = json.loads(
            subprocess.check_output(
                ["cargo", "metadata", "--format-version=1"], text=True
            )
        )
        # Find the package named "componentize-py"
        pkg = next(p for p in metadata["packages"] if p["name"] == "componentize-py")
        # Print the parent directory of its Cargo.toml manifest with forward slashes
        print(Path(pkg["manifest_path"]).parent.as_posix())
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
