"""Generates fastly_compute/_bindings/*.py from the Fastly Compute WIT.

Each generated module wraps the corresponding wit_world.imports.* module,
applying remap_wit_errors at definition time so there is no runtime
monkeypatching required.

This runs at SDK build time; customers don't run it.
"""
