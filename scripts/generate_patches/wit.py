"""Abstraction over a WIT file

Provides affordances for walking among WIT constructs and translating drawing
correspondences between them, componentize-py-generated Python code, and
Fastly's own slightly higher level generated code.
"""
# We override many methods and don't want to clutter the module repeating
# identical docstrings or tagging each with @override.
# ruff: noqa D102

import re
from collections.abc import Iterable
import textwrap
from types import NoneType
from typing import Any, Self

from .utils import lower_snake, only, shouty_snake, upper_camel

# ---------------------------------------------------------------------------
# WIT primitive type -> Python annotation string
# ---------------------------------------------------------------------------

_PRIMITIVES: dict[str, str] = {
    "string": "str",
    "bool": "bool",
    "u8": "int",
    "u16": "int",
    "u32": "int",
    "u64": "int",
    "s8": "int",
    "s16": "int",
    "s32": "int",
    "s64": "int",
    "f32": "float",
    "f64": "float",
    "char": "str",
    "bytes": "bytes",
}


class DocsHaver:
    """A WIT item which has documentation

    Abstract.
    """

    def __init__(self, me: Any):
        """Construct.

        :arg me: The JSON representing the WIT-file entity I am
        """
        self._me: dict[str, Any] = me

    def docs(self) -> str:
        """Return the documentation of the type, "" if omitted.

        Strip leading and trailing whitespace.
        """
        return self._me.get("docs", {}).get("contents", "").strip()

    def docstring(self, indent=4) -> str:
        """Return a one-level-indented, triple-quoted version of the docs
        suitable for use as a docstring in a top-level construct.
        """
        docs = self.docs()
        if docs:
            if docs.count("\n") > 0:  # multi-line
                docs += "\n"
            docs += '"""'

            # Use a raw string if the doc contains backslashes so that ruff
            # doesn't flag it with D301.
            prefix = 'r"""' if "\\" in docs else '"""'
            return prefix + textwrap.indent(docs, " " * indent).lstrip()
        return ""


class Thing(DocsHaver):
    """Any kind of thing represented in WIT: type, function, etc.

    Abstract.
    """

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.name()}>"

    def name(self) -> str:
        """Return the name of this type, in usual WIT kebab case."""
        return self._me["name"]

    def wit_module_path(self) -> str:
        """Return the full dotted path to the Python module in which I am defined."""
        return "wit_world.imports." + lower_snake(self.interface().name())

    def wit_path(self):
        """Return the dotted path to my definition in wit_world.

        This is used as the key fed to ``remap_wit_errors()`` for a type,
        among other things.
        """
        return self.wit_module_path() + "." + upper_camel(self.name())

    def py_exception_name(self) -> str:
        """Return my name, fashioned as a suitable name for an exception."""
        return upper_camel(self.name())

    def interface(self) -> "Interface":
        """Return the interface where this type is defined."""
        raise NotImplementedError


class Type(Thing):
    """A WIT type: primitive, stock, or user-defined.

    In practice, many types, like variants and the unit type, are represented by
    more-specific subclasses, leaving this one to stand in for ones we haven't
    needed to specialize for yet.
    """

    @classmethod
    def from_id(
        cls, type_id: int | str | None, wit_json: dict[str, list[dict]]
    ) -> "Type":
        """Construct a type of the given index under the WIT's "types" key.

        If that type is an alias (which is the case when referencing a type from
        a different interface), chase it down to its ultimate resolution.
        Construct an Enum, Variant, or other more specific class if there is one.

        :arg type_id: The (non-negative) array index of the type in the WIT's type array
        :arg wit_json: The entire JSON-decided WIT file
        """
        while True:
            if isinstance(type_id, str):
                # It's a primitive — always a base Type regardless of calling class.
                return Type(type_id, {"name": type_id}, wit_json)
            elif isinstance(type_id, NoneType):
                return NullType(wit_json)

            # It's an int. Chase that down, including following type aliases.
            current_type = wit_json["types"][type_id]
            kind_val = current_type["kind"]
            # Resources have kind = "resource" (a bare string, not a dict).
            if isinstance(kind_val, str):
                class_ = KINDS_TO_CLASSES.get(kind_val, Type)
                return class_(type_id, current_type, wit_json)
            next_type = kind_val.get("type")
            if next_type is None:
                kind = only(kind_val.keys())
                class_ = KINDS_TO_CLASSES.get(kind, Type)
                return class_(type_id, current_type, wit_json)
            else:
                # It's a pointer to a different type.
                type_id = next_type

    def __init__(self, id: int | str, type_: dict, wit_json: dict[str, list[dict]]):
        """Private constructor. Use from_id() instead."""
        super().__init__(type_)
        self._id: int | str = id
        self._wit = wit_json

    def __hash__(self):
        """Let us put Types into dicts and constrain them unique.

        Type instances compare and hash based on their IDs: their positions in
        the WIT's type array. Only non-alias type IDs occur in instances.
        """
        return hash(self._id)

    def __eq__(self, other):
        return self._id == other._id

    def __ne__(self, other):
        return not (self == other)

    def has_cases(self) -> bool:
        return False

    def cases(self) -> Iterable["Case"]:
        """Return the cases of an type if it has them, else an empty iterable."""
        return []

    def interface(self) -> "Interface":
        return Interface(
            self._wit["interfaces"][self._me["owner"]["interface"]], self._wit
        )

    def py_package(self) -> str:
        """Return the innermost, undotted package in which this type resides."""
        return lower_snake(self.interface().name())

    def py_module(self) -> str:
        """Return the name of the file (minus ".py") in which the exception
        corresponding to this type resides.
        """
        raise NotImplementedError(
            "Only variants, enums, and records are currently handled as "
            "``result`` error types. Looks like it's time to support others!"
        )

    def py_module_path(self) -> str:
        """Return the dotted import path of the module holding the exception
        corresponding to this type.
        """
        raise NotImplementedError(
            "Only variants, enums, and records are currently handled as "
            "``result`` error types. Looks like it's time to support others!"
        )

    def py_annotation(self, self_resource: "Resource | None" = None) -> str:
        """Return the Python type annotation string for this type.

        :arg self_resource: When resolving a handle to a resource that is the
            same resource as the method being generated, use ``Self`` instead of
            the class name.  Pass the owning resource to enable this.
        """
        # Primitive types (id is a string like "string", "u32", etc.)
        if isinstance(self._id, str):
            return _PRIMITIVES.get(self._id, self._id)
        # Named types with no special handling fall back to their upper-camel name
        name = self._me.get("name")
        if name:
            return upper_camel(name)
        return "Any"


