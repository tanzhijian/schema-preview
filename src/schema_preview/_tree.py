"""Tree renderer – turns a SchemaNode tree into a pretty Unicode string.

Produces output like::

    root: dict
    ├── user_id: int
    ├── profile: dict
    │   ├── nickname: str
    │   └── settings: dict
    │       ├── dark_mode: bool
    │       └── notifications: list[int]
    └── history: list[dict]
        ├── action: str
        └── timestamp: int

Non-dict root values are also supported::

    root: list[int]

    root: list[dict]
    ├── action: str
    └── timestamp: int
"""

from __future__ import annotations

from ._schema import SchemaNode

# Box-drawing pieces
_TEE = "├── "
_ELBOW = "└── "
_PIPE = "│   "
_SPACE = "    "

# Sequence type names that support ``type[element]`` formatting.
_SEQUENCE_TYPES = {"list", "tuple", "set", "frozenset"}


def render(node: SchemaNode) -> str:
    """Return a multi-line Unicode tree string for *node*."""
    lines: list[str] = []
    _render_node(node, lines, prefix="")
    return "\n".join(lines)


def _format_type(node: SchemaNode) -> str:
    """Format the type annotation shown after the colon."""
    if len(node.types) == 1 and node.types[0] in _SEQUENCE_TYPES:
        seq_type = node.types[0]
        if node.element_type:
            return f"{seq_type}[{node.element_type}]"
        return seq_type
    if node.types == ["dict"]:
        return "dict"
    if len(node.types) == 1:
        return node.types[0]

    # Nullable compound types – e.g. NoneType | dict, NoneType | list[int]
    non_none = [t for t in node.types if t != "NoneType"]
    if "NoneType" in node.types and len(non_none) == 1:
        compound = non_none[0]
        if compound in _SEQUENCE_TYPES and node.element_type:
            return f"NoneType | {compound}[{node.element_type}]"
        if compound == "dict" and node.children:
            return "NoneType | dict"
        if compound in _SEQUENCE_TYPES and not node.element_type:
            return f"NoneType | {compound}"

    # Multiple types – use pipe syntax (e.g. str | int)
    return " | ".join(node.types)


def _render_node(
    node: SchemaNode,
    lines: list[str],
    *,
    prefix: str,
) -> None:
    """Render one node and its children."""
    lines.append(f"{prefix}{node.key}: {_format_type(node)}")

    if node.children:
        _render_children(node.children, lines, prefix=prefix)


def _render_children(
    children: list[SchemaNode],
    lines: list[str],
    *,
    prefix: str,
) -> None:
    """Render child nodes with tree connectors."""
    for i, child in enumerate(children):
        is_last = i == len(children) - 1
        connector = _ELBOW if is_last else _TEE
        child_prefix = prefix + (_SPACE if is_last else _PIPE)

        child_line = f"{prefix}{connector}{child.key}: {_format_type(child)}"
        lines.append(child_line)

        if child.children:
            _render_children(child.children, lines, prefix=child_prefix)
