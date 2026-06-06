from pathlib import Path
from types import SimpleNamespace

import tests.conftest as repo_conftest


def _dsl_item(filename):
    return SimpleNamespace(path=Path(__file__).with_name(filename))


def test_auth_dsl_setup_loads_simple_config_and_starts_mock_server(monkeypatch):
    from pytest_dsl.core.yaml_vars import yaml_vars

    server_starts = []
    monkeypatch.setattr(
        repo_conftest,
        "_ensure_auth_mock_server",
        lambda: server_starts.append("started"),
    )

    original_variables = yaml_vars._variables.copy()
    original_loaded_files = yaml_vars._loaded_files.copy()
    item = _dsl_item("simple_auth_test.dsl")

    try:
        repo_conftest.pytest_runtest_setup(item)

        http_clients = yaml_vars.get_variable("http_clients")
        assert server_starts == ["started"]
        assert http_clients["basic_auth_valid"]["auth"]["username"] == "admin"
        assert http_clients["basic_auth_valid"]["auth"]["password"] == "admin123"
    finally:
        repo_conftest.pytest_runtest_teardown(item)
        yaml_vars._variables = original_variables
        yaml_vars._loaded_files = original_loaded_files


def test_null_literal_dsl_setup_installs_and_restores_fake_http_request():
    from pytest_dsl.keywords import http_keywords

    original_http_request = http_keywords.HTTPRequest
    item = _dsl_item("test_http_null_literal_request.dsl")

    try:
        repo_conftest.pytest_runtest_setup(item)
        fake_request = http_keywords.HTTPRequest(
            {"request": {"json": {"meta": {"caller": None}}}},
            "default",
            None,
        )

        response = fake_request.execute()
        assert response.status_code == 200
        assert fake_request.captured_values == {"caller": None}
        assert fake_request.process_asserts() == ([{"result": True}], [])
    finally:
        repo_conftest.pytest_runtest_teardown(item)

    assert http_keywords.HTTPRequest is original_http_request
