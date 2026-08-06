import importlib
import sys
import types
from pathlib import Path

from pytest_dsl.core.keyword_manager import keyword_manager
from pytest_dsl.core.plugin_discovery import load_plugin_keywords, scan_local_keywords


def test_scan_local_keywords_supports_project_package_imports(
    tmp_path,
    monkeypatch,
):
    original_sys_path = sys.path.copy()
    original_keywords = keyword_manager._keywords.copy()
    module_prefixes = ("keywords", "business")
    original_modules = {
        name: module
        for name, module in sys.modules.items()
        if name in module_prefixes or name.startswith(
            tuple(f"{prefix}." for prefix in module_prefixes)
        )
    }

    business_dir = tmp_path / "business"
    keywords_dir = tmp_path / "keywords"
    business_dir.mkdir()
    keywords_dir.mkdir()
    (business_dir / "__init__.py").write_text("", encoding="utf-8")
    (business_dir / "service.py").write_text(
        "def helper():\n    return 'project helper'\n",
        encoding="utf-8",
    )
    (keywords_dir / "__init__.py").write_text("", encoding="utf-8")
    (keywords_dir / "project_keywords.py").write_text(
        "\n".join(
            [
                "from business.service import helper",
                "from pytest_dsl.core.keyword_manager import keyword_manager",
                "",
                "@keyword_manager.register('项目包导入关键字', [])",
                "def project_package_keyword():",
                "    return helper()",
                "",
            ]
        ),
        encoding="utf-8",
    )

    try:
        for name in list(sys.modules):
            if name in module_prefixes or name.startswith(
                tuple(f"{prefix}." for prefix in module_prefixes)
            ):
                sys.modules.pop(name)

        monkeypatch.chdir(tmp_path)
        project_root = Path.cwd()
        sys.path[:] = [
            path
            for path in sys.path
            if path not in {str(project_root), str(project_root / "keywords"), ""}
        ]
        assert str(project_root) not in sys.path
        assert str(project_root / "keywords") not in sys.path
        importlib.invalidate_caches()

        scan_local_keywords()

        assert keyword_manager.execute("项目包导入关键字") == "project helper"
        assert sys.path.index(str(project_root)) < sys.path.index(
            str(project_root / "keywords")
        )
    finally:
        sys.path[:] = original_sys_path
        keyword_manager._keywords.clear()
        keyword_manager._keywords.update(original_keywords)
        for name in list(sys.modules):
            if name in module_prefixes or name.startswith(
                tuple(f"{prefix}." for prefix in module_prefixes)
            ):
                sys.modules.pop(name)
        sys.modules.update(original_modules)


def test_scan_local_keywords_keeps_sibling_module_import_compatibility(
    tmp_path,
    monkeypatch,
):
    original_sys_path = sys.path.copy()
    original_keywords = keyword_manager._keywords.copy()
    module_names = {"keywords", "legacy_keyword_helper"}
    original_modules = {
        name: module
        for name, module in sys.modules.items()
        if name in module_names or name.startswith("keywords.")
    }

    keywords_dir = tmp_path / "keywords"
    keywords_dir.mkdir()
    (keywords_dir / "__init__.py").write_text("", encoding="utf-8")
    (keywords_dir / "legacy_keyword_helper.py").write_text(
        "def helper():\n    return 'legacy helper'\n",
        encoding="utf-8",
    )
    (keywords_dir / "legacy_keywords.py").write_text(
        "\n".join(
            [
                "from legacy_keyword_helper import helper",
                "from pytest_dsl.core.keyword_manager import keyword_manager",
                "",
                "@keyword_manager.register('旧式同级模块导入关键字', [])",
                "def legacy_sibling_keyword():",
                "    return helper()",
                "",
            ]
        ),
        encoding="utf-8",
    )

    try:
        for name in list(sys.modules):
            if name in module_names or name.startswith("keywords."):
                sys.modules.pop(name)

        monkeypatch.chdir(tmp_path)
        project_root = Path.cwd()
        sys.path[:] = [
            path
            for path in sys.path
            if path not in {str(project_root), str(project_root / "keywords"), ""}
        ]
        assert str(project_root) not in sys.path
        assert str(project_root / "keywords") not in sys.path
        importlib.invalidate_caches()

        scan_local_keywords()

        assert keyword_manager.execute("旧式同级模块导入关键字") == "legacy helper"
    finally:
        sys.path[:] = original_sys_path
        keyword_manager._keywords.clear()
        keyword_manager._keywords.update(original_keywords)
        for name in list(sys.modules):
            if name in module_names or name.startswith("keywords."):
                sys.modules.pop(name)
        sys.modules.update(original_modules)


