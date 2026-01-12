"""Little helpers used in patch generation"""

import textwrap


def only(iterable):
    """Return the one and only item of the iterable, raising ValueError if there
    are more or fewer than one.
    """
    items = list(iterable)
    if (len_ := len(items)) != 1:
        raise ValueError(f"Iterable had {len_} items, not 1.")
    return items[0]


def upper_camel(s: str) -> str:
    """Convert lower-kebab case to UpperCamelCase."""
    return "".join(word.capitalize() for word in s.split("-"))


def lower_snake(s: str) -> str:
    """Convert lower-kebab case to lower_snake_case."""
    return s.replace("-", "_")


def shouty_snake(s: str) -> str:
    """Convert lower-kebab case to SHOUTY_SNAKE_CASE."""
    return s.replace("-", "_").upper()


def indent(s: str):
    """Indent as for a docstring.

    Indent all but the first line of a string by 4 spaces, strip leading and
    trailing whitespace, and put a newline at the end if there's more than 1
    line.
    """
    return textwrap.indent(s, "    ").strip()
