"""Thin wrapper for calling the rust fastly-compute-py builder"""

import sys

from fastly_compute._fastly_compute_py import run_main_py


def main():
    """Run the fastly-compute-py CLI"""
    run_main_py(sys.argv)


if __name__ == "__main__":
    main()
