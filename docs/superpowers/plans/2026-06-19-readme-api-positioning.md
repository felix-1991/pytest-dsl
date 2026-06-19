# README API Positioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the oversized root README with an evidence-backed API-testing product page, add a self-contained `[HTTP请求]` Studio example, and publish real Studio/Allure screenshots.

**Architecture:** Promote `examples/gui_validation` from an ignored local scratch project to a tracked runnable showcase while keeping generated files ignored. A standard-library mock HTTP server supplies deterministic API responses; one DSL file exercises the existing HTTP keyword, captures, assertions, variable flow, and Allure output. The root README links that verified flow to three screenshots and delegates detailed reference material to the existing `docs/guide/` pages.

**Tech Stack:** Python 3.9+, pytest, pytest-dsl CLI/plugin, stdlib `ThreadingHTTPServer`, requests, Allure, Electron 30, Node test runner, Markdown.

---

## File map

- Modify `.gitignore`: track the GUI validation source project while continuing to ignore runtime metadata, generated pytest wrappers, Allure output, caches, and OS files.
- Create `examples/gui_validation/tools/mock_api_server.py`: deterministic local API server used by CLI, Studio, and tests.
- Create `examples/gui_validation/config/api.yaml`: local client and test-account configuration.
- Create `examples/gui_validation/tests/api_quickstart.dsl`: the canonical API example shown in the README and screenshots.
- Modify `examples/gui_validation/README.md`: document the actual API mock, CLI, pytest/Allure, and Studio workflows.
- Create `tests/test_gui_validation_api_example.py`: endpoint and end-to-end DSL regression tests.
- Create `tests/test_readme_product_page.py`: product-page structure and local-link/image integrity checks.
- Rewrite `README.md`: concise API-first product page grounded in current implementation.
- Create `docs/images/readme/studio-api-editor.png`: real Studio editor screenshot.
- Create `docs/images/readme/studio-api-run.png`: real Studio successful-run screenshot.
- Create `docs/images/readme/allure-api-report.png`: real expanded Allure report screenshot.

### Task 1: Promote the validation project and add the deterministic mock API

**Files:**
- Modify: `.gitignore`
- Create: `tests/test_gui_validation_api_example.py`
- Create: `examples/gui_validation/tools/mock_api_server.py`

- [ ] **Step 1: Write the failing mock API behavior test**

Create `tests/test_gui_validation_api_example.py` with a path-based module loader, a server context manager, and this behavior:

```python
from __future__ import annotations

import importlib.util
import json
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
    spec = importlib.util.spec_from_file_location("gui_validation_mock_api", SERVER_PATH)
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
        assert session_response.json()["data"]["access_token"] == "demo-token-1001"

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
    assert response.json() == {"code": 40101, "message": "missing or invalid token"}
```

- [ ] **Step 2: Run the test to verify RED**

Run: `python -m pytest tests/test_gui_validation_api_example.py -q`

Expected: FAIL because `examples/gui_validation/tools/mock_api_server.py` does not exist.

- [ ] **Step 3: Implement the minimal standard-library API server**

Create `examples/gui_validation/tools/mock_api_server.py` with:

```python
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


USER = {"id": 1001, "username": "api_demo", "role": "tester"}
TOKEN = "demo-token-1001"


class MockAPIHandler(BaseHTTPRequestHandler):
    server_version = "pytest-dsl-mock-api/1.0"

    def log_message(self, format, *args):
        print(f"[mock-api] {self.address_string()} - {format % args}")

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/users/1001":
            self._send_json(200, {"code": 0, "message": "ok", "data": USER})
            return
        if path == "/api/users/1001/profile":
            if self.headers.get("Authorization") != f"Bearer {TOKEN}":
                self._send_json(401, {"code": 40101, "message": "missing or invalid token"})
                return
            self._send_json(
                200,
                {
                    "code": 0,
                    "message": "ok",
                    "data": {"user_id": 1001, "active": True, "plan": "team"},
                },
            )
            return
        self._send_json(404, {"code": 40401, "message": "not found"})

    def do_POST(self):
        if urlparse(self.path).path != "/api/sessions":
            self._send_json(404, {"code": 40401, "message": "not found"})
            return
        payload = self._read_json()
        if payload != {"username": "api_demo", "password": "pytest-dsl"}:
            self._send_json(401, {"code": 40102, "message": "invalid credentials"})
            return
        self._send_json(
            201,
            {
                "code": 0,
                "message": "login successful",
                "data": {"access_token": TOKEN, "user_id": USER["id"]},
            },
        )


def create_server(host="127.0.0.1", port=8765):
    return ThreadingHTTPServer((host, port), MockAPIHandler)


def main():
    parser = argparse.ArgumentParser(description="pytest-dsl GUI validation mock API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = create_server(args.host, args.port)
    print(f"Mock API listening on http://{args.host}:{server.server_address[1]}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Replace the broad ignore rule with generated-file ignores**

Remove `examples/gui_validation/` from `.gitignore` and add:

```gitignore
examples/gui_validation/.pytest-dsl-gui/
examples/gui_validation/**/.pytest-dsl-generated/
examples/gui_validation/allure-results/
examples/gui_validation/allure-report/
examples/gui_validation/**/__pycache__/
examples/gui_validation/**/.DS_Store
```

- [ ] **Step 5: Run the test to verify GREEN**

Run: `python -m pytest tests/test_gui_validation_api_example.py -q`

Expected: `2 passed`.

- [ ] **Step 6: Commit**

```bash
git add .gitignore tests/test_gui_validation_api_example.py examples/gui_validation/tools/mock_api_server.py
git commit -m "test: add deterministic API showcase server"
```

### Task 2: Add and execute the `[HTTP请求]` API showcase

**Files:**
- Modify: `tests/test_gui_validation_api_example.py`
- Create: `examples/gui_validation/config/api.yaml`
- Create: `examples/gui_validation/tests/api_quickstart.dsl`

- [ ] **Step 1: Add a failing end-to-end DSL test**

Append a test that starts the mock on a random port, writes an isolated YAML file, invokes the real CLI, and requires success:

```python
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

    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "接口测试核心链路验证完成" in result.stdout
