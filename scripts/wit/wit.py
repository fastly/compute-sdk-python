"""WIT structural traversal: Function, Param, Interface, Package, Wit.

This module covers the parts of a WIT file that describe structure and
behaviour — functions, their parameters, and the interfaces and packages
that group them.  The type system (Type and all its subclasses) lives in
types.py. Base classes (DocsHaver, Thing) live in base.py.
"""

# ruff: noqa D102

import re
import textwrap
from collections.abc import Iterable
from typing import Any

from .base import DocsHaver, Thing
from .types import (
    CaseHaver,
    Handle,
    Option,
    Record,
    Resource,
    Result,
    TupleType,
    Type,
)
from .utils import lower_snake, only, upper_camel

METHOD_RE = re.compile(r"\[(static|method|constructor)\]([a-z0-9%-]+)\.([a-z0-9%-]+)")
CONSTRUCTOR_RE = re.compile(r"\[constructor\]([a-z0-9%-]+)")
FREESTANDING_FUNCTION_RE = re.compile(r"[a-z0-9%-]+")


class Function(Thing):
    """A function or resource method in a WIT"""

    def __init__(
        self,
        function_json: dict[str, Any],
        interface_json: dict[str, Any],
        wit_json: dict[str, list[dict]],
    ):
        super().__init__(function_json)
        self._interface = interface_json
        self._wit = wit_json

    def interface(self) -> "Interface":
        """Return the interface to which I belong."""
        return Interface(self._interface, self._wit)

    def interface_name(self) -> str:
        return self._interface["name"]

    def wit_path(self) -> str:
        """Return the dotted path to my definition in wit_world."""
        name = self._me["name"]
        if match := METHOD_RE.match(name):
            return (
                self.wit_module_path()
                + "."
                + upper_camel(match.group(2))
                + "."
                + lower_snake(match.group(3))
            )
        elif FREESTANDING_FUNCTION_RE.match(name):
            return self.wit_module_path() + "." + lower_snake(name)
        else:
            raise NotImplementedError(
                f'A new and exciting kind of function needs to be recognized. Its name field is "{name}".'
            )

    def kind(self) -> str:
        """Return 'static', 'method', 'constructor', or 'freestanding'."""
        name = self._me["name"]
        if match := METHOD_RE.match(name):
            return match.group(1)
        if CONSTRUCTOR_RE.match(name):
            return "constructor"
        return "freestanding"

    def resource_name(self) -> str | None:
        """Return the WIT kebab-case resource name this method belongs to, or None."""
        name = self._me["name"]
        if match := METHOD_RE.match(name):
            return match.group(2)
        if match := CONSTRUCTOR_RE.match(name):
            return match.group(1)
        return None

    def py_name(self) -> str:
        """Return the Python method/function name (snake_case).

        Constructors are named ``new`` since they take no arguments and
        return an owned instance of the resource.
        """
        name = self._me["name"]
        if match := METHOD_RE.match(name):
            return lower_snake(match.group(3))
        if CONSTRUCTOR_RE.match(name):
            return "new"
        return lower_snake(name)

    def params(self) -> list["Param"]:
        """Return parameters, excluding the implicit 'self' borrow handle."""
        result = []
        for p in self._me.get("params", []):
            if p["name"] == "self":
                continue
            result.append(Param(p, self._wit))
        return result

    def return_annotation(self, self_resource: "Resource | None" = None) -> str:
        """Return the Python return type annotation string.

        For result<T, E> the ok type T is returned; errors are handled by the decorator.
        """
        return Type.from_id(self._me.get("result"), self._wit).py_annotation(
            self_resource
        )

    def returns_resource_handle(self) -> bool:
        """Return True if the ok return type is an owned resource handle.

        Freestanding functions (and non-Self static methods) that return a
        resource handle need to wrap the raw WIT return value in the binding
        class, e.g. ``return ClassName(_wit.fn(...))``.
        """
        ret_id = self._me.get("result")
        if ret_id is None:
            return False
        t = Type.from_id(ret_id, self._wit)
        if isinstance(t, Result):
            ok_id = t._me["kind"]["result"].get("ok")
            if ok_id is None:
                return False
            t = Type.from_id(ok_id, self._wit)
        if isinstance(t, Option):
            t = Type.from_id(t._me["kind"]["option"], self._wit)
        return isinstance(t, Handle) and t.is_own()

    def return_wrap_expression(self, call_expr: str) -> str:
        """Return a Python expression that wraps ``call_expr`` for owned handles.

        Returns ``ClassName(call_expr)`` for owned handle returns, or
        ``call_expr`` unchanged for everything else. For tuple returns
        use ``tuple_return_parts()`` instead.

        :arg call_expr: The raw WIT call expression
        """
        ret_id = self._me.get("result")
        if ret_id is None:
            return call_expr
        t = Type.from_id(ret_id, self._wit)
        if isinstance(t, Result):
            ok_id = t._me["kind"]["result"].get("ok")
            if ok_id is None:
                return call_expr
            t = Type.from_id(ok_id, self._wit)
        if isinstance(t, Option):
            t = Type.from_id(t._me["kind"]["option"], self._wit)
        if isinstance(t, Handle) and t.is_own():
            cls_name = t._resource_type().py_annotation()
            return f"{cls_name}({call_expr})"
        return call_expr

    def _unwrap_to_tuple(self) -> "TupleType | None":
        """Chase result/option wrappers to a TupleType, or return None."""
        ret_id = self._me.get("result")
        if ret_id is None:
            return None
        t = Type.from_id(ret_id, self._wit)
        if isinstance(t, Result):
            ok_id = t._me["kind"]["result"].get("ok")
            if ok_id is None:
                return None
            t = Type.from_id(ok_id, self._wit)
        if isinstance(t, Option):
            t = Type.from_id(t._me["kind"]["option"], self._wit)
        if isinstance(t, TupleType):
            return t
        return None

    def tuple_is_optional(self) -> bool:
        """Return True if the tuple return is wrapped in option<...>."""
        ret_id = self._me.get("result")
        if ret_id is None:
            return False
        t = Type.from_id(ret_id, self._wit)
        if isinstance(t, Result):
            ok_id = t._me["kind"]["result"].get("ok")
            if ok_id is None:
                return False
            t = Type.from_id(ok_id, self._wit)
        return isinstance(t, Option)

    def returns_tuple_with_handles(self) -> bool:
        """Return True if the ok return type is a tuple containing owned handles."""
        tup = self._unwrap_to_tuple()
        if tup is None:
            return False
        for item_id in tup._me["kind"]["tuple"]["types"]:
            item_t = Type.from_id(item_id, self._wit)
            if isinstance(item_t, Handle) and item_t.is_own():
                return True
        return False

    def tuple_return_parts(self) -> list[str]:
        """For tuple-returning functions, return a list of wrap expressions per element.

        Each element is either ``'_r[i]'`` (no wrap) or ``'ClassName(_r[i])'`` (wrap).
        The caller assigns the raw WIT return to ``_r`` and returns a tuple of these.
        """
        tup = self._unwrap_to_tuple()
        assert tup is not None
        parts = []
        for i, item_id in enumerate(tup._me["kind"]["tuple"]["types"]):
            item_t = Type.from_id(item_id, self._wit)
            if isinstance(item_t, Handle) and item_t.is_own():
                cls_name = item_t._resource_type().py_annotation()
                parts.append(f"{cls_name}(_r[{i}])")
            else:
                parts.append(f"_r[{i}]")
        return parts

    def raises_errors(self) -> bool:
        """Return True if this function returns a result type."""
        return self.error_type_of_returned_result() is not None

    def error_type_of_returned_result(self) -> Type | None:
        """If this Function returns a result type, return the type of its error case."""
        return_type = Type.from_id(self._me.get("result"), self._wit)
        if isinstance(return_type, Result):
            return return_type.error_type()

    def raises_python(self) -> list[tuple[str, str, str]]:
        """Return a list of (short_name, qualified_name, description) for each Python
        exception this function can raise, derived from its WIT result error type.

        short_name: the bare class name, e.g. ``KvError``
        qualified_name: dotted import path, e.g. ``fastly_compute.exceptions.kv_store.kv_error.KvError``
        description: the type's docstring (may be empty)

        Emits the parent exception class for the error type rather than each
        individual case — the parent is the right type to catch, and the module
        it lives in documents the specific subclasses.
        """
        error_type = self.error_type_of_returned_result()
        if error_type is None:
            return []

        entries: list[tuple[str, str, str]] = []

        if isinstance(error_type, CaseHaver):
            short = upper_camel(error_type.name())
            qualified = error_type.py_module_path() + "." + short
            desc = error_type.docstring(indent=0) or ""
            entries.append((short, qualified, desc))
        elif isinstance(error_type, Record):
            short = error_type.wit_class_name()
            qualified = error_type.py_module_path() + "." + short
            desc = error_type.docstring(indent=0) or ""
            entries.append((short, qualified, desc))

        return entries

    def docstring_with_raises(
        self, indent: int = 4, fallback: str | None = None
    ) -> str:
        """Return a complete triple-quoted docstring, appending :raises lines.

        If the function has no WIT docs and no raises entries, returns the
        fallback string (defaulting to the function name followed by a period).
        """
        raises = self.raises_python()
        raw_docs = self.docs_for_python()
        pad = " " * indent

        if not raw_docs and not raises:
            return fallback or f'"""{self.py_name()}."""'

        body_parts: list[str] = []
        if raw_docs:
            # textwrap.indent adds `pad` to every non-blank line; lstrip()
            # removes the leading pad from the very first line so it sits
            # flush against the opening `"""`. rstrip() removes any trailing
            # newline so there is exactly one blank line before :raises.
            body_parts.append(textwrap.indent(raw_docs.rstrip(), pad).lstrip())
        elif raises:
            # No WIT docs but we have raises — use the function name as a
            # minimal summary so the :raises lines don't land flush against """.
            body_parts.append(f"{self.py_name()}.")
        if raises:
            if body_parts:
                body_parts.append("")  # blank line — no trailing whitespace
            for _short, qualified, _desc in raises:
                body_parts.append(f":raises ~{qualified}:")
        # Join lines with newline + pad so continuation lines are indented.
        # Blank lines must emit only a bare newline (no pad) to satisfy W293.
        out: list[str] = []
        for i, part in enumerate(body_parts):
            if i == 0:
                out.append(part)
            elif part == "":
                out.append("\n")
            else:
                out.append("\n" + pad + part)
        body = "".join(out)

        use_raw = "\\" in body
        prefix = 'r"""' if use_raw else '"""'
        if "\n" in body:
            return f'{prefix}{body}\n{pad}"""'
        return f'{prefix}{body}"""'


