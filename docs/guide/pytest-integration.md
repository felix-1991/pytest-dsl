# pytest集成

pytest-dsl 设计为与 pytest 生态系统无缝集成，让您能够在现有的 pytest 项目中使用 DSL 文件，同时享受 pytest 的强大功能，如参数化测试、fixture、插件等。

## 基本集成

### 安装要求

确保您已经安装了 pytest 和 pytest-dsl：

```bash
pip install pytest pytest-dsl
```

### 基本用法

创建一个 Python 测试文件，使用 `pytest_dsl.run_dsl_file()` 函数运行 DSL 文件：

```python
# test_dsl_integration.py
import pytest
from pytest_dsl import run_dsl_file

def test_hello_world():
    """使用DSL文件进行测试"""
    result = run_dsl_file("hello.dsl")
    assert result.success

def test_api_basic():
    """API测试示例"""
    result = run_dsl_file("api_basic.dsl")
    assert result.success
```

运行测试：

```bash
pytest test_dsl_integration.py -v
```

## 参数化测试

### 使用 pytest 参数化运行多个 DSL 文件

```python
import pytest
from pytest_dsl import run_dsl_file

@pytest.mark.parametrize("dsl_file", [
    "hello.dsl",
    "api_basic.dsl", 
    "builtin_keywords.dsl"
])
def test_dsl_files(dsl_file):
    """参数化测试多个DSL文件"""
    result = run_dsl_file(dsl_file)
    assert result.success, f"DSL文件 {dsl_file} 执行失败"
```

### 数据驱动测试集成

结合 pytest 的参数化功能和 DSL 的数据驱动能力：

```python
import pytest
from pytest_dsl import run_dsl_file

# 测试数据
test_data = [
    {"user_id": 1, "expected_name": "Leanne Graham"},
    {"user_id": 2, "expected_name": "Ervin Howell"},
    {"user_id": 3, "expected_name": "Clementine Bauch"}
]

@pytest.mark.parametrize("data", test_data)
def test_user_api(data):
    """参数化的用户API测试"""
    # 将测试数据传递给DSL
    result = run_dsl_file(
        "user_test.dsl",
        variables={
            "user_id": data["user_id"],
            "expected_name": data["expected_name"]
        }
    )
    assert result.success
```

## Fixture 集成

### 使用 pytest fixture

```python
import pytest
from pytest_dsl import run_dsl_file

@pytest.fixture
def test_config():
    """测试配置 fixture"""
    return {
        "base_url": "https://jsonplaceholder.typicode.com",
        "timeout": 30,
        "retry_count": 3
    }

@pytest.fixture
def auth_token():
    """认证令牌 fixture"""
    # 在实际项目中，这里可能会调用认证API获取token
    return "test-auth-token-12345"

def test_authenticated_api(test_config, auth_token):
    """使用 fixture 的认证API测试"""
    result = run_dsl_file(
        "auth_api.dsl",
        variables={
            "base_url": test_config["base_url"],
            "auth_token": auth_token,
            "timeout": test_config["timeout"]
        }
    )
    assert result.success
```

### 共享 fixture

创建 `conftest.py` 文件共享 fixture：

```python
# conftest.py
import pytest
from pytest_dsl import run_dsl_file

@pytest.fixture(scope="session")
def api_base_url():
    """会话级别的API基础URL"""
    return "https://jsonplaceholder.typicode.com"

@pytest.fixture(scope="function")
def dsl_runner():
    """DSL运行器 fixture"""
    def _run_dsl(file_path, **kwargs):
        result = run_dsl_file(file_path, **kwargs)
        assert result.success, f"DSL文件执行失败: {result.error}"
        return result
    return _run_dsl
```

使用共享 fixture：

```python
def test_posts_api(dsl_runner, api_base_url):
    """使用共享fixture的测试"""
    dsl_runner("posts_test.dsl", variables={"base_url": api_base_url})
```

## 配置集成

### pytest 配置文件集成

在 `pytest.ini` 或 `pyproject.toml` 中配置 DSL 相关设置：

```ini
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py *_test.py
python_functions = test_*
markers =
    dsl: DSL文件测试
    api: API测试
    slow: 慢速测试
```

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "dsl: DSL文件测试",
    "api: API测试", 
    "slow: 慢速测试"
]
```

### 标记 DSL 测试

```python
import pytest
from pytest_dsl import run_dsl_file

