#!/usr/bin/env python
"""Script to package all starter kits under starter-kits/ into dist/."""

import zipfile
from pathlib import Path


def package_starter_kits():
    """Discover and package starter kits as zips in dist/ directory"""
    # Base directory of the repository (parent of scripts/)
    repo_root = Path(__file__).resolve().parent.parent
    starter_kits_dir = repo_root / "starter-kits"
    dist_dir = repo_root / "dist"

    # Ensure dist/ directory exists
    dist_dir.mkdir(parents=True, exist_ok=True)

    if not starter_kits_dir.is_dir():
        print(f"Error: starter-kits directory not found at {starter_kits_dir}")
        return

    # Iterate over all subdirectories of starter-kits/
    for kit_dir in starter_kits_dir.iterdir():
        if kit_dir.is_dir():
            kit_name = kit_dir.name
            zip_path = dist_dir / f"starter-kit-python-{kit_name}.zip"
            print(
                f"Packaging starter kit '{kit_name}' to {zip_path.relative_to(repo_root)}..."
            )

            # Create/overwrite the zip archive
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                # Walk the files inside the starter kit directory
                for file_path in kit_dir.rglob("*"):
                    if file_path.is_file():
                        # Calculate the relative path for the zip archive
                        arcname = file_path.relative_to(kit_dir)
                        zipf.write(file_path, arcname)


if __name__ == "__main__":
    package_starter_kits()