```

- [ ] **Step 2: Run the test to verify RED**

Run: `python -m pytest tests/test_gui_validation_api_example.py::test_api_quickstart_runs_through_the_real_pytest_dsl_cli -q`

Expected: FAIL because `tests/api_quickstart.dsl` does not exist.

- [ ] **Step 3: Add the real client configuration**

Create `examples/gui_validation/config/api.yaml`:

```yaml
http_clients:
  local_api:
    base_url: http://127.0.0.1:8765/
    timeout: 5
    verify_ssl: false

api_demo:
  user_id: 1001
  username: api_demo
  password: pytest-dsl
```

- [ ] **Step 4: Add the canonical API DSL flow**

Create `examples/gui_validation/tests/api_quickstart.dsl`:

```python
@name: "接口测试核心链路：查询用户、登录并校验账户"
@description: "使用一个内置 HTTP请求 关键字完成请求、捕获、断言和变量传递"
@tags: ["api", "http", "quickstart"]

[HTTP请求], 客户端: "local_api", 配置: '''
    method: GET
    url: /api/users/${api_demo.user_id}
    captures:
        user_id: ["jsonpath", "$.data.id"]
        username: ["jsonpath", "$.data.username"]
        user_role: ["jsonpath", "$.data.role"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.code", "eq", 0]
        - ["jsonpath", "$.data.role", "eq", "tester"]
''', 步骤名称: "查询接口测试用户"

[HTTP请求], 客户端: "local_api", 配置: '''
    method: POST
    url: /api/sessions
    request:
        headers:
            Content-Type: application/json
        json:
            username: "${username}"
            password: "${api_demo.password}"
    captures:
        access_token: ["jsonpath", "$.data.access_token"]
        login_user_id: ["jsonpath", "$.data.user_id"]
    asserts:
        - ["status", "eq", 201]
        - ["jsonpath", "$.code", "eq", 0]
        - ["jsonpath", "$.data.user_id", "eq", ${user_id}]
''', 步骤名称: "登录并捕获访问令牌"

[HTTP请求], 客户端: "local_api", 配置: '''
    method: GET
    url: /api/users/${login_user_id}/profile
    request:
        headers:
            Authorization: "Bearer ${access_token}"
    captures:
        account_active: ["jsonpath", "$.data.active"]
        account_plan: ["jsonpath", "$.data.plan"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.data.active", "eq", true]
        - ["jsonpath", "$.data.plan", "eq", "team"]
''', 步骤名称: "携带令牌查询账户状态"