class Result(Type):
    """A WIT ``result``"""

    def error_type(self) -> Type:
        """Return the type of my error case."""
        return self.from_id(self._me["kind"]["result"]["err"], self._wit)

    def ok_type(self) -> "Type":
        """Return the type of the ok case, or NullType if unit."""
        return self.from_id(self._me["kind"]["result"].get("ok"), self._wit)

    def py_annotation(self, self_resource=None) -> str:
        return self.ok_type().py_annotation(self_resource)


class NullType(Type):
    def __init__(self, wit_json):
        super().__init__("null", {"name": "null"}, wit_json)

    def py_annotation(self, self_resource=None) -> str:
        return "None"


class Resource(Type):
    """A WIT ``resource`` type."""

    def py_annotation(self, self_resource=None) -> str:
        return upper_camel(self._me["name"])

    def bindings_class_name(self) -> str:
        """The Python class name for this resource in the generated bindings."""
        return upper_camel(self._me["name"])

    def bindings_module_path(self) -> str:
        """The dotted import path of the generated bindings module for this resource's interface."""
        return "fastly_compute._bindings." + lower_snake(self.interface().name())


class Handle(Type):
    """A WIT ``handle`` (own<T> or borrow<T>)."""

    def _resource_type(self) -> Resource:
        """Resolve the resource this handle points to."""
        handle_kind = self._me["kind"]["handle"]
        resource_id = handle_kind.get("own") or handle_kind.get("borrow")
        t = Type.from_id(resource_id, self._wit)
        assert isinstance(t, Resource), f"Handle points to non-resource type: {t}"
        return t

    def is_own(self) -> bool:
        return "own" in self._me["kind"]["handle"]

    def py_annotation(self, self_resource=None) -> str:
        resource = self._resource_type()
        if self_resource is not None and resource == self_resource:
            return "Self"
        return resource.py_annotation()


class Option(Type):
    """A WIT ``option<T>``."""

    def inner_type(self) -> Type:
        return Type.from_id(self._me["kind"]["option"], self._wit)

    def py_annotation(self, self_resource=None) -> str:
        inner = self.inner_type().py_annotation(self_resource)
        return f"{inner} | None"


class ListType(Type):
    """A WIT ``list<T>``."""

    def inner_type(self) -> Type:
        return Type.from_id(self._me["kind"]["list"], self._wit)

    def py_annotation(self, self_resource=None) -> str:
        inner = self.inner_type().py_annotation(self_resource)
        return f"list[{inner}]"


class TupleType(Type):
    """A WIT ``tuple<A, B, ...>``."""

    def py_annotation(self, self_resource=None) -> str:
        items = self._me["kind"]["tuple"]["types"]
        parts = [Type.from_id(t, self._wit).py_annotation(self_resource) for t in items]
        return f"tuple[{', '.join(parts)}]"


class Flags(Type):
    """A WIT ``flags`` type -- re-exported from wit_world."""

    def py_annotation(self, self_resource=None) -> str:
        return upper_camel(self._me["name"])


