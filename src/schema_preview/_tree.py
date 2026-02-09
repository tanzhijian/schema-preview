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
"""

from __future__ import annotations

from ._schema import SchemaNode

# Box-drawing pieces
_TEE = "├── "
_ELBOW = "└── "
_PIPE = "│   "
_SPACE = "    "


def render(node: SchemaNode) -> str:
    """Return a multi-line Unicode tree string for *node*."""
    lines: list[str] = []
    _render_node(node, lines, prefix="", is_root=True)
    return "\n".join(lines)


def _format_type(node: SchemaNode) -> str:
    """Format the type annotation shown after the colon."""
    if node.types == ["list"]:
        if node.element_type:
            return f"list[{node.element_type}]"
        return "list"
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
        lines.append(f"{prefix}{node.key}")
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
