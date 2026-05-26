"""Entry point: generate fastly_compute/exceptions/ from WIT."""

from .generation import generate

if __name__ == "__main__":
    generate()