@pytest.mark.dsl
@pytest.mark.api
def test_user_crud():
    """标记为DSL和API测试"""
    result = run_dsl_file("user_crud.dsl")
    assert result.success

@pytest.mark.slow
def test_performance():
    """标记为慢速测试"""
    result = run_dsl_file("performance_test.dsl")
    assert result.success
```

运行特定标记的测试：

```bash
# 只运行DSL测试
pytest -m dsl

# 排除慢速测试
pytest -m "not slow"

# 运行API相关的DSL测试
pytest -m "dsl and api"
```

## 报告集成

### HTML 报告

```bash
# 生成HTML报告
pytest --html=report.html --self-contained-html
```

### Allure 报告

安装 Allure 插件：

```bash
pip install allure-pytest
```

在测试中添加 Allure 装饰器：

```python
import allure
from pytest_dsl import run_dsl_file

@allure.feature("用户管理")
@allure.story("用户信息查询")
def test_get_user():
    with allure.step("执行用户查询DSL"):
        result = run_dsl_file("get_user.dsl")
        assert result.success

@allure.feature("API测试")
@allure.severity(allure.severity_level.CRITICAL)
def test_critical_api():
    with allure.step("执行关键API测试"):
        result = run_dsl_file("critical_api.dsl")
        assert result.success
```

生成 Allure 报告：

```bash
pytest --alluredir=allure-results
allure serve allure-results
```

## 错误处理和调试

### 详细错误信息

```python
from pytest_dsl import run_dsl_file, DSLExecutionError

def test_with_error_handling():
    try:
        result = run_dsl_file("may_fail.dsl")
        assert result.success
    except DSLExecutionError as e:
        pytest.fail(f"DSL执行失败: {e.message}\n详细信息: {e.details}")
```

### 调试模式

```python
def test_debug_mode():
    """在调试模式下运行DSL"""
    result = run_dsl_file(
        "debug_test.dsl", 
        debug=True,  # 启用调试输出
        verbose=True  # 详细输出
    )
    assert result.success
```

## 并行执行

### 使用 pytest-xdist 并行运行

安装并行插件：

```bash
pip install pytest-xdist
```

并行运行测试：

```bash
# 使用4个进程并行运行
pytest -n 4

# 自动检测CPU核心数
pytest -n auto
```

注意：确保您的 DSL 测试是线程安全的，避免共享状态冲突。

## CI/CD 集成示例

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: DSL Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.8
        
    - name: Install dependencies
      run: |
        pip install pytest pytest-dsl pytest-html
        
    - name: Run DSL tests
      run: |
        pytest tests/ --html=report.html --self-contained-html
        
    - name: Upload test report
      uses: actions/upload-artifact@v2
      with:
        name: test-report
        path: report.html
```

## 最佳实践

### 1. 文件组织

```
project/
├── tests/
│   ├── conftest.py          # 共享fixture
│   ├── test_user_api.py     # pytest测试文件
│   └── dsl/                 # DSL文件目录
│       ├── user_crud.dsl
│       ├── auth_test.dsl
│       └── config.yaml
├── pytest.ini              # pytest配置
└── requirements.txt
```

### 2. 命名约定

- pytest 文件：`test_*.py` 或 `*_test.py`
- DSL 文件：`*.dsl`
- 配置文件：`config.yaml` 或 `test_config.yaml`

### 3. 标记策略

```python
@pytest.mark.unit      # 单元测试
@pytest.mark.api       # API测试
@pytest.mark.e2e       # 端到端测试
@pytest.mark.smoke     # 冒烟测试
@pytest.mark.regression # 回归测试
```

### 4. 错误处理

总是检查 DSL 执行结果，提供清晰的错误信息：

```python
def test_dsl_with_clear_error():
    result = run_dsl_file("test.dsl")
    assert result.success, f"测试失败: {result.error_message}"
```

通过 pytest 集成，您可以充分利用 pytest 生态系统的强大功能，同时享受 DSL 带来的简洁性和可读性。这种集成方式特别适合需要在现有 pytest 项目中逐步引入 DSL 测试的场景。 