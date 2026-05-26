"""WIT type system classes.

Covers the full hierarchy of types that appear in a WIT file: primitives,
resources, handles, options, lists, tuples, flags, records, enums, variants,
and the case types that populate them.

Maps directly onto entries in the ``types`` array of the WIT JSON produced by
``wasm-tools component wit --json``.
"""

# ruff: noqa D102

import re
from collections.abc import Iterable
from types import NoneType
from typing import Any, Self

from .base import DocsHaver, Thing
from .utils import lower_snake, only, shouty_snake, upper_camel


# WIT primitive type -> Python annotation string
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

    def interface_name(self) -> str:
        """Return the name of the interface that owns this type."""
        iface_index = self._me["owner"]["interface"]
        return self._wit["interfaces"][iface_index]["name"]

    def interface_docstring(self, indent: int = 0) -> str:
        """Return the docstring of the interface that owns this type."""
        iface_index = self._me["owner"]["interface"]
        iface_json = self._wit["interfaces"][iface_index]
        contents = iface_json.get("docs", {}).get("contents", "").strip()
        if not contents:
            return ""
        # Reuse DocsHaver.docstring() logic inline — we don't have a DocsHaver
        # for the interface here, just its raw JSON.
        import textwrap

        if contents.count("\n") > 0:
            contents += "\n"
        contents += '"""'
        prefix = 'r"""' if "\\" in contents else '"""'
        return prefix + textwrap.indent(contents, " " * indent).lstrip()

    def has_cases(self) -> bool:
        return False

    def cases(self) -> Iterable["Case"]:
        """Return the cases of an type if it has them, else an empty iterable."""
        return []

    def py_package(self) -> str:
        """Return the innermost, undotted package in which this type resides."""
        return lower_snake(self.interface_name())

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

    def interface_name(self) -> str:
        return ""

    def interface_docstring(self, indent: int = 0) -> str:
        return ""

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
        return "fastly_compute._bindings." + lower_snake(self.interface_name())


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
        # list<u8> is the WIT encoding of a byte buffer; map it to bytes
        # rather than list[int] since that is what callers actually pass.
        if self._me["kind"]["list"] == "u8":
            return "bytes"
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
        return [RecordField(f, self._wit) for f in self._me["kind"]["record"]["fields"]]

    def wit_class_name(self) -> str:
        """The componentize-py class name for this record (e.g. InsertOptions)."""
        return upper_camel(self._me["name"])


class RecordField(DocsHaver):
    """A field of a WIT record."""

    def __init__(self, field_json: dict, wit_json: dict):
        super().__init__(field_json)
        self._wit = wit_json

    def name(self) -> str:
        """Python snake_case field name, avoiding reserved keywords."""
        n = lower_snake(self._me["name"])
        # Append underscore to avoid clashing with Python reserved words
        if n in (
            "from",
            "import",
            "class",
            "def",
            "return",
            "pass",
            "in",
            "is",
            "not",
            "and",
            "or",
            "if",
            "else",
            "for",
            "while",
            "with",
            "as",
            "try",
            "except",
            "finally",
            "raise",
            "del",
            "global",
            "nonlocal",
            "lambda",
            "yield",
            "assert",
            "break",
            "continue",
            "type",
        ):
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

    def param_doc(self) -> str:
        """Return docs_for_python() normalized for use as a single-line :param entry.

        Collapses newlines and runs of whitespace to a single space so that the
        full field description fits on one line without breaking Sphinx parsing.
        """
        text = self.docs_for_python()
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

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

    def interface_name(self) -> str:
        return self._haver.interface_name()


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
