#!/usr/bin/env bash
# Install the nightly Rust toolchain required to build this project.
#
# componentize-py's build.rs uses -Z build-std (nightly-only) to compile its
# wasm32-wasip1 runtime. It also invokes `rustup run nightly cargo build` by
# name, so both the pinned dated nightly and the bare 'nightly' channel must
# be installed; rustup rejects 'nightly' as a toolchain link target.
#
# Both installs are skipped if already present (e.g. restored from cache).
#
# Usage: setup-nightly.sh <nightly-date>
#   e.g. setup-nightly.sh nightly-2026-04-27

set -euo pipefail

RUST_NIGHTLY="${1:?Usage: $0 <nightly-date>}"

if ! rustup toolchain list | grep -q "^${RUST_NIGHTLY}"; then
  rustup toolchain install "$RUST_NIGHTLY" --component rust-src
  rustup target add wasm32-wasip1 --toolchain "$RUST_NIGHTLY"
else
  echo "Nightly toolchain $RUST_NIGHTLY already installed (cache hit)"
fi

if ! rustup run nightly rustc --version &>/dev/null; then
  rustup toolchain install nightly --component rust-src
  rustup target add wasm32-wasip1 --toolchain nightly
else
  echo "Bare nightly toolchain already installed (cache hit)"
fi
