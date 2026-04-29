import importlib
import sys

from pytest_dsl.core.keyword_manager import keyword_manager
from pytest_dsl.core.plugin_discovery import scan_local_keywords


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
