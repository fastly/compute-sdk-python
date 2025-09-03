"""Pytest plugin for automatic viceroy output on test failures."""

import sys

import pytest


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook to display viceroy output on test failure.

    This hook automatically displays recent viceroy server output
    when any test fails, making debugging easier.
    """
    outcome = yield
    rep = outcome.get_result()

    # Only show output on test failures during the call phase
    if rep.when == "call" and rep.failed:
        # Try to get the viceroy_server fixture from the test
        if hasattr(item, "funcargs") and "viceroy_server" in item.funcargs:
            server = item.funcargs["viceroy_server"]
            if hasattr(server, "output_lines"):
                print(
                    f"\n=== Viceroy output for failed test: {item.name} ===",
                    file=sys.stderr,
                )
                # Show last 15 lines of output
                for line in server.output_lines[-15:]:
                    print(f"  {line}", file=sys.stderr)
                print("=== End viceroy output ===", file=sys.stderr)