class Record(Type):
    """A WIT ``record`` type"""

    def py_module(self) -> str:
        return "__init__"

    def py_module_path(self) -> str:
        return f"fastly_compute.exceptions.{self.py_package()}"

    def py_annotation(self, self_resource=None) -> str:
        return upper_camel(self._me["name"])

    def fields(self) -> list["RecordField"]:
        """Return the fields of this record."""
        return [
            RecordField(f, self._wit)
            for f in self._me["kind"]["record"]["fields"]
        ]

    def wit_class_name(self) -> str:
        """The componentize-py class name for this record (e.g. InsertOptions)."""
        return upper_camel(self._me["name"])


class RecordField:
    """A field of a WIT record."""

    def __init__(self, field_json: dict, wit_json: dict):
        self._me = field_json
        self._wit = wit_json

    def name(self) -> str:
        """Python snake_case field name, avoiding reserved keywords."""
        n = lower_snake(self._me["name"])
        # Append underscore to avoid clashing with Python reserved words
        if n in ("from", "import", "class", "def", "return", "pass", "in",
                 "is", "not", "and", "or", "if", "else", "for", "while",
                 "with", "as", "try", "except", "finally", "raise", "del",
                 "global", "nonlocal", "lambda", "yield", "assert", "break",
                 "continue", "type"):
            return n + "_"
        return n

    def wit_name(self) -> str:
        """Raw WIT kebab-case field name."""
        return self._me["name"]

    def type_(self) -> "Type":
        return Type.from_id(self._me["type"], self._wit)

    def is_optional(self) -> bool:
        return isinstance(self.type_(), Option)

    def is_extra(self) -> bool:
        """True if this is an extensibility handle field (should be hidden)."""
        return self._me["name"].startswith("extra")

    def annotation(self) -> str:
        return self.type_().py_annotation()

    def needs_unwrap(self) -> bool:
        """True if this field holds a resource handle (unwrap via ._wit_resource)."""
        t = self.type_()
        if isinstance(t, Option):
            return isinstance(t.inner_type(), Handle)
        return isinstance(t, Handle)

    def needs_record_unwrap(self) -> bool:
        """True if this field holds a record wrapper (unwrap via ._wit)."""
        t = self.type_()
        if isinstance(t, Option):
            return isinstance(t.inner_type(), Record)
        return isinstance(t, Record)

    def default(self) -> str:
        """Python literal for a sensible default value for this field."""
        t = self.type_()
        if isinstance(t, Option):
            return "None"
        if isinstance(t, NullType):
            return "None"
        # Primitive defaults
        ann = t.py_annotation()
        if ann == "bool":
            return "False"
        if ann == "int":
            return "0"
        if ann == "float":
            return "0.0"
        if ann == "str":
            return '""'
        # Enum: use the first case
        if isinstance(t, (Enum, Variant)):
            cases = list(t.cases())
            if cases:
                return f"{upper_camel(t.name())}.{shouty_snake(cases[0].name())}"
        return "None"


class CaseHaver(Type):
    """Abstract WIT type that has cases"""

    _case_class: type

    def has_cases(self) -> bool:
        return True

    def cases(self):
        return (
            self._case_class(c, self) for c in self._me["kind"][self._case_key]["cases"]
        )

    def py_module(self) -> str:
        return lower_snake(self.name())

    def py_module_path(self) -> str:
        return f"fastly_compute.exceptions.{self.py_package()}.{self.py_module()}"

    def py_annotation(self, self_resource=None) -> str:
        return upper_camel(self._me["name"])


class Case(Thing):
    """Abstract arm of a WIT type that has alternative manifestations."""

    def __init__(self, case_json: dict[str, Any], haver: CaseHaver):
        super().__init__(case_json)
        self._haver = haver


class EnumCase(Case):
    """An arm of a WIT ``enum``"""

    def wit_path(self) -> str:
        return self._haver.wit_path() + "." + shouty_snake(self.name())


class VariantCase(Case):
    """An arm of a WIT ``variant``"""

    def wit_path(self) -> str:
        return (
            self._haver.wit_module_path()
            + "."
            + upper_camel(self._haver.name())
            + "_"
            + upper_camel(self.name())
        )


class Enum(CaseHaver):
    _case_key = "enum"
    _case_class = EnumCase


class Variant(CaseHaver):
    _case_key = "variant"
    _case_class = VariantCase


KINDS_TO_CLASSES = {
    "enum": Enum,
    "variant": Variant,
    "record": Record,
    "result": Result,
    "resource": Resource,
    "handle": Handle,
    "option": Option,
    "list": ListType,
    "tuple": TupleType,
    "flags": Flags,
}


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
        return Type.from_id(self._me.get("result"), self._wit).py_annotation(self_resource)

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
        my_index = self._me.get("_index")
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
            f for f in self.functions()
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
