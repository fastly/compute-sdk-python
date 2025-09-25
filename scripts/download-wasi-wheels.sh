#!/bin/bash

# Download WASI wheels from the wasi-wheels repository
# Usage: ./scripts/download-wasi-wheels.sh [package1] [package2] ...
# If no packages specified, downloads numpy and pandas by default

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Get the project root directory (parent of scripts/)
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

WASI_WHEELS_VERSION=${WASI_WHEELS_VERSION:-latest}
if [ "$WASI_WHEELS_VERSION" = "latest" ]; then
    WASI_WHEELS_BASE_URL="https://github.com/dicej/wasi-wheels/releases/latest/download"
else
    WASI_WHEELS_BASE_URL="https://github.com/dicej/wasi-wheels/releases/download/$WASI_WHEELS_VERSION"
fi
WASI_PACKAGES_DIR="$PROJECT_ROOT/wasi-packages"

# Default packages if none specified
DEFAULT_PACKAGES=("numpy" "pandas")

# Function to download and extract a WASI package
download_package() {
    local package_name=$1
    local tar_name="${package_name}-wasi.tar.gz"
    local download_url="${WASI_WHEELS_BASE_URL}/${tar_name}"

    echo "Downloading $package_name from $download_url"

    # Create temporary directory for this package
    local temp_dir=$(mktemp -d)

    # Download the package
    if curl -L -f -o "$temp_dir/$tar_name" "$download_url"; then
        echo "✅ Downloaded $package_name"

        # Extract to wasi-packages directory
        mkdir -p "$WASI_PACKAGES_DIR"

        # Extract the tar file in the temp directory
        tar -xzf "$temp_dir/$tar_name" -C "$temp_dir"

        # Find the extracted content and move it to wasi-packages
        local extracted_dir=$(find "$temp_dir" -maxdepth 1 -type d -name "*$package_name*" | head -1)
        if [ -n "$extracted_dir" ]; then
            rm -rf "$WASI_PACKAGES_DIR/$package_name"
            mv "$extracted_dir" "$WASI_PACKAGES_DIR/$package_name"
            echo "✅ Extracted $package_name to $WASI_PACKAGES_DIR/$package_name"
        else
            # Try extracting directly to wasi-packages
            tar -xzf "$temp_dir/$tar_name" -C "$WASI_PACKAGES_DIR/"
            echo "✅ Extracted $package_name to $WASI_PACKAGES_DIR/"
        fi
    else
        echo "❌ Failed to download $package_name from $download_url"
        echo "Available packages at $WASI_WHEELS_VERSION:"
        if [ "$WASI_WHEELS_VERSION" = "latest" ]; then
            curl -s "https://api.github.com/repos/dicej/wasi-wheels/releases/latest" | \
                jq -r '.assets[].name' | grep -E '\.(tar\.gz|whl)$' | sed 's/^/ - /'
        else
            curl -s "https://api.github.com/repos/dicej/wasi-wheels/releases/tags/$WASI_WHEELS_VERSION" | \
                jq -r '.assets[].name' | grep -E '\.(tar\.gz|whl)$' | sed 's/^/ - /'
        fi
        return 1
    fi

    # Clean up temp directory
    rm -rf "$temp_dir"
}

# Function to list available packages
list_available_packages() {
    echo "Available WASI packages:"
    if [ "$WASI_WHEELS_VERSION" = "latest" ]; then
        curl -s "https://api.github.com/repos/dicej/wasi-wheels/releases/latest" | \
            jq -r '.assets[].name' | grep -E '\.(tar\.gz|whl)$' | \
            sed 's/-wasi\.tar\.gz$//' | sed 's/^/ - /'
    else
        curl -s "https://api.github.com/repos/dicej/wasi-wheels/releases/tags/$WASI_WHEELS_VERSION" | \
            jq -r '.assets[].name' | grep -E '\.(tar\.gz|whl)$' | \
            sed 's/-wasi\.tar\.gz$//' | sed 's/^/ - /'
    fi
}

# Main script
main() {
    # Check if help requested
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        echo "Usage: $0 [package1] [package2] ..."
        echo "       $0 --list    # List available packages"
        echo ""
        echo "Downloads WASI wheels from github.com/dicej/wasi-wheels"
        echo "If no packages specified, downloads: ${DEFAULT_PACKAGES[*]}"
        echo ""
        echo "Environment variables:"
        echo "  WASI_WHEELS_VERSION   Version to download (default: $WASI_WHEELS_VERSION)"
        exit 0
    fi

    # Check if list requested
    if [[ "$1" == "--list" ]]; then
        list_available_packages
        exit 0
    fi

    # Determine which packages to download
    local packages=("$@")
    if [ ${#packages[@]} -eq 0 ]; then
        packages=("${DEFAULT_PACKAGES[@]}")
    fi

    echo "WASI Wheels Downloader"
    echo "Version: $WASI_WHEELS_VERSION"
    echo "Packages: ${packages[*]}"
    echo ""

    # Create wasi-packages directory
    mkdir -p "$WASI_PACKAGES_DIR"

    # Download each package
    local success_count=0
    local total_count=${#packages[@]}

    for package in "${packages[@]}"; do
        if download_package "$package"; then
            ((success_count++))
        fi
        echo ""
    done

    echo "📦 Downloaded $success_count/$total_count packages successfully"

    if [ $success_count -gt 0 ]; then
        echo ""
        echo "WASI packages installed in: $WASI_PACKAGES_DIR"
        echo "Contents:"
        ls -la "$WASI_PACKAGES_DIR"
    fi

    if [ $success_count -ne $total_count ]; then
        exit 1
    fi
}

# Run main function with all arguments
main "$@"