class Param:
    """A parameter of a WIT function."""

    def __init__(self, param_json: dict[str, Any], wit_json: dict[str, list[dict]]):
        self._me = param_json
        self._wit = wit_json

    def name(self) -> str:
        """Return the parameter name as a Python identifier (snake_case)."""
        return lower_snake(self._me["name"])

    def wit_name(self) -> str:
        """Return the raw WIT parameter name."""
        return self._me["name"]

    def type_(self) -> Type:
        """Return the resolved Type for this parameter."""
        return Type.from_id(self._me["type"], self._wit)

    def annotation(self, self_resource: "Resource | None" = None) -> str:
        """Return the Python type annotation string."""
        return self.type_().py_annotation(self_resource)

    def needs_unwrap(self) -> bool:
        """Return True if this param is a resource handle and must be unwrapped.

        When calling through to the underlying WIT binding, any parameter that
        is a generated FastlyResource wrapper must be unwrapped via
        ``._wit_resource`` before being passed to the raw WIT method.
        """
        return isinstance(self.type_(), Handle)

    def needs_record_unwrap(self) -> bool:
        """Return True if this param is a record wrapper and must be unwrapped.

        Record wrapper objects expose a ``._wit`` attribute containing the
        underlying WIT record that the raw WIT method expects.
        """
        return isinstance(self.type_(), Record)


