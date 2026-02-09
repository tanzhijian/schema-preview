from __future__ import annotations

import json
import textwrap
import warnings

import pytest

from schema_preview import preview
from schema_preview._schema import infer_schema

# ── basic rendering ────────────────────────────────────────────────


class TestBasicPreview:
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
        assert preview(my_dict, print_result=False) == expected

    def test_flat_dict(self) -> None:
        data = {"a": 1, "b": "hello", "c": 3.14}
        result = preview(data, print_result=False)
        assert "a: int" in result
        assert "b: str" in result
        assert "c: float" in result

    def test_empty_dict(self) -> None:
        result = preview({}, print_result=False)
        assert result == "root"

    def test_empty_list_value(self) -> None:
        result = preview({"items": []}, print_result=False)
        assert "items: list" in result


# ── list type inference ────────────────────────────────────────────


class TestListInference:
    def test_homogeneous_list(self) -> None:
        result = preview({"x": [1, 2, 3]}, print_result=False)
        assert "x: list[int]" in result

    def test_list_of_strings(self) -> None:
        result = preview({"tags": ["a", "b"]}, print_result=False)
        assert "tags: list[str]" in result

    def test_list_of_dicts(self) -> None:
        data = {"rows": [{"id": 1}, {"id": 2}]}
        result = preview(data, print_result=False)
        assert "rows: list[dict]" in result
        assert "id: int" in result

    def test_mixed_types_warning(self) -> None:
        data = {"vals": [1, "two", 3]}
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = preview(data, print_result=False)
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
        result = preview(data, print_result=False)
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
        result = preview(data, print_result=False)
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
        result = preview(data, max_items=5, print_result=False)
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
        result = preview(data, print_result=False)
        assert "level1: dict" in result
        assert "level2: dict" in result
        assert "level3: str" in result


# ── CLI ───────────────────────────────────────────────────────────


class TestCLI:
    def test_file_argument(self, tmp_path: pytest.TempPathFactory) -> None:
        import subprocess

        p = tmp_path / "test.json"  # type: ignore[operator]
        p.write_text(json.dumps({"name": "test", "value": 42}))
        result = subprocess.run(
            ["uv", "run", "schema-preview", str(p)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "name: str" in result.stdout
        assert "value: int" in result.stdout

    def test_stdin(self) -> None:
        import subprocess

        data = json.dumps({"x": [1, 2, 3]})
        result = subprocess.run(
            ["uv", "run", "schema-preview"],
            input=data,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "x: list[int]" in result.stdout

    def test_max_items_flag(self, tmp_path: pytest.TempPathFactory) -> None:
        import subprocess

        p = tmp_path / "test.json"  # type: ignore[operator]
        p.write_text(json.dumps({"items": list(range(100))}))
        result = subprocess.run(
            ["uv", "run", "schema-preview", str(p), "--max-items", "5"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "items: list[int]" in result.stdout


# ── edge cases ────────────────────────────────────────────────────


class TestEdgeCases:
    def test_none_value(self) -> None:
        result = preview({"x": None}, print_result=False)
        assert "x: NoneType" in result

    def test_bool_value(self) -> None:
        result = preview({"flag": True}, print_result=False)
        assert "flag: bool" in result

    def test_nested_list_of_lists(self) -> None:
        data = {"matrix": [[1, 2], [3, 4]]}
        result = preview(data, print_result=False)
        assert "matrix: list[list]" in result

    def test_list_with_nested_dicts_different_depths(self) -> None:
        data = {
            "items": [
                {"a": {"b": 1}},
                {"a": {"b": 2, "c": 3}},
            ]
        }
        result = preview(data, print_result=False)
        assert "a: dict" in result
        assert "b: int" in result
        assert "c: int" in result
