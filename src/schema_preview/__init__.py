"""schema-preview – quickly visualise the schema of a Python object.

Usage (Python API)::

    from schema_preview import preview

    preview(my_dict)                # prints to stdout
    preview([1, 2, 3])              # works with any iterable
    text = preview(my_dict, print_result=False)  # returns string

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
]


def preview(
    data: Any,
    *,
    max_items: int = 10,
    print_result: bool = True,
) -> str:
    """Infer schema of *data* and return / print a tree diagram.

    Parameters
    ----------
    data:
        The object to inspect.  Accepts ``dict``, ``list``, ``tuple``,
        ``set``, ``frozenset``, or any value with a recognisable type.
    max_items:
        Maximum number of list elements sampled for type inference.
    print_result:
        If *True* (default) the tree is also printed to stdout.
    """
    tree = infer_schema(data, max_items=max_items)
    text = render(tree)
    if print_result:
        print(text)
    return text