class Interface(DocsHaver):
    """A WIT interface"""

    def __init__(self, interface_json: dict[str, Any], wit_json: dict[str, list[dict]]):
        self._me = interface_json
        self._wit = wit_json

    def name(self) -> str:
        return self._me["name"]

    def interface_name(self) -> str:
        return self._me["name"]

    def py_module(self) -> str:
        """Return the snake_case Python module name for this interface."""
        return lower_snake(self.name())

    def functions(self) -> Iterable[Function]:
        """Return all functions and methods defined in this interface."""
        for function in self._me["functions"].values():
            yield Function(function, self._me, self._wit)

    def resources(self) -> list[Resource]:
        """Return resource types defined directly in this interface (not imported aliases)."""
        result = []
        for type_id in self._me.get("types", {}).values():
            t = Type.from_id(type_id, self._wit)
            if not isinstance(t, Resource):
                continue
            # Only include resources whose canonical owner is this interface.
            owner = t._me.get("owner")
            if owner is None:
                continue
            owner_iface_index = owner.get("interface")
            # Find this interface's index in the global interfaces array.
            for i, iface in enumerate(self._wit["interfaces"]):
                if iface is self._me:
                    if i == owner_iface_index:
                        result.append(t)
                    break
        return result

    def methods_for_resource(self, resource: Resource) -> list[Function]:
        """Return constructors, static methods, and instance methods for a resource."""
        resource_wit_name = resource.name()
        return [
            f
            for f in self.functions()
            if f.resource_name() == resource_wit_name
            and f.kind() in ("constructor", "static", "method")
        ]

    def freestanding_functions(self) -> list[Function]:
        """Return functions that are not methods or constructors of any resource."""
        return [f for f in self.functions() if f.kind() == "freestanding"]


class Package:
    """A WIT package"""

    def __init__(self, package_json: dict, wit_json: dict[str, list[dict]]):
        self._package = package_json
        self._wit = wit_json

    def interfaces(self) -> Iterable[Interface]:
        """Return the interfaces defined in this package."""
        for interface_num in self._package["interfaces"].values():
            yield Interface(self._wit["interfaces"][interface_num], self._wit)


class Wit:
    """A WIT file

    This provides an abstraction layer atop the output of ``wasm-tools component
    wit --json``. It begins a tree of classes which work their way steadily
    narrower into the WIT: package, then interface, then function or type. They
    are instantiated lazily, for the most part, retaining unprocessed bits of
    JSON for later instantiation.
    """

    def __init__(self, wit_json: dict[str, list[dict]]):
        """Construct.

        :arg wit_json: The loaded JSON out of ``wasm-tools component wit wit/ --json``
        """
        self._packages: dict[str, Package] = {
            p["name"]: Package(p, wit_json) for p in wit_json["packages"]
        }

    def package(self, name: str) -> Package:
        """Return a package of the given name, e.g.
        "fastly:compute@0.0.0-prerelease.0", or raise KeyError.
        """
        return self._packages[name]

    def fastly_compute_package(self) -> Package:
        """Return the package representing the Fastly Compute API."""
        package_name = only(
            [p for p in self._packages.keys() if p.startswith("fastly:compute@")]
        )
        return self.package(package_name)
