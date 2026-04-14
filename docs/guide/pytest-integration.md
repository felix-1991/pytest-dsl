# pytest集成

**pytest-dsl 是用于测试 DSL 文件的工具**，核心的自动化测试能力依靠 pytest 生态系统。pytest-dsl 设计为与 pytest 无缝集成，让您能够在现有的 pytest 项目中使用 DSL 文件，同时享受 pytest 的强大功能。

**核心集成方式是通过 `auto_dsl` 装饰器**，它能够自动将目录下的 DSL 文件转换为标准的 pytest 测试方法。

## 核心集成：auto_dsl 装饰器

### 安装要求

确保您已经安装了 pytest 和 pytest-dsl：

```bash
pip install pytest pytest-dsl
```

### 基本用法

`auto_dsl` 装饰器是 pytest-dsl 与 pytest 集成的核心，它能够自动扫描目录下的 `.dsl` 和 `.auto` 文件，并将它们转换为标准的 pytest 测试方法。

```python
# test_runner.py
from pytest_dsl.core.auto_decorator import auto_dsl

@auto_dsl("./tests")
class TestAPI:
    """自动加载tests目录下的所有DSL文件"""
    pass
```

**工作原理：**
- 自动扫描指定目录下的所有 `.dsl` 和 `.auto` 文件
- 将每个 DSL 文件转换为一个 `test_` 开头的测试方法
- 支持数据驱动测试自动参数化
- 自动处理 setup 和 teardown 钩子文件

### 目录结构示例

```
project/
├── test_runner.py           # pytest 测试文件
└── tests/                   # DSL 文件目录
    ├── setup.dsl            # 可选：类级别 setup
    ├── teardown.dsl         # 可选：类级别 teardown
    ├── user_login.dsl       # 普通测试
    ├── api_crud.dsl         # API测试
    └── data_driven.dsl      # 数据驱动测试
```

运行测试：

```bash
pytest test_runner.py -v
```

输出示例：
```
test_runner.py::TestAPI::test_user_login PASSED
test_runner.py::TestAPI::test_api_crud PASSED
test_runner.py::TestAPI::test_data_driven[case1] PASSED
test_runner.py::TestAPI::test_data_driven[case2] PASSED
```

### 单文件集成

也可以指定单个 DSL 文件：

```python
from pytest_dsl.core.auto_decorator import auto_dsl

@auto_dsl("./tests/user_login.dsl", is_file=True)
class TestUserLogin:
    """测试用户登录功能"""
    pass
```

### 多目录集成

为不同的测试模块创建不同的测试类：

```python
from pytest_dsl.core.auto_decorator import auto_dsl

@auto_dsl("./tests/api")
class TestAPI:
    """API相关测试"""
    pass

@auto_dsl("./tests/ui")
class TestUI:
    """UI相关测试"""
    pass

@auto_dsl("./tests/integration")
class TestIntegration:
    """集成测试"""
    pass
```

## 高级功能

### 自动数据驱动测试

`auto_dsl` 装饰器自动识别数据驱动的 DSL 文件，并使用 `pytest.mark.parametrize` 进行参数化：

```dsl
# data_driven_test.dsl
@data: users.yaml
@name: "用户API测试"

# user_id 由数据驱动数据集直接注入
[HTTP请求], 客户端: "default", 保存响应: "response", 配置: '''
    method: GET
    url: https://api.example.com/users/${user_id}
'''
[断言], 条件: "${response.status_code} == 200", 消息: "状态码应为 200"
```

自动转换为：
```python
@pytest.mark.parametrize('test_data', [...], ids=[...])
def test_data_driven_test(self, test_data):
    # 执行DSL逻辑
```

### Setup 和 Teardown 支持

`auto_dsl` 装饰器自动识别并处理钩子文件：

- `setup.dsl` 或 `setup.auto` - 类级别的前置操作
- `teardown.dsl` 或 `teardown.auto` - 类级别的后置操作

```dsl
# tests/setup.dsl
@name: "API测试环境准备"

# 初始化测试环境
base_url = "https://api.example.com"
auth_token = "test-token"
```

## 传统集成方式

当前版本没有公开的 `run_dsl_file()` 便捷函数。
如果不使用 `auto_dsl`，推荐在 pytest 用例里通过 `subprocess` 调用 `pytest-dsl` CLI：

```python
import subprocess
import pytest


@pytest.mark.parametrize("dsl_file", [
    "hello.dsl",
    "api_basic.dsl",
    "builtin_keywords.dsl",
])
def test_dsl_files(dsl_file):
    completed = subprocess.run(
        ["pytest-dsl", dsl_file],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, (
        f"DSL文件 {dsl_file} 执行失败\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )
```

## Fixture 集成

### 在 auto_dsl 中使用 fixture

```python
import pytest
from pytest_dsl.core.auto_decorator import auto_dsl

@pytest.fixture(scope="class")
def test_config():
    """测试配置 fixture"""
    return {
        "base_url": "https://jsonplaceholder.typicode.com",
        "timeout": 30
    }

@auto_dsl("./tests")
class TestAPI:
    """自动加载tests目录下的所有DSL文件"""
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self, test_config):
        """为每个测试方法设置测试数据"""
        # 这里可以将 fixture 数据传递给 DSL 执行环境
        from pytest_dsl.core.context import get_context
        context = get_context()
        context.set_variable("base_url", test_config["base_url"])
        context.set_variable("timeout", test_config["timeout"])
```

### 共享 fixture

创建 `conftest.py` 文件：

