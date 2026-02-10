from __future__ import annotations

import json
import shutil
import sys
import textwrap
import warnings
from io import StringIO
from pathlib import Path

import pytest

from schema_preview import preview, schema_of
from schema_preview._cli import main as cli_main
from schema_preview._schema import infer_schema


def _get_uv_path() -> str:
    """Get path to uv executable from PATH.

    Raises RuntimeError if uv is not found, ensuring tests fail clearly
    rather than silently with confusing subprocess errors.
    """
    uv_path = shutil.which("uv")
    if uv_path is None:
        raise RuntimeError(
            "uv not found in PATH. "
            "Please ensure uv is installed and available in your PATH."
        )
    return uv_path


def _run_cli_direct(
    file_path: str | None = None, stdin_data: str | None = None
) -> str:
    """Run CLI directly by calling main() function.

    Args:
        file_path: Path to input file (if None, reads from stdin)
        stdin_data: Data to pass via stdin (if file_path is None)

    Returns:
        Captured stdout output
    """
    old_stdout = sys.stdout
    old_argv = sys.argv
    old_stdin = sys.stdin
    stdout_capture = StringIO()
    try:
        sys.stdout = stdout_capture
        if stdin_data is not None:
            sys.stdin = StringIO(stdin_data)

        if file_path:
            sys.argv = ["schema-preview", file_path]
        else:
            sys.argv = ["schema-preview"]

        cli_main()
    except SystemExit:
        pass
    finally:
        output = stdout_capture.getvalue()
        sys.stdout = old_stdout
        sys.stdin = old_stdin
        sys.argv = old_argv

    return output


# ── basic rendering ────────────────────────────────────────────────


class TestPreview:
    def test_prints_to_stdout(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        preview({"a": 1, "b": "hello"})
        captured = capsys.readouterr()
        assert "a: int" in captured.out
        assert "b: str" in captured.out


class TestSchemaOf:
    def test_full_example(self) -> None:
        """The showcase example from the README."""
        my_dict = {
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
                {"action": "login", "timestamp": 167890123},
            ],
        }
        expected = textwrap.dedent("""\
            root
            ├── user_id: int
            ├── profile: dict
            │   ├── nickname: str
            │   └── settings: dict
            │       ├── dark_mode: bool
            │       └── notifications: list[int]
            └── history: list[dict]
                ├── action: str
                └── timestamp: int""")
        assert schema_of(my_dict) == expected

    def test_flat_dict(self) -> None:
        data = {"a": 1, "b": "hello", "c": 3.14}
        result = schema_of(data)
        assert "a: int" in result
        assert "b: str" in result
        assert "c: float" in result

    def test_empty_dict(self) -> None:
        result = schema_of({})
        assert result == "root"

    def test_empty_list_value(self) -> None:
        result = schema_of({"items": []})
        assert "items: list" in result


# ── list type inference ────────────────────────────────────────────


class TestListInference:
    def test_homogeneous_list(self) -> None:
        result = schema_of({"x": [1, 2, 3]})
        assert "x: list[int]" in result

    def test_list_of_strings(self) -> None:
        result = schema_of({"tags": ["a", "b"]})
        assert "tags: list[str]" in result

    def test_list_of_dicts(self) -> None:
        data = {"rows": [{"id": 1}, {"id": 2}]}
        result = schema_of(data)
        assert "rows: list[dict]" in result
        assert "id: int" in result

    def test_mixed_types_warning(self) -> None:
        data = {"vals": [1, "two", 3]}
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = schema_of(data)
            assert len(w) == 1
            assert "mixed types" in str(w[0].message)
        assert "vals: list" in result


# ── merged dict keys ──────────────────────────────────────────────


class TestMergedDictKeys:
    def test_inconsistent_keys(self) -> None:
        data = {
            "history": [
                {"action": "login", "timestamp": 167890123},
                {"action": "login", "timestamp": 167890123},
                {"action": "login", "result": None},
                {"action": "login", "result": 1},
            ],
        }
        result = schema_of(data)
        assert "action: str" in result
        assert "timestamp: int" in result
        assert "result:" in result
        assert "'NoneType'" in result
        assert "'int'" in result

    def test_all_keys_same(self) -> None:
        data = {
            "items": [
                {"k": 1},
                {"k": 2},
                {"k": 3},
            ]
        }
        result = schema_of(data)
        assert "k: int" in result


