"""schema-preview – quickly visualise the schema of a Python object.

Usage (Python API)::

    from schema_preview import preview, schema_of

    preview(my_dict)                # prints to stdout
    preview([1, 2, 3])              # works with any iterable
    text = schema_of(my_dict)       # returns string

Usage (CLI)::

    schema-preview data.json
    cat data.json | schema-preview
"""

from __future__ import annotations

from typing import Any

from ._cli import main
from ._schema import SchemaNode, infer_schema
from ._tree import render

__all__ = [
    "SchemaNode",
    "infer_schema",
    "main",
    "preview",
    "render",
    "schema_of",
]


def schema_of(
    data: Any,
    *,
    max_items: int = 10,
) -> str:
    """Infer schema of *data* and return a tree diagram string.

    Parameters
    ----------
    data:
        The object to inspect.  Accepts ``dict``, ``list``, ``tuple``,
        ``set``, ``frozenset``, or any value with a recognisable type.
    max_items:
        Maximum number of list elements sampled for type inference.
    """
    tree = infer_schema(data, max_items=max_items)
    return render(tree)


def preview(
    data: Any,
    *,
    max_items: int = 10,
) -> None:
    """Infer schema of *data* and print a tree diagram to stdout.

    Parameters
    ----------
    data:
        The object to inspect.  Accepts ``dict``, ``list``, ``tuple``,
        ``set``, ``frozenset``, or any value with a recognisable type.
    max_items:
        Maximum number of list elements sampled for type inference.
    """
    print(schema_of(data, max_items=max_items))
