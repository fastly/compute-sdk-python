"""Generate fastly_compute/exceptions/ from WIT result error types.

Handles high-level logic and writing to the filesystem.
"""

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from functools import partial
from pathlib import Path
from subprocess import check_output
from typing import Any

from jinja2 import Environment, PackageLoader, Template, TemplateNotFound

from scripts.wit import NullType, Type, Wit

WIT_DIR = "wit"
FASTLY_COMPUTE = Path(__file__).parent.parent.parent / "fastly_compute"


jinja_env = Environment(
    loader=PackageLoader("scripts.generate_exceptions"),
    autoescape=False,
    keep_trailing_newline=True,
)


def generate_exceptions(error_types: Iterable[Type]):
    """Generate Python exception classes we can map error types to.

    Inherit names and docstrings from the WIT. Create a common superclass for
    each type so you can catch the whole smear if you like.

    :arg error_types: An iterable of unique types used as error arms of
        ``result``s

    :return: A dict of package names pointing to module names pointing to
        contained code. For example, acl (from the interface name) -> acl_error.py
        (from the enum name) -> class AclError(FastlyError)...
    """
    # package -> module -> code:
    exceptions = defaultdict(lambda: defaultdict(dict[str, str]))
    # package -> module -> docstring:
    module_docstrings = defaultdict(dict)
    # package -> docstring:
    package_docstrings = {}

    for error_type in error_types:
        package = error_type.py_package()
        module = error_type.py_module() + ".py"

        try:
            module_docstrings[package][module]
        except KeyError:
            module_docstrings[package][module] = error_type.docstring(indent=0)

        # Create package's __init__.py if not already there:
        if package not in package_docstrings:
            package_docstrings[package] = error_type.interface().docstring(indent=0)

        # Common superclass for exceptions based on the enum or variant's
        # members. Or the raised exception itself for records.
        top_level_exception_name = error_type.py_exception_name()
        exceptions[package][module][top_level_exception_name] = (
            f"""class {top_level_exception_name}(FastlyError):\n"""
            f"""    {error_type.docstring(indent=4) or "pass"}"""
        )
        # Insert enum or variant cases.
        for case in error_type.cases():
            case_exception_name = case.py_exception_name()
            exceptions[package][module][case_exception_name] = (
                f"""class {case_exception_name}({top_level_exception_name}):\n"""
                f"""    {case.docstring(indent=4) or "pass"}"""
            )

    for package, docstring in package_docstrings.items():
        write_templated_file(
            FASTLY_COMPUTE / "exceptions" / package / "__init__.py",
            {"module_docstring": docstring},
            jinja_env.get_template("exception_init_module.py.jinja"),
        )
    for package, modules in exceptions.items():
        for module, exceptions_by_name in modules.items():
            write_templated_file(
                FASTLY_COMPUTE / "exceptions" / package / module,
                {
                    "generated_exceptions": partial(
                        join_named_chunks, exceptions_by_name, "\n\n\n"
                    ),
                    "module_docstring": module_docstrings[package][module],
                },
                jinja_env.get_template("default_exception.py.jinja"),
            )


def join_named_chunks(
    chunks: dict[str, str], sep: str, omit: list[str] | None = None
) -> str:
    """Return an ordered concatenation of all items in a dict except those of
    the given keys.
    """
    if omit is None:
        omit = []
    return sep.join(
        chunk for name, chunk in chunks.items() if name not in omit
    )  # O(n^2) but small


def write_templated_file(
    dest_file: Path, template_vars: Mapping[str, Any], default_template: Template
):
    """Render templates to generate code on disk, providing hook points for
    replacing generated pieces with manual improvements.

    We examine the ``templates`` folder for a file at the same relative path as
    ``dest_file`` is from ``fastly_compute``. We use it if found. Otherwise, we
    call back to ``default_template``.

    :arg dest_file: Path to the file to write, relative to ``fastly_compute``
    :arg template_vars: Data to populate the template
    :arg default_template: Template to fall back to if a parallel one to does
        not exist in the templates folder

    """
    subpath = dest_file.relative_to(FASTLY_COMPUTE)
    try:
        # Render a parallel template if it's there:
        template = jinja_env.get_template(str(subpath) + ".jinja")
    except TemplateNotFound:
        template = default_template
    rendered = template.render(template_vars)
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    dest_file.write_text(rendered)


def generate():
    """Generate idiomatic exception classes from WIT result error types.

    Currently handles ``result`` error types that are variants, enums, records,
    or the unit type.  Primitives and options are not yet supported but would be
    straightforward to add.
    """
    wit_text = check_output(["wasm-tools", "component", "wit", WIT_DIR, "--json"])
    wit_json = json.loads(wit_text)
    wit = Wit(wit_json)

    # Hunt through our whole fastly-compute package to find the result error
    # types we return. Each inspires the generation of one exception class (in
    # the case of records) or more (in the case of variants or enums).
    # A dict preserves order, for comprehensibility and determinism.
    exceptions_to_generate: dict[Type, bool] = {}

    for interface in wit.fastly_compute_package().interfaces():
        for function in interface.functions():
            if error_type := function.error_type_of_returned_result():
                if not isinstance(error_type, NullType):
                    # Null errors (result<whatever, _>) are handled by a static
                    # entry mapping them to FastlyError.

                    # We don't need to go any deeper than the top-level type of
                    # the result's error arm. That represents the whole universe
                    # of Err values the componentize-py-generated code may raise,
                    # and those values are what we promote to exceptions.
                    exceptions_to_generate[error_type] = True

    generate_exceptions(exceptions_to_generate.keys())
