"""schema-preview – quickly visualise the schema of a Python object.

Usage (Python API)::

    from schema_preview import preview, schema_of

    preview(my_dict)                # prints to stdout
    preview([1, 2, 3])              # works with any iterable
    text = schema_of(my_dict)       # returns string

    # Also accepts file paths (str or pathlib.Path):
    from pathlib import Path
    preview(Path("data.json"))
    preview("data.json")
    preview(Path("data.jsonl"))

Usage (CLI)::

    schema-preview data.json
    schema-preview data.jsonl
    cat data.json | schema-preview
    cat data.jsonl | schema-preview --jsonl
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ._cli import main
from ._loader import load_path
from ._schema import SchemaNode, infer_schema
from ._tree import render

# Strings longer than this or containing newlines are never file paths.
# 4096 covers PATH_MAX on Linux/macOS; Windows MAX_PATH is 260.
_MAX_PATH_LEN = 4096

__all__ = [
    "SchemaNode",
    "infer_schema",
    "main",
    "preview",
    "render",
    "schema_of",
]


def _maybe_load(data: Any) -> Any:
    """If *data* is a path, load it; otherwise return as-is."""
    if isinstance(data, Path):
        return load_path(data)
    if isinstance(data, str):
        if len(data) > _MAX_PATH_LEN or "\n" in data:
            return data
        p = Path(data)
        if p.is_file():
            return load_path(p)
    return data


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
        ``set``, ``frozenset``, a file path (``str`` or
        ``pathlib.Path`` to a ``.json`` file), or any value with a
        recognisable type.
    max_items:
        Maximum number of list elements sampled for type inference.
    """
    data = _maybe_load(data)
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
        ``set``, ``frozenset``, a file path (``str`` or
        ``pathlib.Path`` to a ``.json`` file), or any value with a
        recognisable type.
    max_items:
        Maximum number of list elements sampled for type inference.
    """
    print(schema_of(data, max_items=max_items))
