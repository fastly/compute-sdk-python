"""Generate fastly_compute/_bindings/*.py from the Fastly Compute WIT."""

import json
from dataclasses import dataclass
from pathlib import Path
from subprocess import check_output

from jinja2 import Environment, FileSystemLoader

from scripts.generate_patches.utils import lower_snake, upper_camel
from scripts.generate_patches.wit import (
    Enum,
    Flags,
    Handle,
    Interface,
    Option,
    Record,
    Resource,
    Result,
    TupleType,
    Type,
    Variant,
    Wit,
)

WIT_DIR = "wit"
BINDINGS_DIR = Path("fastly_compute/_bindings")
TEMPLATES_DIR = Path(__file__).parent / "templates"


@dataclass
class ExtraImport:
    """A single import line to emit at the top of a generated module."""
    module: str   # e.g. "wit_world.imports.http_types"
    name: str     # e.g. "HttpVersion"


def _all_type_refs(interface: Interface) -> list[Type]:
    """Return every non-self type referenced in params or ok-return positions.

    Error types from result arms are excluded — those are handled by the
    exception hierarchy and MAPPINGS, not by generated imports.

    Record field types are included recursively so that any enum/variant/resource
    types that appear only as record fields still get their imports generated.
    """
    seen: set[int | str] = set()
    result: list[Type] = []

    def _collect(raw_type_id):
        if raw_type_id is None:
            return
        t = Type.from_id(raw_type_id, interface._wit)
        # Unwrap handle to the resource it points to
        if isinstance(t, Handle):
            t = t._resource_type()
        # Unwrap result: collect ok type only, skip error arm
        elif isinstance(t, Result):
            _collect(t._me["kind"]["result"].get("ok"))
            return
        elif isinstance(t, Option):
            _collect(t._me["kind"]["option"])
            return
        elif isinstance(t, TupleType):
            for sub_id in t._me["kind"]["tuple"]["types"]:
                _collect(sub_id)
            return
        if t._id in seen:
            return
        seen.add(t._id)
        result.append(t)
        # Recurse into record fields so field-level type deps get imports generated.
        if isinstance(t, Record):
            for field in t.fields():
                _collect(field._me["type"])

    for func in interface.functions():
        for raw_p in func._me.get("params", []):
            if raw_p["name"] == "self":
                continue
            _collect(raw_p["type"])
        _collect(func._me.get("result"))

    return result


def _extra_imports_for_interface(interface: Interface) -> list[ExtraImport]:
    """Compute import statements needed for types defined in other interfaces."""
    # Find this interface's own index so we can detect foreign types.
    own_index: int | None = None
    for i, iface_json in enumerate(interface._wit["interfaces"]):
        if iface_json is interface._me:
            own_index = i
            break

    imports: list[ExtraImport] = []
    seen_names: set[str] = set()

    for t in _all_type_refs(interface):
        owner = t._me.get("owner")
        if owner is None:
            continue
        owner_idx = owner.get("interface")
        if owner_idx is None or owner_idx == own_index:
            continue
        owner_iface = interface._wit["interfaces"][owner_idx]
        owner_module = lower_snake(owner_iface["name"])
        type_name = upper_camel(t._me["name"])
        if type_name in seen_names:
            continue
        seen_names.add(type_name)

        if isinstance(t, Resource):
            imports.append(ExtraImport(
                module=f"fastly_compute._bindings.{owner_module}",
                name=type_name,
            ))
        elif isinstance(t, Enum | Variant | Flags):
            imports.append(ExtraImport(
                module=f"wit_world.imports.{owner_module}",
                name=type_name,
            ))

    return sorted(imports, key=lambda i: (i.module, i.name))


