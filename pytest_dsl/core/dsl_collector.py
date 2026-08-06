"""pytest native collector for .dsl and .auto case files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import allure
import pytest

from pytest_dsl.core.auto_decorator import resolve_case_data_source
from pytest_dsl.core.dsl_executor import DSLExecutor
from pytest_dsl.core.dsl_executor_utils import (
    execute_dsl_file,
    extract_metadata_from_ast,
)
from pytest_dsl.core.lexer import get_lexer
from pytest_dsl.core.hook_files import is_hook_file
from pytest_dsl.core.parser import (
    format_parse_errors,
    parse_with_error_handling,
)


DSL_SUFFIXES = {".dsl", ".auto"}


def is_dsl_case_file(path: Path) -> bool:
    """Return True for executable DSL case files."""
    return path.suffix in DSL_SUFFIXES and not is_hook_file(path)


def find_tests_root(case_path: Path) -> Path:
    """Find the nearest tests directory, or fall back to the case directory."""
    resolved = Path(case_path).resolve()
    for parent in [resolved.parent, *resolved.parents]:
        if parent.name == "tests":
            return parent
    return resolved.parent


def suite_id_for(tests_root: Path, case_path: Path) -> str:
    """Return stable suite metadata for a DSL case path."""
    root = Path(tests_root).resolve()
    case = Path(case_path).resolve()
    rel_parent = case.parent.relative_to(root)
    if not rel_parent.parts:
        return "__root__"
    return rel_parent.as_posix()


def apply_allure_labels(tests_root: Path, case_path: Path) -> None:
    """Apply path-based Allure labels for native DSL items."""
    root = Path(tests_root).resolve()
    case = Path(case_path).resolve()
    rel = case.relative_to(root)
    directory_parts = rel.parent.parts
    project_name = root.parent.name

    allure.dynamic.parent_suite(project_name)
    allure.dynamic.suite(directory_parts[0] if directory_parts else "__root__")
    if len(directory_parts) > 1:
        allure.dynamic.sub_suite("/".join(directory_parts[1:]))
    allure.dynamic.title(case.stem)
    case_label = f"{root.name}/{rel.as_posix()}" if root.name == "tests" else rel.as_posix()
    allure.dynamic.label("case_path", case_label)


class DslFile(pytest.File):
    """Collect one DSL case file into one or more pytest items."""

    def collect(self):
        case_path = Path(self.path).resolve()
        tests_root = find_tests_root(case_path)
        case_name = case_path.stem

        try:
            ast = load_case_ast(case_path)
            data_cases = load_data_cases(case_path, ast=ast)
            tags = extract_tags_from_ast(ast)
        except Exception as exc:
            raise self.CollectError(str(exc)) from exc

        if data_cases:
            for index, test_data in data_cases:
                yield DslItem.from_parent(
                    self,
                    name=f"{case_name}[data-{index}]",
                    case_path=case_path,
                    tests_root=tests_root,
                    test_data=test_data,
                    data_index=index,
                    tags=tags,
                )
            return

        yield DslItem.from_parent(
            self,
            name=case_name,
            case_path=case_path,
            tests_root=tests_root,
            tags=tags,
        )


class DslItem(pytest.Item):
    """pytest item that executes a DSL case file."""

    def __init__(
        self,
        *,
        case_path: Path,
        tests_root: Path,
        test_data: dict[str, Any] | None = None,
        data_index: int | None = None,
        tags: list[str] | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.case_path = Path(case_path).resolve()
        self.tests_root = Path(tests_root).resolve()
        self.test_data = test_data
        self.data_index = data_index
        self.tags = tuple(dict.fromkeys(tags or []))
        self._pytest_dsl_case = {
            "case_path": str(self.case_path),
            "hook_root": str(self.tests_root),
            "suite_id": suite_id_for(self.tests_root, self.case_path),
            "tags": list(self.tags),
        }
        registered_tags = getattr(self.config, "_pytest_dsl_registered_tags", set())
        for tag in self.tags:
            if tag not in registered_tags:
                self.config.addinivalue_line("markers", f"{tag}: generated from DSL @tags")
                registered_tags.add(tag)
            self.add_marker(tag)
        self.config._pytest_dsl_registered_tags = registered_tags
        self._obj = self._make_function_proxy()

    @property
    def obj(self):
        return self._obj

    @property
    def function(self):
        """Compatibility alias used by pytest plugins for Function items."""
        return self.obj

    def _make_function_proxy(self):
        def pytest_dsl_case_function():
            return self.runtest()

        pytest_dsl_case_function.__name__ = self.name
        pytest_dsl_case_function.__qualname__ = self.name
        pytest_dsl_case_function.__doc__ = f"pytest-dsl case: {self.case_path}"
        pytest_dsl_case_function.case_path = str(self.case_path)
        pytest_dsl_case_function.dsl_id = str(self.case_path)
        pytest_dsl_case_function.pytest_dsl_case = dict(self._pytest_dsl_case)
        if self.data_index is not None:
            pytest_dsl_case_function.data_index = self.data_index
        return pytest_dsl_case_function

    def runtest(self):
        apply_allure_labels(self.tests_root, self.case_path)
        executor = DSLExecutor(enable_hooks=True, enable_tracking=True)
        if self.test_data is not None:
            executor.set_current_data(self.test_data)
        execute_dsl_file(str(self.case_path), executor)

    def reportinfo(self):
        return self.case_path, 0, self.name


def load_case_ast(case_path: Path):
    """Parse one DSL case for collection-time metadata."""
    content = case_path.read_text(encoding="utf-8")
    ast, errors = parse_with_error_handling(content, lexer=get_lexer())
    if errors:
        message = format_parse_errors(errors, file_path=str(case_path))
        raise ValueError(f"DSL解析失败:\n{message}")
    if ast is None:
        raise ValueError(f"DSL解析失败: {case_path}")
    return ast


def extract_tags_from_ast(ast) -> list[str]:
    """Extract ordered, non-empty @tags values from a parsed DSL AST."""
    for child in ast.children:
        if child.type != "Metadata":
            continue
        for item in child.children:
            if item.type == "@tags":
                return [str(tag.value) for tag in item.value if str(tag.value)]
    return []


def load_data_cases(case_path: Path, ast=None) -> list[tuple[int, dict[str, Any]]]:
    """Load @data rows for collection without executing the DSL body."""
    if ast is None:
        ast = load_case_ast(case_path)

    data_source, _test_title = extract_metadata_from_ast(ast)
    if not data_source:
        return []

    resolved_source = resolve_case_data_source(case_path, data_source)
    rows = DSLExecutor(enable_hooks=False, enable_tracking=False)._load_test_data(resolved_source)
    return list(enumerate(rows))
