"""Convention-based pytest target discovery and generation."""

from __future__ import annotations

import hashlib
import keyword
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


ROOT_SUITE_ID = "__root__"
GENERATED_DIR_NAME = ".pytest-dsl-generated"
GENERATED_FILE_NAME = "test_dsl_cases.py"
HOOK_FILENAMES = {"setup.dsl", "setup.auto", "teardown.dsl", "teardown.auto"}
DSL_SUFFIXES = {".dsl", ".auto"}
PYTEST_FILE_RE = re.compile(r"^(test_.*|.*_test)\.py$")
HELPER_DIR_NAMES = {"_support", "_data"}


@dataclass
class ConventionSuite:
    id: str
    name: str
    root_path: Path
    dsl_case_files: list[Path] = field(default_factory=list)
    python_test_files: list[Path] = field(default_factory=list)
    generated_files: list[Path] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)

    def to_dict(self, project_root: Path) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "rootPath": _relpath(self.root_path, project_root),
            "dslCaseCount": len(self.dsl_case_files),
            "pythonTestCount": len(self.python_test_files),
            "generatedFiles": [_relpath(path, project_root) for path in sorted(self.generated_files)],
            "pythonTestFiles": [_relpath(path, project_root) for path in sorted(self.python_test_files)],
            "diagnostics": list(self.diagnostics),
        }


def discover_convention_suites(project_root: str | Path) -> list[dict]:
    """Discover convention suites under ``<project_root>/tests``."""
    root = Path(project_root).resolve()
    suites = _discover_suite_models(root)
    return [suite.to_dict(root) for suite in suites]


def generate_pytest_files(
    project_root: str | Path,
    selected_suite_ids: Iterable[str] | None = None,
) -> list[str]:
    """Deprecated compatibility shim; native collection no longer generates files."""
    return []


def build_pytest_targets(
    project_root: str | Path,
    selected_suite_ids: Iterable[str] | None = None,
) -> list[str]:
    """Return native pytest directory targets for selected suites."""
    root = Path(project_root).resolve()
    selected = list(selected_suite_ids or [])
    tests_root = root / "tests"
    if not tests_root.exists() or not tests_root.is_dir():
        return []
    if not selected or "all" in selected:
        return [_relpath(tests_root, root)]

    suites = _selected_suite_models(root, selected_suite_ids)
    targets = _compact_target_paths([suite.root_path for suite in suites])
    return [_relpath(path, root) for path in targets]


def make_test_function_name(case_path: Path, used_names: set[str]) -> str:
    """Create an ASCII-safe deterministic pytest function name."""
    stem = re.sub(r"[^0-9a-zA-Z_]+", "_", case_path.stem).strip("_").lower()
    stem = re.sub(r"_+", "_", stem) or "case"
    if stem[0].isdigit() or keyword.iskeyword(stem):
        stem = f"case_{stem}"

    name = f"test_{stem}"
    if name not in used_names:
        used_names.add(name)
        return name

    digest = hashlib.sha1(str(case_path).encode("utf-8")).hexdigest()[:8]
    name_with_hash = f"{name}_{digest}"
    used_names.add(name_with_hash)
    return name_with_hash


def _discover_suite_models(project_root: Path) -> list[ConventionSuite]:
    tests_root = project_root / "tests"
    if not tests_root.exists() or not tests_root.is_dir():
        return []

    suites: dict[str, ConventionSuite] = {}

    for file_path in sorted(tests_root.rglob("*")):
        if not file_path.is_file() or _is_generated_path(file_path) or _is_helper_path(file_path):
            continue

        relative_to_tests = file_path.relative_to(tests_root)
        suite_id = _suite_id_for(relative_to_tests)
        suite = suites.setdefault(
            suite_id,
            ConventionSuite(
                id=suite_id,
                name=suite_id,
                root_path=tests_root if suite_id == ROOT_SUITE_ID else tests_root / suite_id,
            ),
        )

        if _is_dsl_case_file(file_path):
            suite.dsl_case_files.append(file_path)
        elif _is_pytest_file(file_path):
            suite.python_test_files.append(file_path)

    return [
        suites[suite_id]
        for suite_id in sorted(suites, key=lambda value: (value != ROOT_SUITE_ID, value))
        if suites[suite_id].dsl_case_files or suites[suite_id].python_test_files
    ]


def _selected_suite_models(
    project_root: Path,
    selected_suite_ids: Iterable[str] | None,
) -> list[ConventionSuite]:
    suites = _discover_suite_models(project_root)
    selected = list(selected_suite_ids or [])
    if not selected:
        return suites
    if "all" in selected:
        selected_ids = {suite.id for suite in suites}
    else:
        selected_ids = set(selected)
    return [suite for suite in suites if suite.id in selected_ids]


def _render_generated_file(case_dir: Path, case_files: list[Path], suite_id: str) -> str:
    used_names: set[str] = set()
    test_blocks: list[str] = []

    for case_file in sorted(case_files):
        test_name = make_test_function_name(case_file.relative_to(case_dir), used_names)
        case_name = case_file.name
        test_blocks.append(
            "\n".join(
                [
                    "@pytest.mark.pytest_dsl_case(",
                    f'    case_path=str(_CASE_DIR / "{case_name}"),',
                    f'    suite_id="{suite_id}",',
                    "    hook_root=str(_TESTS_ROOT),",
                    ")",
                    f"def {test_name}():",
                    f'    execute_dsl_file(str(_CASE_DIR / "{case_name}"))',
                    "",
                ]
            )
        )

    parents_to_tests_root = len(case_dir.relative_to(_find_tests_root(case_dir)).parts) + 1
    return "\n".join(
        [
            "from pathlib import Path",
            "",
            "import pytest",
            "",
            "from pytest_dsl.core.dsl_executor_utils import execute_dsl_file",
            "",
            "",
            "_CASE_DIR = Path(__file__).resolve().parents[1]",
            f"_TESTS_ROOT = Path(__file__).resolve().parents[{parents_to_tests_root}]",
            "",
            "",
            "\n".join(test_blocks).rstrip(),
            "",
        ]
    )


def _suite_id_for(relative_to_tests: Path) -> str:
    parts = relative_to_tests.parts
    return ROOT_SUITE_ID if len(parts) == 1 else Path(*parts[:-1]).as_posix()


def _compact_target_paths(paths: Iterable[Path]) -> list[Path]:
    compacted: list[Path] = []
    for path in sorted({item.resolve() for item in paths}, key=lambda item: (len(item.parts), item.as_posix())):
        if any(path == selected or path.is_relative_to(selected) for selected in compacted):
            continue
        compacted.append(path)
    return compacted


def _is_dsl_case_file(file_path: Path) -> bool:
    return file_path.suffix in DSL_SUFFIXES and file_path.name not in HOOK_FILENAMES


def _is_pytest_file(file_path: Path) -> bool:
    return PYTEST_FILE_RE.match(file_path.name) is not None


def _is_generated_path(file_path: Path) -> bool:
    return GENERATED_DIR_NAME in file_path.parts


def _is_helper_path(file_path: Path) -> bool:
    return any(part in HELPER_DIR_NAMES for part in file_path.parts)


def _find_tests_root(path: Path) -> Path:
    for parent in [path, *path.parents]:
        if parent.name == "tests":
            return parent
    raise ValueError(f"Path is not under a tests directory: {path}")


def _relpath(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root).as_posix()
