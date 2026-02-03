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
from types import NoneType
from typing import Any, Self

from .utils import indent, lower_snake, only, shouty_snake, upper_camel


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
        """Return the documentation of the type, "" if omitted."""
        return self._me.get("docs", {}).get("contents", "")

    def docstring_or_pass(self) -> str:
        """Return a one-level-indented version of the docs suitable for use as a
        docstring in an otherwise empty construct.

        Accordingly, emit "pass" if there is no docstring.
        """
        return indent(self.docs()) or "pass"


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
    ) -> Self:
        """Construct a type of the given index under the WIT's "types" key.

        If that type is an alias (which is the case when referencing a type from
        a different interface), chase it down to its ultimate resolution.
        Construct an Enum, Variant, or other more specific class if there is one.

        :arg type_id: The (non-negative) array index of the type in the WIT's type array
        :arg wit_json: The entire JSON-decided WIT file
        """
        while True:
            if isinstance(type_id, str):
                # It's a primitive.
                return cls(type_id, {"name": type_id}, wit_json)
            elif isinstance(type_id, NoneType):
                return NullType(wit_json)

            # It's an int. Chase that down, including following type aliases.
            current_type = wit_json["types"][type_id]
            next_type = current_type["kind"].get("type")
            if next_type is None:
                kind = only(current_type["kind"].keys())
                class_ = KINDS_TO_CLASSES.get(kind, cls)
                return class_(type_id, current_type, wit_json)
            else:
                # It's a pointer to a different tyoe.
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


class Result(Type):
    """A WIT ``result``"""

    def error_type(self) -> Type:
        """Return the type of my error case."""
        return self.from_id(self._me["kind"]["result"]["err"], self._wit)


class NullType(Type):
    def __init__(self, wit_json):
        super().__init__("null", {"name": "null"}, wit_json)


class Record(Type):
    """A WIT ``record`` type"""

    def py_module(self) -> str:
        return "__init__"

    def py_module_path(self) -> str:
        return f"fastly_compute.exceptions.{self.py_package()}"


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
}


METHOD_RE = re.compile(r"\[(static|method|constructor)\]([a-z0-9%-]+)\.([a-z0-9%-]+)")
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
        """Return the dotted path to my definition in wit_world.

        This is used as the key fed to ``remap_wit_errors()`` for this type,
        among other things.
        """
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

    def error_type_of_returned_result(self) -> Type | None:
        """If this Function returns a single ``result`` type, return the type of its error case.

        Otherwise, return None.
        """
        return_type = Type.from_id(self._me.get("result"), self._wit)
        if isinstance(return_type, Result):
            return return_type.error_type()


class Interface:
    """A WIT interface"""

    def __init__(self, interface_json: dict[str, Any], wit_json: dict[str, list[dict]]):
        self._me = interface_json
        self._wit = wit_json

    def name(self) -> str:
        return self._me["name"]

    def functions(self) -> Iterable[Function]:
        """Return the functions and methods defined in this interface."""
        for function in self._me["functions"].values():
            yield Function(function, self._me, self._wit)


class Package:
    """A WIT package"""

    def __init__(self, package_json: dict, wit_json: dict[str, list[dict]]):
        self._package = package_json
        self._wit = wit_json

    def interfaces(self) -> Iterable[Interface]:
        """Return the iterfaces defined in this package."""
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
