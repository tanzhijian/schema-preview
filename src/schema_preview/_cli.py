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
from typing import IO, Any

from ._schema import infer_schema
from ._tree import render


def _load_jsonl(f: IO[str]) -> list[Any]:
    """Parse a JSONL stream (one JSON object per line)."""
    return [json.loads(line) for line in f if line.strip()]


def _build_parser() -> argparse.ArgumentParser:
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
        is_jsonl = args.file.endswith(".jsonl")
        with open(args.file, encoding="utf-8") as f:
            data = _load_jsonl(f) if is_jsonl else json.load(f)
    else:
        if sys.stdin.isatty():
            parser.print_help()
            sys.exit(1)
        if args.jsonl:
            data = _load_jsonl(sys.stdin)
        else:
            data = json.load(sys.stdin)

    tree = infer_schema(data, max_items=args.max_items)
    print(render(tree))
