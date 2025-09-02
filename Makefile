all: app.wasm

STUBS_DIR := stubs

app.wasm: wit/viceroy.wit wit/deps/fastly/compute.wit app.py
	rm -rf ${STUBS_DIR}
	uv run componentize-py -d wit -w viceroy bindings ${STUBS_DIR}
	uv run componentize-py -d wit -w viceroy componentize app -o app.wasm

serve: app.wasm
	viceroy serve app.wasm

test:
	uv run --extra test pytest -m integration

lint:
	uv run --extra dev ruff check .

format:
	uv run --extra dev ruff format .

format-check:
	uv run --extra dev ruff format --check .

.PHONY: all serve test lint format format-check
