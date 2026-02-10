# schema-preview

> ✨ Built entirely by AI.

Quickly visualise the schema of Python objects as pretty Unicode tree diagrams.

## Features

- **Zero dependencies** — pure Python stdlib only
- **Works with any nested data** — dicts, lists, tuples, sets, and arbitrary values
- **File path support** — pass `.json` file paths directly (as `str` or `pathlib.Path`)
- **Smart merging** — automatically merges schemas across list-of-dicts
- **CLI + library API** — use as a command-line tool or import as a library
- **Fast sampling** — large payloads are sampled (default: first 10 items)

## Install

```bash
uv pip install git+https://github.com/tanzhijian/schema-preview
```

## Usage

### As a library

```python
from schema_preview import preview, schema_of

my_data = {
    "user_id": 123,
    "profile": {
        "nickname": "Archer",
        "settings": {
            "dark_mode": True,
            "notifications": [1, 2, 3],
        },
    },
    "history": [
        {"action": "login", "timestamp": 167890123},
        {"action": "logout", "timestamp": 167895000},
    ],
}

preview(my_data)  # prints to stdout
text = schema_of(my_data)  # returns string
```

You can also pass file paths directly:

```python
from pathlib import Path

preview(Path("data.json"))        # pathlib.Path
preview("data.json")              # or string path
```

Output:

```
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
```

### As a CLI

```bash
# From a file
schema-preview data.json

# From stdin
cat data.json | schema-preview

# Adjust sampling
schema-preview data.json --max-items 50
```

## Development

```bash
uv run ruff check .  # lint
uv run mypy .        # type-check
uv run pytest        # run tests
```

See [AGENTS.md](./AGENTS.md) for detailed code style and testing conventions.

## License

MIT
