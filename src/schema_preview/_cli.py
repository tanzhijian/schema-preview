"""Command-line interface for schema-preview.

Usage::

    schema-preview data.json
    schema-preview data.json --max-items 20
    cat data.json | schema-preview
"""

from __future__ import annotations

import argparse
import json
import sys

from ._schema import infer_schema
from ._tree import render


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="schema-preview",
        description="Quickly preview the schema of a JSON file.",
    )
    parser.add_argument(
        "file",
        nargs="?",
        default=None,
        help="Path to a JSON file. Reads from stdin if omitted.",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=10,
        help=(
            "Max number of list elements sampled for type inference "
            "(default: 10)."
        ),
    )
    return parser


def main() -> None:
    """Entry-point wired to the ``schema-preview`` console script."""
    parser = _build_parser()
    args = parser.parse_args()

    if args.file is not None:
        with open(args.file, encoding="utf-8") as f:
            data = json.load(f)
    else:
        if sys.stdin.isatty():
            parser.print_help()
            sys.exit(1)
        data = json.load(sys.stdin)

    tree = infer_schema(data, max_items=args.max_items)
    print(render(tree))