[断言], 条件: "${account_active} == True", 消息: "账户应该处于启用状态"
[打印], 内容: "接口测试核心链路验证完成：用户=${username}，角色=${user_role}，套餐=${account_plan}"
```

- [ ] **Step 5: Run end-to-end tests to verify GREEN**

Run: `python -m pytest tests/test_gui_validation_api_example.py -q`

Expected: `3 passed`.

- [ ] **Step 6: Generate and inspect real Allure results**

Start the mock server in terminal A:

```bash
python examples/gui_validation/tools/mock_api_server.py
```

Run the native pytest collector in terminal B:

```bash
cd examples/gui_validation
python -m pytest tests/api_quickstart.dsl --yaml-vars config/api.yaml --alluredir allure-results -q
```

Expected: one passing DSL case and JSON/container files in `allure-results/`. Inspect the result JSON for the three custom HTTP step names and HTTP/response/capture/assertion attachments before using those claims in README.

- [ ] **Step 7: Commit**

```bash
git add examples/gui_validation/config/api.yaml examples/gui_validation/tests/api_quickstart.dsl tests/test_gui_validation_api_example.py
git commit -m "feat: add runnable HTTP keyword API showcase"
```

### Task 3: Rewrite the example guide and root product page from verified facts

**Files:**
- Create: `tests/test_readme_product_page.py`
- Modify: `examples/gui_validation/README.md`
- Rewrite: `README.md`

- [ ] **Step 1: Write failing README structure and link-integrity tests**

Create `tests/test_readme_product_page.py`:

```python
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


def test_readme_is_an_api_first_product_page():
    content = README.read_text(encoding="utf-8")
    required = [
        "## 为什么是 pytest-dsl",
        "## 一个关键字开始接口测试",
        "[HTTP请求]",
        "allure.step",
        "## 从 DSL 到可读报告",
        "## Pytest DSL Studio",
        "examples/gui_validation/tests/api_quickstart.dsl",
    ]
    for marker in required:
        assert marker in content
    assert len(content.splitlines()) < 500


def test_readme_references_the_three_verified_screenshots():
    content = README.read_text(encoding="utf-8")
    for name in (
        "studio-api-editor.png",
        "studio-api-run.png",
        "allure-api-report.png",
    ):
        assert f"docs/images/readme/{name}" in content


def test_readme_local_links_and_images_exist():
    content = README.read_text(encoding="utf-8")
    targets = re.findall(r"!?\[[^]]*\]\(([^)]+)\)", content)
    missing = []
    for raw_target in targets:
        target = raw_target.strip().split("#", 1)[0]
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        if not (ROOT / target).resolve().exists():
            missing.append(raw_target)
    assert missing == []
```

- [ ] **Step 2: Run the tests to verify RED**

Run: `python -m pytest tests/test_readme_product_page.py -q`

Expected: FAIL because the current README lacks the new information architecture and screenshots.

- [ ] **Step 3: Rewrite `examples/gui_validation/README.md`**

Document only commands that were executed successfully:

```markdown
# Pytest DSL Studio 验证项目

这个项目同时用于 Studio 演示和 pytest-dsl 回归验证。核心 API 示例只使用内置 `[HTTP请求]` 与 `[断言]`，不需要编写 Python 请求客户端、pytest fixture 或 `allure.step` 包装。

## API 示例

终端 1：

```bash
python tools/mock_api_server.py
```

终端 2：

```bash
pytest-dsl tests/api_quickstart.dsl --yaml-vars config/api.yaml
```

生成 Allure 结果：

```bash
python -m pytest tests/api_quickstart.dsl \
  --yaml-vars config/api.yaml \
  --alluredir allure-results -q
```

继续保留并核对以下现有流程：本地 GUI 用例使用 `config/app.yaml` 与 `config/i18n.yaml`；远程用例先运行 `python -m pytest_dsl.remote.keyword_server --host localhost --port 8278`，再使用 `--yaml-vars-dir config` 以加载 `remote_servers.yaml`；生成目录 `.pytest-dsl-gui/`、`allure-results/` 和 `allure-report/` 不提交。Studio 部分写明选择项目根目录、选择 `config/api.yaml`、打开 `tests/api_quickstart.dsl`，以及运行页和构建页各自用途，最终措辞以本次实际界面操作为准。
```

- [ ] **Step 4: Rewrite `README.md` as the approved product page**

Keep the final file below 500 lines and use these exact factual sections:

1. `# pytest-dsl：用语法约束测试过程，让接口用例和报告天然可读`
2. One sentence: pytest-based keyword DSL; API testing is the first adoption path; Studio is optional.
3. `## 为什么是 pytest-dsl`: compare a conventional pytest function with manually nested `allure.step` against the canonical DSL, without claiming pytest itself is incapable.
4. `## 一个关键字开始接口测试`: state “接近零额外封装成本,” then list only verified `[HTTP请求]` capabilities and embed the three-request canonical example.
5. `## 从 DSL 到可读报告`: map custom step names, request/response summaries, captures, assertions, and failures to current Allure behavior.
6. `## Pytest DSL Studio`: describe verified project tree, CodeMirror editor, keyword discovery, run/debug, suite build, and embedded Allure report; state that Studio is optional.
7. `## 5 分钟运行 API 示例`: install, start mock, run CLI, generate Allure, and start Studio with commands verified in this worktree.
8. `## 核心能力`: API, variables/config, custom keywords/resources, remote keywords, pytest/Allure integration.
9. `## 文档`: link to `docs/guide/getting-started.md`, `docs/guide/http-testing.md`, `docs/guide/dsl-syntax.md`, `docs/guide/custom-keywords.md`, `docs/guide/remote-keywords.md`, `docs/guide/reporting.md`, and `examples/gui_validation/README.md`.
10. Requirements, contribution, and MIT license.

