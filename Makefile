wasiless.wasm: target/wasm32-unknown-unknown/debug/wasiless.wasm
	wasm-tools component new target/wasm32-unknown-unknown/release/wasiless.wasm -o wasiless.wasm

target/wasm32-unknown-unknown/debug/wasiless.wasm: $(shell find src -name '*.rs')
	cargo build --release

# `wasm-tools component wit some_componentize_py_output.wasm --out-dir wit`
# handily extracts the wit for a new version of Python/componentize-py into this
# tree.