# ── max_items sampling ────────────────────────────────────────────


class TestMaxItems:
    def test_samples_limited_elements(self) -> None:
        """With max_items=2, only first 2 elements are inspected."""
        data = {"nums": list(range(10_000))}
        node = infer_schema(data, max_items=2)
        # Should still correctly infer int
        child = node.children[0]
        assert child.element_type == "int"

    def test_large_list_performance(self) -> None:
        """Ensure a huge list doesn't blow up."""
        data = {"big": list(range(1_000_000))}
        result = schema_of(data, max_items=5)
        assert "big: list[int]" in result


# ── schema node structure ─────────────────────────────────────────


class TestSchemaNode:
    def test_simple_node(self) -> None:
        node = infer_schema(42, key="val")
        assert node.key == "val"
        assert node.types == ["int"]
        assert node.children == []

    def test_dict_node_children(self) -> None:
        node = infer_schema({"a": 1, "b": "x"})
        assert node.types == ["dict"]
        assert len(node.children) == 2
        assert node.children[0].key == "a"
        assert node.children[1].key == "b"


# ── deeply nested ─────────────────────────────────────────────────


class TestDeepNesting:
    def test_three_levels(self) -> None:
        data = {
            "level1": {
                "level2": {
                    "level3": "deep",
                }
            }
        }
        result = schema_of(data)
        assert "level1: dict" in result
        assert "level2: dict" in result
        assert "level3: str" in result


# ── CLI ───────────────────────────────────────────────────────────


@pytest.fixture(scope="class")
def data_paths() -> dict[str, Path]:
    """Fixture providing test data file paths (class-scoped)."""
    base = Path(__file__).parent / "data"
    return {
        "dict_file": base / "dict.json",
        "list_file": base / "list.json",
    }