Do not copy the stale “重试次数/重试间隔” names from `pytest_dsl/examples/http/README.md`; if retry is mentioned, use the current registered names “断言重试次数/断言重试间隔.” Remove unverified superlatives such as “完美兼容” and claims that UI automation is built in.

- [ ] **Step 5: Run README tests**

Run: `python -m pytest tests/test_readme_product_page.py tests/test_gui_validation_api_example.py -q`

Expected before screenshots: product structure and API example assertions pass；本地链接完整性测试仅因三张目标截图尚不存在而失败，并明确列出这三个路径。

- [ ] **Step 6: Keep the text changes staged for screenshot completion**

Do not commit a known failing link-integrity test. Review `git diff -- README.md examples/gui_validation/README.md tests/test_readme_product_page.py`, then continue directly to Task 4 and make the suite green by capturing the real images.

### Task 4: Capture real Studio and Allure screenshots

**Files:**
- Create: `docs/images/readme/studio-api-editor.png`
- Create: `docs/images/readme/studio-api-run.png`
- Create: `docs/images/readme/allure-api-report.png`

- [ ] **Step 1: Verify the GUI baseline before capture**

Run: `npm run check --prefix electron-gui`

Expected: all Node tests and app-file checks pass.

- [ ] **Step 2: Start the deterministic API and Studio**

Start the mock server synchronously in a persistent terminal session:

```bash
python examples/gui_validation/tools/mock_api_server.py
```

Start Studio from the repository root in a second persistent session:

```bash
npm start --prefix electron-gui
```

Use the desktop-computer-automation skill because Studio is a native Electron application. Load `examples/gui_validation`, select `config/api.yaml`, and open `tests/api_quickstart.dsl`.

- [ ] **Step 3: Capture the editor view**

Set a consistent window size, expose the project tree and the complete first HTTP request, then save the screenshot as `docs/images/readme/studio-api-editor.png`. Inspect the saved image and reject it if text is clipped, another app is visible, or local-sensitive paths dominate the frame.

- [ ] **Step 4: Capture the successful run view**

Run `tests/api_quickstart.dsl` from Studio. Confirm the UI reports a passed task and the console contains `接口测试核心链路验证完成`, then save `docs/images/readme/studio-api-run.png`.

- [ ] **Step 5: Capture the expanded Allure report**

Use Studio’s build view to run the API DSL with `config/api.yaml`. Wait for the embedded Allure report, open the passing API case, expand the HTTP steps/attachments enough to show the DSL-to-report mapping, and save `docs/images/readme/allure-api-report.png`.

- [ ] **Step 6: Re-run link/image tests and commit screenshots**

Run: `python -m pytest tests/test_readme_product_page.py -q`

Expected: `3 passed`.

```bash
git add README.md examples/gui_validation/README.md tests/test_readme_product_page.py docs/images/readme/*.png
git commit -m "docs: reposition pytest-dsl around API readability"
```

### Task 5: Full evidence review and verification

**Files:**
- Verify all modified files.

- [ ] **Step 1: Audit every product claim against source or runtime evidence**

Cross-check README statements against:

- `pytest_dsl/keywords/http_keywords.py`
- `pytest_dsl/core/http_request.py`
- `pytest_dsl/core/keyword_manager.py`
- `electron-gui/src/services/executionService.js`
- `electron-gui/src/services/buildService.js`
- the generated Allure result JSON
- the three captured screenshots

Delete or narrow any sentence that cannot be demonstrated.

- [ ] **Step 2: Run targeted Python verification**

Run:

```bash
python -m pytest \
  tests/test_gui_validation_api_example.py \
  tests/test_readme_product_page.py \
  tests/test_http_assertions_extractors.py \
  tests/test_readme_validation_runner.py -q
```

Expected: all tests pass.

- [ ] **Step 3: Run the established README validation suite**

Run: `python examples/readme_validation/run_all_tests.py --skip-remote`

Expected: zero failures.

- [ ] **Step 4: Run Electron verification**

Run: `npm run check --prefix electron-gui`

Expected: all tests and file checks pass.

- [ ] **Step 5: Run repository hygiene checks**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; only intentional files are modified or newly tracked.

- [ ] **Step 6: Commit any final evidence corrections**

```bash
git add README.md examples/gui_validation tests docs/images/readme .gitignore
git commit -m "docs: finalize evidence-backed API quick start"
```
