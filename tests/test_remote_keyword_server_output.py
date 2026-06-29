from pytest_dsl.remote.keyword_server import RemoteKeywordServer, _load_extensions


def test_remote_keyword_server_registration_is_quiet_on_success(
    monkeypatch,
    capsys,
):
    import pytest_dsl.core.plugin_discovery as plugin_discovery

    monkeypatch.setattr(plugin_discovery, "load_all_plugins", lambda: None)
    monkeypatch.setattr(plugin_discovery, "scan_local_keywords", lambda: None)

    RemoteKeywordServer()

    assert capsys.readouterr().out == ""


def test_remote_keyword_server_registration_logs_when_verbose(
    monkeypatch,
    capsys,
):
    import pytest_dsl.core.plugin_discovery as plugin_discovery

    monkeypatch.setenv("PYTEST_DSL_VERBOSE", "1")
    monkeypatch.setattr(plugin_discovery, "load_all_plugins", lambda: None)
    monkeypatch.setattr(plugin_discovery, "scan_local_keywords", lambda: None)

    RemoteKeywordServer()

    output = capsys.readouterr().out
    assert "正在加载内置关键字" in output
    assert "关键字加载完成，可用关键字数量" in output


def test_load_extensions_is_quiet_on_success(tmp_path, capsys):
    extension_file = tmp_path / "quiet_extension.py"
    extension_file.write_text(
        "print('扩展模块成功加载输出')\n",
        encoding="utf-8",
    )

    _load_extensions(str(extension_file))

    assert capsys.readouterr().out == ""


def test_load_extensions_logs_when_verbose(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("PYTEST_DSL_VERBOSE", "1")
    extension_file = tmp_path / "verbose_extension.py"
    extension_file.write_text(
        "print('扩展模块详细加载输出')\n",
        encoding="utf-8",
    )

    _load_extensions(str(extension_file))

    output = capsys.readouterr().out
    assert "扩展模块详细加载输出" in output
    assert f"已加载扩展模块: {extension_file}" in output
