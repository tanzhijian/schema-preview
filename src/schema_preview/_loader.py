"""File loading utilities for JSON and JSONL files.

Centralises all file I/O so that both the Python API
(``__init__.py``) and the CLI (``_cli.py``) share a single
code path for validation and parsing.

Usage::

    from ._loader import load_path, load_jsonl

    data = load_path(Path("data.json"))
    data = load_jsonl(sys.stdin)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import IO, Any

_SUPPORTED_SUFFIXES = {".json", ".jsonl"}


def load_jsonl(f: IO[str]) -> list[Any]:
    """Parse a JSONL stream (one JSON object per line)."""
    return [json.loads(line) for line in f if line.strip()]


def load_path(path: Path) -> Any:
    """Read and parse a JSON or JSONL file from *path*.

    Parameters
    ----------
    path:
        Must point to an existing ``.json`` or ``.jsonl`` file.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    ValueError
        If *path* has an unsupported extension.
    """
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    suffix = path.suffix.lower()
    if suffix not in _SUPPORTED_SUFFIXES:
        raise ValueError(
            f"Unsupported file type '{suffix}': "
            f"only .json and .jsonl files are supported"
        )
    with open(path, encoding="utf-8") as f:
        if suffix == ".jsonl":
            return load_jsonl(f)
        return json.load(f)
