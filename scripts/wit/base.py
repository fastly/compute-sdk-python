"""Base classes shared across the WIT abstraction layer.

DocsHaver and Thing are the documentation and identity base classes used by
both the type system (types.py) and the structural traversal layer (wit.py).
Kept separate to avoid circular imports between those two modules.
"""

# ruff: noqa D102

import re
import textwrap
from typing import Any

from .utils import lower_snake, upper_camel


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

    def docs_for_python(self) -> str:
        """Return docs() with high-confidence WIT-isms rewritten to Python idioms.

        Transformations applied:
        - ``ok(some(X))`` → ``X``   (unwrapped option inside ok)
        - ``ok(none)``    → ``None`` (absent option inside ok)
        - ``ok(X)``       → ``X``   (plain ok value)
        - ``none``        → ``None``
        - ``true``        → ``True``
        - ``false``       → ``False``
        - kebab-case identifiers inside backticks → snake_case
          e.g. ``kv-store`` → ``kv_store``

        ``err(...)`` phrases are left untouched — they don't have a clean
        mechanical replacement and the ``:raises`` block already covers the
        intent.
        """
        text = self.docs()
        if not text:
            return text

        # ok(some(X)) → X  (must come before ok(X) so the longer form matches first)
        text = re.sub(r"`ok\(some\(([^)]+)\)\)`", r"`\1`", text)
        # ok(none) → None
        text = re.sub(r"`ok\(none\)`", "`None`", text)
        # ok(X) → X  (plain ok wrapping a value)
        text = re.sub(r"`ok\(([^)]+)\)`", r"`\1`", text)
        # standalone `none` → `None`
        text = re.sub(r"`none`", "`None`", text)
        # `true` / `false` → `True` / `False`
        text = re.sub(r"`true`", "`True`", text)
        text = re.sub(r"`false`", "`False`", text)
        # kebab-case identifiers inside backticks → snake_case
        # Only matches pure kebab identifiers (letters, digits, hyphens).
        text = re.sub(
            r"`([a-z][a-z0-9]*(?:-[a-z0-9]+)+)`",
            lambda m: "`" + m.group(1).replace("-", "_") + "`",
            text,
        )
        return text

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

    def interface_name(self) -> str:
        """Return the name of the interface where this thing is defined."""
        raise NotImplementedError

    def wit_module_path(self) -> str:
        """Return the full dotted path to the Python module in which I am defined."""
        return "wit_world.imports." + lower_snake(self.interface_name())

    def wit_path(self):
        """Return the dotted path to my definition in wit_world.

        This is used as the key fed to ``remap_wit_errors()`` for a type,
        among other things.
        """
        return self.wit_module_path() + "." + upper_camel(self.name())

    def py_exception_name(self) -> str:
        """Return my name, fashioned as a suitable name for an exception."""
        return upper_camel(self.name())
