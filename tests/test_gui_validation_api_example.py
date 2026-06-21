from __future__ import annotations

import importlib.util
import subprocess
import sys
import threading
from contextlib import contextmanager
from pathlib import Path

import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_ROOT = REPO_ROOT / "examples" / "gui_validation"
SERVER_PATH = EXAMPLE_ROOT / "tools" / "mock_api_server.py"


def load_mock_api_module():
    spec = importlib.util.spec_from_file_location(
        "gui_validation_mock_api", SERVER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def running_mock_api():
    module = load_mock_api_module()
    server = module.create_server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield f"http://{host}:{port}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_mock_api_supports_the_documented_user_session_flow():
    with running_mock_api() as base_url:
        user_response = requests.get(f"{base_url}api/users/1001", timeout=3)
        assert user_response.status_code == 200
        assert user_response.json()["data"] == {
            "id": 1001,
            "username": "api_demo",
            "role": "tester",
        }

        session_response = requests.post(
            f"{base_url}api/sessions",
            json={"username": "api_demo", "password": "pytest-dsl"},
            timeout=3,
        )
        assert session_response.status_code == 201
        assert (
            session_response.json()["data"]["access_token"]
            == "demo-token-1001"
        )

        profile_response = requests.get(
            f"{base_url}api/users/1001/profile",
            headers={"Authorization": "Bearer demo-token-1001"},
            timeout=3,
        )
        assert profile_response.status_code == 200
        assert profile_response.json()["data"]["active"] is True


def test_mock_api_rejects_a_profile_request_without_the_captured_token():
    with running_mock_api() as base_url:
        response = requests.get(f"{base_url}api/users/1001/profile", timeout=3)

    assert response.status_code == 401
    assert response.json() == {
        "code": 40101,
        "message": "missing or invalid token",
    }


def test_api_quickstart_runs_through_the_real_pytest_dsl_cli(tmp_path):
    with running_mock_api() as base_url:
        config_path = tmp_path / "api.yaml"
        config_path.write_text(
            "\n".join(
                [
                    "http_clients:",
                    "  local_api:",
                    f"    base_url: {base_url}",
                    "    timeout: 5",
                    "    verify_ssl: false",
                    "api_demo:",
                    "  user_id: 1001",
                    "  username: api_demo",
                    "  password: pytest-dsl",
                ]
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest_dsl.cli",
                "run",
                "tests/api_quickstart.dsl",
                "--yaml-vars",
                str(config_path),
            ],
            cwd=EXAMPLE_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )

    assert result.returncode == 0, (
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "接口测试核心链路验证完成" in result.stdout
