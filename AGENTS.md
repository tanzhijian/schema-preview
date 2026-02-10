# AGENTS.md — schema-preview

## Project Overview

A zero-dependency Python CLI tool and library that infers and visualises the
schema of Python objects (dicts, lists, tuples, sets) as Unicode tree diagrams.
Built with Python 3.14, managed by `uv`.

## Build / Lint / Test Commands

```bash
# Run all checks (lint → type-check → tests) — the canonical CI command
uv run ruff check .
uv run mypy .
uv run pytest .

# Run a single test by name
uv run pytest tests/test_schema_preview.py -k "test_full_example"

# Run a single test class
uv run pytest tests/test_schema_preview.py -k "TestCLI"

# Auto-fix lint issues (imports, formatting)
uv run ruff check . --fix

# Type-check only
uv run mypy .

# Install / sync dependencies
uv sync
```

Always run all checks before considering a task complete. All three must
pass: ruff, mypy strict, pytest.

## Project Layout

```
src/schema_preview/
├── __init__.py       # Public API: preview(), schema_of(), main()
├── _cli.py           # CLI entry point (argparse)
├── _schema.py        # Core engine: SchemaNode dataclass, infer_schema()
└── _tree.py          # Unicode tree renderer: render()
tests/
├── test_schema_preview.py   # All tests (single file)
└── data/                    # JSON fixtures for CLI tests
```

## Code Style

### Python Version & Tooling

- **Python 3.14** — see `.python-version`.
- **uv** — always prefix commands with `uv run`.
- **Zero runtime dependencies** — stdlib only. Dev deps: ruff, mypy, pytest.

### Formatting & Line Length

- **Line length: 79 characters** (strict PEP 8). Configured in
  `pyproject.toml` under `[tool.ruff]`.

### Imports

- **Always** start every `.py` file with `from __future__ import annotations`.
- Order: stdlib → third-party → local, enforced by ruff `I` rule (isort).
- Use `from ._module import name` for intra-package imports (relative).
- Public re-exports go in `__init__.py` with an explicit `__all__` list.

### Type Annotations

- **mypy strict mode** is enabled (`strict = true` in `pyproject.toml`).
- Every function must have full parameter and return type annotations.
- Use `str | None` union syntax (not `Optional`).
- Use lowercase generics: `list[str]`, `dict[str, Any]`.

### Naming Conventions

- **Private modules**: prefixed with `_` (e.g. `_cli.py`, `_schema.py`,
  `_tree.py`). Only `__init__.py` is public.
- **Private functions**: prefixed with `_` (e.g. `_type_name()`,
  `_infer_dict()`).
- **Public API**: defined in `__init__.py` via `__all__`.
- **Constants**: `_UPPER_SNAKE` for private module-level constants.
- **Classes**: `PascalCase`. **Functions/variables**: `snake_case`.

### Docstrings

- Every module gets a module-level docstring with description and usage
  examples (using `::` for code blocks).
- Public functions use NumPy-style docstrings (`Parameters\n----------`).
- Private functions use concise single-line docstrings.

### Data Structures

- Use `@dataclass` for data containers (see `SchemaNode`).
- Use `field(default_factory=list)` for mutable defaults.

### Error Handling

- Use `warnings.warn()` for non-fatal issues (e.g. mixed types in a list),
  **not** exceptions. This keeps the tool non-blocking.
- Use `sys.exit(1)` only in the CLI entry point for usage errors.
- Raise `RuntimeError` for truly unexpected/unrecoverable states.

### Comments

- Use `# ── section name ──────...` dash-line comments to separate major
  sections in both source and test files.

## Testing Conventions

### Framework & Structure

- **pytest** — no unittest. Run with `uv run pytest`.
- **Class-based grouping**: group related tests in classes
  (`TestPreview`, `TestSchemaOf`, `TestCLI`, `TestEdgeCases`, etc.).
  Do **not** use standalone test functions at module level.
- **Single test file**: all tests live in `tests/test_schema_preview.py`.
- Import from the public API (`from schema_preview import ...`) and private
  modules when testing internals (`from schema_preview._cli import main`).

### Fixtures

- Use `@pytest.fixture(scope="class")` for shared setup within a test class.

### Assertion Patterns

- **Substring checks**: `assert "x: list[int]" in result` — for verifying
  tree output contains expected type annotations.
- **Exact match**: `assert result == textwrap.dedent("""...""")` — for full
  tree structure validation. Use `textwrap.dedent` with `"""\` to avoid
  leading newlines.
- **Warning checks**: wrap in `warnings.catch_warnings(record=True)` and
  assert on `len(w)` and `str(w[0].message)`.
- **Node inspection**: access `node.key`, `node.types`, `node.children`,
  `node.element_type` directly on `SchemaNode`.

### CLI Testing

- **Subprocess** (integration): `subprocess.run()` with
  `[uv_path, "run", "schema-preview", ...]`. Resolve `uv` via
  `shutil.which("uv")`.
- **Direct call** (fast): use `_run_cli_direct()` helper that patches
  `sys.stdout`, `sys.stdin`, `sys.argv` and calls `cli_main()`.
  Prefer this for most CLI tests.

### Test Naming

- Method names: `test_<what_is_being_tested>` (e.g. `test_full_example`,
  `test_mixed_types_warning`, `test_stdin`).
- Docstrings on tests are optional but encouraged for non-obvious cases.

## Key Design Decisions

- Pipeline: `data → _maybe_load() → infer_schema() → SchemaNode tree → render() → string`.
  Keep these stages separate.
- **Path detection**: `Path` objects always treated as files; strings checked with
  `Path.is_file()` to avoid false positives (so `schema_of("hello")` still works).
- **File validation**: only `.json` files allowed; `FileNotFoundError` if missing,
  `ValueError` if wrong extension.
- Lists are **sampled** (`max_items=10` default) via `itertools.islice`.
- Merging list-of-dicts: collect all keys across sampled dicts with type sets.
- Renderer uses Unicode box-drawing chars (`├── `, `└── `, `│   `).
