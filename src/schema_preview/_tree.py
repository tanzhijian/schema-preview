"""Tree renderer – turns a SchemaNode tree into a pretty Unicode string.

Produces output like::

    root
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
    _render_node(node, lines, prefix="", is_root=True)
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
    # Multiple types – show as list of strings
    return repr(node.types)


def _render_node(
    node: SchemaNode,
    lines: list[str],
    *,
    prefix: str,
    is_root: bool,
) -> None:
    if is_root:
        if node.types == ["dict"]:
            # Dict root: show just the key name (classic style).
            lines.append(f"{prefix}{node.key}")
        else:
            # Non-dict root (list, tuple, set, primitive, …): show type.
            lines.append(f"{prefix}{node.key}: {_format_type(node)}")
    else:
        lines.append(f"{prefix}{node.key}: {_format_type(node)}")

    children = node.children
    for i, child in enumerate(children):
        is_last = i == len(children) - 1
        connector = _ELBOW if is_last else _TEE
        child_prefix = prefix + (_SPACE if is_last else _PIPE)

        # First, print the child's own line
        child_line = f"{prefix}{connector}{child.key}: {_format_type(child)}"
        lines.append(child_line)

        # If the child itself has children, recurse for those grandchildren
        if child.children:
            _render_children(child.children, lines, prefix=child_prefix)


def _render_children(
    children: list[SchemaNode],
    lines: list[str],
    *,
    prefix: str,
) -> None:
    for i, child in enumerate(children):
        is_last = i == len(children) - 1
        connector = _ELBOW if is_last else _TEE
        child_prefix = prefix + (_SPACE if is_last else _PIPE)

        child_line = f"{prefix}{connector}{child.key}: {_format_type(child)}"
        lines.append(child_line)

        if child.children:
            _render_children(child.children, lines, prefix=child_prefix)