def test_scan_local_keywords_continues_after_subpackage_import_error(
    tmp_path,
    monkeypatch,
    capsys,
):
    original_keywords = keyword_manager._keywords.copy()
    original_modules = {
        name: module
        for name, module in sys.modules.items()
        if name == "keywords" or name.startswith("keywords.")
    }

    keywords_dir = tmp_path / "keywords"
    broken_dir = keywords_dir / "broken"
    broken_dir.mkdir(parents=True)
    (keywords_dir / "__init__.py").write_text("", encoding="utf-8")
    (broken_dir / "__init__.py").write_text(
        "raise RuntimeError('broken package init')\n",
        encoding="utf-8",
    )
    (broken_dir / "later_keywords.py").write_text(
        "\n".join(
            [
                "from pytest_dsl.core.keyword_manager import keyword_manager",
                "",
                "@keyword_manager.register('子包失败后仍加载', [])",
                "def later_keyword():",
                "    return 'ok'",
                "",
            ]
        ),
        encoding="utf-8",
    )

    try:
        for name in list(sys.modules):
            if name == "keywords" or name.startswith("keywords."):
                sys.modules.pop(name)

        monkeypatch.chdir(tmp_path)
        monkeypatch.syspath_prepend(str(tmp_path))
        importlib.invalidate_caches()

        scan_local_keywords()

        assert "子包失败后仍加载" in keyword_manager._keywords
        assert "扫描项目关键字时出错" not in capsys.readouterr().out
    finally:
        keyword_manager._keywords.clear()
        keyword_manager._keywords.update(original_keywords)
        for name in list(sys.modules):
            if name == "keywords" or name.startswith("keywords."):
                sys.modules.pop(name)
        sys.modules.update(original_modules)


def test_load_plugin_keywords_suppresses_success_stdout(capsys):
    plugin_name = "pytest_dsl_noisy_success_plugin"
    keyword_name = "插件成功静默关键字"
    plugin = types.ModuleType(plugin_name)

    def register_keywords(manager):
        print("插件成功注册输出")

        @manager.register(keyword_name, [])
        def plugin_keyword():
            return "ok"

    plugin.register_keywords = register_keywords
    original_module = sys.modules.get(plugin_name)
    original_keywords = keyword_manager._keywords.copy()

    try:
        sys.modules[plugin_name] = plugin

        load_plugin_keywords(plugin_name)

        assert keyword_name in keyword_manager._keywords
        assert capsys.readouterr().out == ""
    finally:
        if original_module is None:
            sys.modules.pop(plugin_name, None)
        else:
            sys.modules[plugin_name] = original_module
        keyword_manager._keywords.clear()
        keyword_manager._keywords.update(original_keywords)


def test_load_plugin_keywords_keeps_success_stdout_when_verbose(
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("PYTEST_DSL_VERBOSE", "1")
    plugin_name = "pytest_dsl_verbose_success_plugin"
    keyword_name = "插件详细注册关键字"
    plugin = types.ModuleType(plugin_name)

    def register_keywords(manager):
        print("插件详细注册输出")

        @manager.register(keyword_name, [])
        def plugin_keyword():
            return "ok"

    plugin.register_keywords = register_keywords
    original_module = sys.modules.get(plugin_name)
    original_keywords = keyword_manager._keywords.copy()

    try:
        sys.modules[plugin_name] = plugin

        load_plugin_keywords(plugin_name)

        assert keyword_name in keyword_manager._keywords
        assert "插件详细注册输出" in capsys.readouterr().out
    finally:
        if original_module is None:
            sys.modules.pop(plugin_name, None)
        else:
            sys.modules[plugin_name] = original_module
        keyword_manager._keywords.clear()
        keyword_manager._keywords.update(original_keywords)
