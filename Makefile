all: app.wasm

app.wasm: hello.wit app.py
	componentize-py -d hello.wit -w hello bindings hello_guest
	componentize-py -d hello.wit -w hello componentize --stub-wasi app -o app.wasm

.PHONY: all