def _reexports_for_interface(interface: Interface) -> list[str]:
    """Names to re-export verbatim from wit_world for this interface.

    Covers enum/flags/variant types owned by this interface that appear in
    any param or return position (not just params).  Error types that appear
    only as result error arms are excluded.
    """
    # Find this interface's own index.
    own_index: int | None = None
    for i, iface_json in enumerate(interface._wit["interfaces"]):
        if iface_json is interface._me:
            own_index = i
            break

    # Collect all type IDs visible from params and return types
    # (via _all_type_refs which already unwraps handles/results/options/tuples).
    referenced_ids: set[int | str] = {t._id for t in _all_type_refs(interface)}

    names = []
    for type_name, type_id in interface._me.get("types", {}).items():
        t = Type.from_id(type_id, interface._wit)
        if t._id not in referenced_ids:
            continue
        owner = t._me.get("owner")
        if owner is None:
            continue
        if owner.get("interface") != own_index:
            continue
        if isinstance(t, Enum | Flags | Variant):
            names.append(upper_camel(type_name))
    return sorted(names)


def _records_for_interface(interface: Interface) -> list[Record]:
    """Return own-interface Record types used in function signatures.

    These need generated Python wrapper classes with documented __init__
    signatures so callers don't have to construct raw WIT dataclasses.
    """
    own_index: int | None = None
    for i, iface_json in enumerate(interface._wit["interfaces"]):
        if iface_json is interface._me:
            own_index = i
            break

    referenced_ids: set[int | str] = {t._id for t in _all_type_refs(interface)}

    records = []
    seen_ids: set[int | str] = set()
    for type_id in interface._me.get("types", {}).values():
        t = Type.from_id(type_id, interface._wit)
        if not isinstance(t, Record):
            continue
        if t._id in seen_ids:
            continue
        if t._id not in referenced_ids:
            continue
        owner = t._me.get("owner", {})
        if owner.get("interface") != own_index:
            continue
        seen_ids.add(t._id)
        records.append(t)
    return records


def generate_binding_module(interface: Interface, env: Environment) -> str:
    """Render the binding module for a single WIT interface."""
    resources_and_methods = [
        (r, interface.methods_for_resource(r)) for r in interface.resources()
    ]
    freestanding = interface.freestanding_functions()
    records = _records_for_interface(interface)
    module_docstring = interface.docstring(indent=0) or ""
    reexports = _reexports_for_interface(interface)
    extra_imports = _extra_imports_for_interface(interface)

    needs_resource = bool(resources_and_methods)
    needs_decorator = (
        any(f.raises_errors() for _, methods in resources_and_methods for f in methods)
        or any(f.raises_errors() for f in freestanding)
    )
    needs_self = (
        any(
            f.return_annotation(r) == "Self"
            for r, methods in resources_and_methods
            for f in methods
            if f.kind() == "static"
        )
        or any(
            f.kind() == "constructor"
            for _, methods in resources_and_methods
            for f in methods
        )
    )

    template = env.get_template("bindings_module.py.jinja")
    return template.render(
        interface=interface,
        module_docstring=module_docstring,
        resources_and_methods=resources_and_methods,
        freestanding=freestanding,
        records=records,
        reexports=reexports,
        extra_imports=extra_imports,
        needs_resource=needs_resource,
        needs_decorator=needs_decorator,
        needs_self=needs_self,
    )


def generate() -> None:
    """Generate all _bindings modules for the Fastly Compute package."""
    wit_text = check_output(["wasm-tools", "component", "wit", WIT_DIR, "--json"])
    wit_json = json.loads(wit_text)
    wit = Wit(wit_json)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    BINDINGS_DIR.mkdir(parents=True, exist_ok=True)

    (BINDINGS_DIR / "__init__.py").write_text(
        "# This package is automatically generated by scripts/generate_bindings.\n"
        "# Do not edit directly.\n"
    )

    pkg = wit.fastly_compute_package()
    for interface in pkg.interfaces():
        module_name = interface.py_module()
        dest = BINDINGS_DIR / f"{module_name}.py"
        code = generate_binding_module(interface, env)
        dest.write_text(code)
        print(f"  wrote {dest}")

    # Sort imports in all generated files so ruff is happy with the output.
    check_output(["uv", "run", "--extra", "dev", "ruff", "check", "--fix", "--exit-zero", "--select", "I", str(BINDINGS_DIR)])