class TestCLI:
    def test_dict_file_subprocess(self, data_paths: dict[str, Path]) -> None:
        """Integration test: verify CLI works via subprocess."""
        import subprocess

        result = subprocess.run(
            [
                _get_uv_path(),
                "run",
                "schema-preview",
                str(data_paths["dict_file"]),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # Check top-level keys
        assert "id: int" in result.stdout
        assert "dateTime: str" in result.stdout
        assert "squadHome: dict" in result.stdout
        assert "squadAway: dict" in result.stdout
        # Check nested structure
        assert "players: list[dict]" in result.stdout
        assert "substitutions: list[dict]" in result.stdout

    def test_list_file(self, data_paths: dict[str, Path]) -> None:
        """Fast test: verify list file parsing via direct function call."""
        output = _run_cli_direct(str(data_paths["list_file"]))
        # Check root is list[dict]
        assert "root: list[dict]" in output
        # Check top-level keys in dict elements
        assert "team_id: int" in output
        assert "team_name: str" in output
        assert "lineup: list[dict]" in output
        # Check nested structure
        assert "player_id: int" in output
        assert "country: dict" in output

    def test_stdin(self) -> None:
        """Fast test: verify stdin input via direct function call."""
        data = json.dumps({"x": [1, 2, 3]})
        output = _run_cli_direct(stdin_data=data)
        assert "x: list[int]" in output

    def test_max_items_flag(self, data_paths: dict[str, Path]) -> None:
        """Fast test: verify --max-items flag via direct function call."""
        old_argv = sys.argv
        old_stdout = sys.stdout
        stdout_capture = StringIO()
        try:
            sys.argv = [
                "schema-preview",
                str(data_paths["dict_file"]),
                "--max-items",
                "5",
            ]
            sys.stdout = stdout_capture
            cli_main()
        except SystemExit:
            pass
        finally:
            output = stdout_capture.getvalue()
            sys.argv = old_argv
            sys.stdout = old_stdout

        # Should still show structure, just limited sampling
        assert "players: list[dict]" in output


# ── edge cases ────────────────────────────────────────────────────


class TestEdgeCases:
    def test_none_value(self) -> None:
        result = schema_of({"x": None})
        assert "x: NoneType" in result

    def test_bool_value(self) -> None:
        result = schema_of({"flag": True})
        assert "flag: bool" in result

    def test_nested_list_of_lists(self) -> None:
        data = {"matrix": [[1, 2], [3, 4]]}
        result = schema_of(data)
        assert "matrix: list[list]" in result

    def test_list_with_nested_dicts_different_depths(self) -> None:
        data = {
            "items": [
                {"a": {"b": 1}},
                {"a": {"b": 2, "c": 3}},
            ]
        }
        result = schema_of(data)
        assert "a: dict" in result
        assert "b: int" in result
        assert "c: int" in result


# ── top-level iterables ───────────────────────────────────────────


class TestTopLevelIterables:
    def test_list_of_ints(self) -> None:
        result = schema_of([1, 2, 3])
        assert result == "root: list[int]"

    def test_tuple_of_ints(self) -> None:
        result = schema_of((1, 2, 3))
        assert result == "root: tuple[int]"

    def test_set_of_ints(self) -> None:
        result = schema_of({1, 2, 3})
        assert result == "root: set[int]"

    def test_list_of_dicts(self) -> None:
        data = [
            {"action": "login", "timestamp": 167890123},
            {"action": "login", "timestamp": 167890123},
            {"action": "login", "result": None},
            {"action": "login", "result": 1, "number": [1, 2, 3]},
        ]
        result = schema_of(data)
        expected = textwrap.dedent("""\
            root: list[dict]
            ├── action: str
            ├── timestamp: int
            ├── result: ['NoneType', 'int']
            └── number: list[int]""")
        assert result == expected

    def test_empty_list(self) -> None:
        result = schema_of([])
        assert result == "root: list"

    def test_empty_tuple(self) -> None:
        result = schema_of(())
        assert result == "root: tuple"

    def test_frozenset_of_strings(self) -> None:
        result = schema_of(frozenset({"a", "b"}))
        assert result == "root: frozenset[str]"

    def test_tuple_of_dicts(self) -> None:
        data = ({"x": 1}, {"x": 2, "y": "hello"})
        result = schema_of(data)
        assert "root: tuple[dict]" in result
        assert "x: int" in result
        assert "y: str" in result


# ── file path support ──────────────────────────────────────────────


class TestFilePath:
    """Test that preview() and schema_of() accept file paths."""

    @pytest.fixture(scope="class")
    def data_dir(self) -> Path:
        return Path(__file__).parent / "data"

    def test_path_object(self, data_dir: Path) -> None:
        """Path objects are loaded and parsed as JSON."""
        path = data_dir / "dict.json"
        result = schema_of(path)
        assert "id: int" in result
        assert "squadHome: dict" in result

    def test_path_string(self, data_dir: Path) -> None:
        """String paths to existing files are loaded."""
        path_str = str(data_dir / "dict.json")
        result = schema_of(path_str)
        assert "id: int" in result
        assert "squadHome: dict" in result

    def test_path_object_list_json(self, data_dir: Path) -> None:
        """Path to a JSON file containing a list."""
        path = data_dir / "list.json"
        result = schema_of(path)
        assert "root: list[dict]" in result
        assert "team_id: int" in result

    def test_preview_with_path(
        self,
        data_dir: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """preview() works with Path objects."""
        path = data_dir / "dict.json"
        preview(path)
        captured = capsys.readouterr()
        assert "id: int" in captured.out

    def test_preview_with_string_path(
        self,
        data_dir: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """preview() works with string paths."""
        path_str = str(data_dir / "dict.json")
        preview(path_str)
        captured = capsys.readouterr()
        assert "id: int" in captured.out

    def test_path_not_found(self) -> None:
        """FileNotFoundError for non-existent path."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            schema_of(Path("/nonexistent/file.json"))

    def test_unsupported_extension(self, tmp_path: Path) -> None:
        """ValueError for non-.json files."""
        txt = tmp_path / "data.txt"
        txt.write_text("hello")
        with pytest.raises(ValueError, match="Unsupported file"):
            schema_of(txt)

    def test_string_not_a_path(self) -> None:
        """Plain strings that aren't files stay as data."""
        result = schema_of("hello")
        assert result == "root: str"

    def test_relative_string_path(self, data_dir: Path) -> None:
        """Relative string paths work when they resolve."""
        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(data_dir.parent.parent)
            result = schema_of("tests/data/dict.json")
            assert "id: int" in result
        finally:
            os.chdir(old_cwd)
