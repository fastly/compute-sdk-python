set -x

# generate wit directory
# wasm-tools component wit $1 --out-dir wit

#wit-bindgen rust --stubs wit --generate-all --world wasiless
#cp wasiless.rs src/lib.rs
cargo build --target=wasm32-unknown-unknown
cp target/wasm32-unknown-unknown/debug/wasiless.wasm .
wasm-tools component new wasiless.wasm -o wasiless.wasm
wac compose --dep fastly:wasiless=wasiless.wasm --dep app:component=$1 -o composed.wasm compose.wac

