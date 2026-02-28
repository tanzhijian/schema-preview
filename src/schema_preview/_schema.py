"""Core schema inference engine.

Converts a Python dict (or any value) into an intermediate SchemaNode tree.
The tree captures:
  - key name
  - inferred type(s)
  - children (for dicts / lists-of-dicts)
  - warnings (e.g. mixed types inside a list)

Performance: list/tuple/set are only sampled up to `max_items` elements
(default 10) to keep inference fast on large payloads.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from itertools import islice
from typing import Any


@dataclass
class SchemaNode:
    """One node in the inferred schema tree."""

    key: str
    types: list[str]  # e.g. ["int"], or ["int", "NoneType"]
    children: list[SchemaNode] = field(default_factory=list)

    # When the node represents a list whose elements are all the same
    # primitive type we store it here so the renderer can print
    # ``list[int]`` instead of just ``list``.
    element_type: str | None = None


def infer_schema(
    data: Any,
    *,
    key: str = "root",
    max_items: int = 10,
) -> SchemaNode:
    """Build a *SchemaNode* tree from *data*.

    Parameters
    ----------
    data:
        The value to inspect.  Typically a ``dict`` loaded from JSON.
    key:
        Label for the root node.
    max_items:
        How many elements of a list / tuple / set to inspect before
        stopping.  Keeps inference O(1) for huge arrays.
    """
    if isinstance(data, dict):
        return _infer_dict(data, key=key, max_items=max_items)
    if isinstance(data, (list, tuple, set, frozenset)):
        return _infer_sequence(data, key=key, max_items=max_items)
    return SchemaNode(key=key, types=[_type_name(data)])


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _type_name(value: Any) -> str:
    return type(value).__name__


def _infer_dict(
    data: dict[str, Any],
    *,
    key: str,
    max_items: int,
) -> SchemaNode:
    """Infer schema for a single dict."""
    children = [
        infer_schema(v, key=k, max_items=max_items) for k, v in data.items()
    ]
    return SchemaNode(key=key, types=["dict"], children=children)


def _infer_sequence(
    data: list[Any] | tuple[Any, ...] | set[Any] | frozenset[Any],
    *,
    key: str,
    max_items: int,
) -> SchemaNode:
    """Infer schema for a list-like container.

    Strategy
    --------
    1. Sample up to *max_items* elements.
    2. Collect all distinct type names.
    3. If **all** sampled elements are dicts → merge keys and recurse
       (the node becomes ``list[dict]`` with merged children).
    4. If all elements share one primitive type → ``list[<type>]``.
    5. Mixed types → emit a warning and fall back to ``list``.
    """
    container_type = _type_name(data)  # "list", "tuple", "set", …
    sampled: list[Any] = list(islice(data, max_items))

    if not sampled:
        return SchemaNode(key=key, types=[container_type])

    type_names: set[str] = {_type_name(v) for v in sampled}

    # --- all dicts → merge --------------------------------------------------
    if type_names == {"dict"}:
        children = _merge_dict_schemas(sampled, max_items=max_items)
        return SchemaNode(
            key=key,
            types=[container_type],
            children=children,
            element_type="dict",
        )

    # --- single primitive type ----------------------------------------------
    if len(type_names) == 1:
        (element_type,) = type_names
        return SchemaNode(
            key=key,
            types=[container_type],
            element_type=element_type,
        )

    # --- mixed types --------------------------------------------------------
    warnings.warn(
        f"Key '{key}': mixed types in list: {sorted(type_names)}",
        stacklevel=2,
    )
    return SchemaNode(key=key, types=[container_type])


def _merge_all_dicts(
    key: str,
    values: list[Any],
    *,
    max_items: int,
) -> SchemaNode:
    """All values for *key* are dicts -> recurse deeper."""
    merged = _merge_dict_schemas(values, max_items=max_items)
    return SchemaNode(key=key, types=["dict"], children=merged)


def _merge_all_lists(
    key: str,
    values: list[Any],
    *,
    max_items: int,
) -> SchemaNode:
    """All values for *key* are lists -> flatten and recurse."""
    flat = [item for lst in values if isinstance(lst, list) for item in lst]
    return _infer_sequence(flat, key=key, max_items=max_items)


def _merge_nullable_dict(
    key: str,
    types: list[str],
    values: list[Any],
    *,
    max_items: int,
) -> SchemaNode | None:
    """Handle {NoneType, dict} -> recurse into non-None dicts."""
    dict_vals = [v for v in values if isinstance(v, dict)]
    if not dict_vals:
        return None
    merged = _merge_dict_schemas(dict_vals, max_items=max_items)
    return SchemaNode(key=key, types=types, children=merged)


def _merge_nullable_list(
    key: str,
    types: list[str],
    values: list[Any],
    *,
    max_items: int,
) -> SchemaNode | None:
    """Handle {NoneType, list} -> recurse into non-None lists."""
    flat = [item for v in values if isinstance(v, list) for item in v]
    if not flat:
        return None
    node = _infer_sequence(flat, key=key, max_items=max_items)
    node.types = types  # preserve nullable annotation
    return node


def _merge_dict_schemas(
    dicts: list[dict[str, Any]],
    *,
    max_items: int,
) -> list[SchemaNode]:
    """Merge keys across many dicts, tracking per-key type sets."""

    # Ordered set of all keys seen (preserves first-seen order).
    all_keys: dict[str, None] = {}
    # key -> list of types seen
    key_types: dict[str, list[str]] = {}
    # key -> list of sub-values that are dicts or lists (for recursion)
    key_values: dict[str, list[Any]] = {}

    for d in dicts:
        for k, v in d.items():
            all_keys.setdefault(k, None)
            key_types.setdefault(k, []).append(_type_name(v))
            key_values.setdefault(k, []).append(v)

    children: list[SchemaNode] = []
    for k in all_keys:
        distinct = sorted(set(key_types[k]))
        distinct_set = set(distinct)

        if distinct == ["dict"]:
            children.append(
                _merge_all_dicts(k, key_values[k], max_items=max_items)
            )
        elif distinct == ["list"]:
            children.append(
                _merge_all_lists(k, key_values[k], max_items=max_items)
            )
        elif distinct_set == {"NoneType", "dict"}:
            node = _merge_nullable_dict(
                k, distinct, key_values[k], max_items=max_items
            )
            if node is not None:
                children.append(node)
            else:
                children.append(SchemaNode(key=k, types=distinct))
        elif distinct_set == {"NoneType", "list"}:
            node = _merge_nullable_list(
                k, distinct, key_values[k], max_items=max_items
            )
            if node is not None:
                children.append(node)
            else:
                children.append(SchemaNode(key=k, types=distinct))
        else:
            children.append(SchemaNode(key=k, types=distinct))

    return children
