"""Entry point: generate fastly_compute/_bindings/*.py from WIT."""

from .generation import generate

if __name__ == "__main__":
    generate()