```python
# conftest.py
import pytest

@pytest.fixture(scope="session")
def api_base_url():
    """会话级别的API基础URL"""
    return "https://jsonplaceholder.typicode.com"

@pytest.fixture(scope="class", autouse=True)
def setup_dsl_context(api_base_url):
    """自动为所有DSL测试设置上下文"""
    from pytest_dsl.core.context import get_context
    context = get_context()
    context.set_variable("base_url", api_base_url)
    yield
    context.clear()
```

## 配置集成

### pytest 配置文件

```ini
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py *_test.py
python_functions = test_*
python_classes = Test*
markers =
    dsl: DSL文件测试
    api: API测试
    slow: 慢速测试
```

### 标记 DSL 测试类

```python
import pytest
from pytest_dsl.core.auto_decorator import auto_dsl

@pytest.mark.dsl
@pytest.mark.api
@auto_dsl("./tests/api")
class TestAPI:
    """API相关的DSL测试"""
    pass

@pytest.mark.slow
@auto_dsl("./tests/performance")
class TestPerformance:
    """性能测试"""
    pass
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
pytest test_runner.py --html=report.html --self-contained-html
```

### Allure 报告

安装 Allure 插件：

```bash
pip install allure-pytest
```

为测试类添加 Allure 元数据：

```python
import allure
from pytest_dsl.core.auto_decorator import auto_dsl

@allure.feature("用户管理")
@auto_dsl("./tests/user")
class TestUser:
    """用户管理相关测试"""
    pass

@allure.feature("API测试")
@allure.severity(allure.severity_level.CRITICAL)
@auto_dsl("./tests/api")
class TestAPI:
    """API测试"""
    pass
```

生成 Allure 报告：

```bash
pytest test_runner.py --alluredir=allure-results
allure serve allure-results
```

## 错误处理和调试

### 调试模式

DSL 执行错误会自动转换为 pytest 断言错误，可以使用 pytest 的调试功能：

```python
from pytest_dsl.core.auto_decorator import auto_dsl

@auto_dsl("./tests")
class TestAPI:
    """测试类，使用pytest的调试功能"""
    pass
```

使用 pytest 调试功能：

```bash
# 详细输出
pytest test_runner.py -v -s

# 失败时进入调试器
pytest test_runner.py --pdb

# 只运行失败的测试
pytest test_runner.py --lf
```

### 详细错误信息

当 DSL 执行失败时，pytest 会显示详细的错误信息：

```
FAILED test_runner.py::TestAPI::test_user_login - AssertionError: DSL执行失败
Expected status code 200, but got 404
File: user_login.dsl, Line: 5
```

## 并行执行

### 使用 pytest-xdist

```bash
pip install pytest-xdist

# 并行运行测试
pytest test_runner.py -n auto
```

注意：确保您的 DSL 测试是线程安全的。

## 自动化运行示例（基于pytest）

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
        pip install pytest pytest-dsl pytest-html allure-pytest
        
    - name: Run DSL tests
      run: |
        pytest test_runner.py --html=report.html --alluredir=allure-results
        
    - name: Upload test reports
      uses: actions/upload-artifact@v2
      with:
        name: test-reports
        path: |
          report.html
          allure-results/
```

## 最佳实践

### 1. 推荐的项目结构

```
project/
├── test_runner.py           # 主测试运行器
├── conftest.py              # 共享 fixture
├── pytest.ini              # pytest 配置
├── tests/                   # DSL 测试目录
│   ├── setup.dsl            # 全局 setup
│   ├── teardown.dsl         # 全局 teardown
│   ├── api/                 # API 测试模块
│   │   ├── setup.dsl        # API 模块 setup
│   │   ├── user_crud.dsl
│   │   └── auth_test.dsl
│   ├── ui/                  # UI 测试模块
│   │   ├── login.dsl
│   │   └── dashboard.dsl
│   └── config/              # 配置文件
│       ├── dev.yaml
│       └── prod.yaml
└── requirements.txt
```

### 2. 主测试运行器模板

```python
# test_runner.py
import pytest
from pytest_dsl.core.auto_decorator import auto_dsl

@pytest.mark.api
@auto_dsl("./tests/api")
class TestAPI:
    """API测试套件"""
    pass

@pytest.mark.ui
@auto_dsl("./tests/ui")
class TestUI:
    """UI测试套件"""
    pass

@pytest.mark.integration
@auto_dsl("./tests/integration")
class TestIntegration:
    """集成测试套件"""
    pass

if __name__ == "__main__":
    # 支持直接运行
    pytest.main([__file__, "-v"])
```

### 3. 命名约定

- 测试类：`Test*` （pytest 标准）
- DSL 文件：描述性名称，如 `user_login.dsl`、`api_crud.dsl`
- 配置文件：环境名称，如 `dev.yaml`、`prod.yaml`

### 4. 性能优化

- 使用类级别的 setup/teardown 减少重复初始化
- 合理使用 pytest fixture 的 scope
- 对于大型测试套件，考虑按模块分离

**auto_dsl 装饰器的优势：**
- 🚀 **零配置**：自动发现和转换 DSL 文件
- 🔄 **完全兼容**：充分利用 pytest 的所有功能
- 📊 **原生报告**：无缝集成 pytest 报告系统
- 🎯 **类型安全**：自动处理数据驱动和参数化
- 🛠️ **易于维护**：清晰的项目结构和文件组织

通过 `auto_dsl` 装饰器，pytest-dsl 实现了与 pytest 的深度集成，让您能够在享受 DSL 简洁性的同时，充分利用 pytest 生态系统的强大功能。 
