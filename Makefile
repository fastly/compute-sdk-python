all: app.wasm

app.wasm: wit/viceroy.wit wit/deps/fastly/compute.wit app.py
	rm -rf hello_compute
	componentize-py -d wit -w compute bindings hello_compute
	componentize-py -d wit -w compute componentize --stub-wasi app -o app.wasm

serve: app.wasm
	viceroy --adapt app.wasm

.PHONY: all serve