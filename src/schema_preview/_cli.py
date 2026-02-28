"""Command-line interface for schema-preview.

Usage::

    schema-preview data.json
    schema-preview data.jsonl
    schema-preview data.json --max-items 20
    cat data.json | schema-preview
    cat data.jsonl | schema-preview --jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ._loader import load_jsonl, load_path
from ._schema import infer_schema
from ._tree import render


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="schema-preview",
        description=("Quickly preview the schema of a JSON / JSONL file."),
    )
    parser.add_argument(
        "file",
        nargs="?",
        default=None,
        help=("Path to a JSON or JSONL file. Reads from stdin if omitted."),
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=10,
        help=(
            "Max number of list elements sampled for type "
            "inference (default: 10)."
        ),
    )
    parser.add_argument(
        "--jsonl",
        action="store_true",
        default=False,
        help=(
            "Treat stdin as JSONL (one JSON object per line). "
            "Auto-detected for .jsonl files."
        ),
    )
    return parser


def main() -> None:
    """Entry-point wired to the ``schema-preview`` console script."""
    parser = _build_parser()
    args = parser.parse_args()

    data: Any
    if args.file is not None:
        data = load_path(Path(args.file))
    else:
        if sys.stdin.isatty():
            parser.print_help()
            sys.exit(1)
        if args.jsonl:
            data = load_jsonl(sys.stdin)
        else:
            data = json.load(sys.stdin)

    tree = infer_schema(data, max_items=args.max_items)
    print(render(tree))
