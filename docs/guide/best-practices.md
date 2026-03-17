# 最佳实践

本章总结了使用pytest-dsl进行测试开发的最佳实践，帮助您建立高质量、可维护的测试项目。

**核心建议：使用pytest集成方式组织测试案例**，通过`auto_dsl`装饰器自动管理DSL文件，充分利用pytest生态系统的强大能力。

## 核心理念

### 🎯 为什么推荐pytest集成？

**pytest-dsl的定位**：DSL文件测试工具，核心自动化测试能力依靠pytest生态系统。

**auto_dsl装饰器的优势**：
- 🚀 **零配置自动化** - 自动扫描并转换DSL文件为pytest测试方法
- 📊 **数据驱动支持** - 只有pytest方式才支持`@data`指令的数据驱动测试
- 🔧 **强大的pytest能力** - fixture、参数化、标记、报告、插件生态
- 🎭 **灵活的测试组织** - 简单场景用目录形式，复杂场景可细化拆分
- 🛠️ **易于维护** - 清晰的项目结构，便于团队协作

### 🎨 组织策略选择

```python
# 🟢 简单项目：目录形式（推荐）
@auto_dsl("./tests")
class TestAll:
    """自动加载所有测试 - 适合小型项目"""
    pass

# 🟡 中型项目：模块拆分
@auto_dsl("./tests/api")
class TestAPI:
    """API测试模块"""
    pass

@auto_dsl("./tests/ui")  
class TestUI:
    """UI测试模块"""
    pass

# 🟠 大型项目：细化拆分（特殊场景）
@pytest.mark.smoke
@auto_dsl("./tests/api/auth")
class TestAPIAuth:
    """认证API - 用于精确控制执行策略"""
    pass
```

## 推荐的项目组织方式

### 1. 基础pytest集成结构（推荐）

使用`auto_dsl`装饰器的目录形式，简单高效：

```
my-test-project/
├── test_runner.py                   # pytest主运行器
├── conftest.py                      # pytest共享配置
├── pytest.ini                      # pytest配置文件
├── tests/                           # DSL测试文件目录
│   ├── setup.dsl                    # 全局setup（可选）
│   ├── teardown.dsl                 # 全局teardown（可选）
│   ├── api/                         # API测试模块
│   │   ├── setup.dsl                # API模块setup（可选）
│   │   ├── teardown.dsl             # API模块teardown（可选）
│   │   ├── auth_login.dsl
│   │   ├── auth_logout.dsl
│   │   ├── users_crud.dsl
│   │   └── orders_workflow.dsl
│   ├── ui/                          # UI测试模块
│   │   ├── login_flow.dsl
│   │   └── dashboard_ops.dsl
│   └── integration/                 # 集成测试模块
│       └── end_to_end.dsl
├── resources/                       # 资源文件
│   ├── common/
│   │   ├── utilities.resource
│   │   └── validators.resource
│   ├── api/
│   │   └── http_helpers.resource
│   └── business/
│       └── workflows.resource
├── data/                            # 测试数据
│   ├── users.csv                    # 数据驱动测试数据
│   ├── scenarios.json
│   └── fixtures/
├── config/                          # 配置文件
│   ├── dev.yaml
│   ├── test.yaml
│   └── prod.yaml
├── requirements.txt                 # Python依赖
└── README.md                        # 项目说明
```

**主运行器示例：**

```python
# test_runner.py
from pytest_dsl.core.auto_decorator import auto_dsl
import pytest

@auto_dsl("./tests/api")
class TestAPI:
    """API测试套件 - 自动加载tests/api/目录下的所有DSL文件"""
    pass

@auto_dsl("./tests/ui") 
class TestUI:
    """UI测试套件 - 自动加载tests/ui/目录下的所有DSL文件"""
    pass

@auto_dsl("./tests/integration")
class TestIntegration:
    """集成测试套件 - 自动加载tests/integration/目录下的所有DSL文件"""
    pass

# 支持直接运行
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**运行方式：**

```bash
# 运行所有测试
pytest test_runner.py -v

# 运行特定测试类
pytest test_runner.py::TestAPI -v

# 使用配置文件
pytest test_runner.py --yaml-vars config/dev.yaml

# 生成报告
pytest test_runner.py --html=report.html --alluredir=allure-results
```

### 2. 特殊场景下的细化拆分

在某些特殊场景下，您可能需要更细粒度的控制，可以拆分为更具体的测试类：

```python
# test_runner_advanced.py
from pytest_dsl.core.auto_decorator import auto_dsl
import pytest

# === API测试的细化拆分 ===
@pytest.mark.smoke
@auto_dsl("./tests/api/auth")
class TestAPIAuth:
    """认证相关API测试"""
    pass

@pytest.mark.regression  
@auto_dsl("./tests/api/users")
class TestAPIUsers:
    """用户管理API测试"""
    pass

@pytest.mark.critical
@auto_dsl("./tests/api/orders")
class TestAPIOrders:
    """订单相关API测试"""
    pass

# === 按测试类型拆分 ===
@pytest.mark.smoke
@auto_dsl("./tests/smoke")
class TestSmoke:
    """冒烟测试套件"""
    pass

@pytest.mark.integration
@auto_dsl("./tests/integration") 
class TestIntegration:
    """集成测试套件"""
    pass

# === 单文件测试（特殊场景）===
@pytest.mark.critical
@auto_dsl("./tests/critical/payment_flow.dsl", is_file=True)
class TestCriticalPayment:
    """关键支付流程测试"""
    pass
```

**特殊场景适用情况：**

1. **大型项目** - 需要精确控制测试执行粒度
2. **CI/CD管道** - 不同阶段运行不同测试集（按常规pytest配置，无额外插件）
3. **并行执行** - 需要平衡不同测试类的执行时间
4. **测试隔离** - 某些测试需要特殊的环境或数据准备
5. **标记管理** - 需要复杂的pytest标记策略

### 3. 利用pytest核心能力

**pytest集成的优势：**

```python
# conftest.py - 利用pytest的fixture系统
import pytest
from pytest_dsl.core.context import get_context

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(request):
    """会话级别的环境设置"""
    # 全局环境初始化
    context = get_context()
    context.set_variable("test_start_time", "2024-01-15 10:00:00")
    context.set_variable("test_environment", "pytest")
    
    yield
    
    # 全局清理
    context.clear()

@pytest.fixture(scope="class")
def api_client_config():
    """为API测试类提供客户端配置"""
    return {
        "base_url": "https://api.test.com",
        "timeout": 30,
        "headers": {"User-Agent": "pytest-dsl-test"}
    }

@pytest.fixture
def test_data_cleanup():
    """自动测试数据清理"""
    created_resources = []
    
    def register_resource(resource_id, resource_type):
        created_resources.append((resource_id, resource_type))
    
    yield register_resource
    
    # 测试完成后自动清理
    for resource_id, resource_type in created_resources:
        print(f"清理 {resource_type}: {resource_id}")
```

**利用pytest参数化：**

```python
# test_runner_parametrized.py
import pytest
from pytest_dsl.core.auto_decorator import auto_dsl

class TestAPIEnvironments:
    """多环境API测试"""
    
    @pytest.mark.parametrize("env_config", [
        {"name": "dev", "config": "config/dev.yaml"},
        {"name": "test", "config": "config/test.yaml"},
        {"name": "staging", "config": "config/staging.yaml"}
    ])
    def test_api_in_environment(self, env_config):
        """在不同环境中运行API测试"""
        from pytest_dsl import run_dsl_file
        
        result = run_dsl_file(
            "tests/api/health_check.dsl",
            variables={"environment": env_config["name"]},
            config_file=env_config["config"]
        )
        assert result.success, f"API测试在{env_config['name']}环境中失败"
```

**利用pytest标记和过滤：**

```bash
# 利用pytest的强大过滤能力
pytest test_runner.py -m "smoke"                    # 只运行冒烟测试
pytest test_runner.py -m "not slow"                 # 排除慢速测试
pytest test_runner.py -m "api and critical"         # 运行关键API测试
pytest test_runner.py -k "auth"                     # 运行包含auth的测试
pytest test_runner.py --lf                          # 只运行上次失败的测试
pytest test_runner.py --ff                          # 先运行上次失败的测试
pytest test_runner.py -x                            # 遇到失败立即停止
pytest test_runner.py --maxfail=3                   # 失败3次后停止
```

## 代码规范

### 文件命名规范

```python
# 测试文件命名
test_user_registration.dsl          # 功能模块_具体功能
test_api_authentication.dsl         # 测试类型_功能模块
test_order_workflow_e2e.dsl        # 功能模块_测试类型

# 资源文件命名
user_management.resource            # 功能域
api_common_utilities.resource       # 用途_范围_类型
database_connection_utils.resource  # 技术栈_功能_类型

# 数据文件命名
user_test_data_valid.csv           # 数据类型_用途_场景
api_endpoints_dev.json             # 数据类型_环境
login_scenarios_regression.xlsx    # 功能_测试套件
```

### DSL代码风格

#### 1. 元信息规范

```python
@name: "用户注册API测试"
@description: "测试用户注册接口的各种场景，包括成功注册、重复注册和无效数据验证"
@tags: ["api", "user", "registration", "smoke"]
@author: "张三"
@date: "2024-01-15"
```

#### 2. 变量命名规范

```python
# 好的变量名 - 具有描述性
新用户数据 = {
    "username": "testuser123",
    "email": "testuser123@example.com",
    "password": "SecurePass123!"
}

注册响应状态码 = 201
期望的用户角色 = "user"

# 避免的变量名 - 模糊不清
data = {}
code = 200
role = "user"
```

#### 3. 关键字调用格式

```python
# 推荐格式 - 参数明确
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: /api/users
    request:
        json: ${新用户数据}
    captures:
        用户ID: ["jsonpath", "$.id"]
        创建时间: ["jsonpath", "$.created_at"]
    asserts:
        - ["status", "eq", 201]
        - ["jsonpath", "$.username", "eq", "${新用户数据.username}"]
'''

# 避免格式 - 参数混乱
[HTTP请求],客户端:"default",配置:'''method:POST
url:/api/users
request:json:${新用户数据}'''
```

#### 4. 注释和文档

```python
# 测试步骤清晰分组
# === 第一步：准备测试数据 ===
测试用户 = {
    "username": "integration_user",
    "email": "integration@example.com"
}

# === 第二步：创建用户 ===
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: /api/users
    request:
        json: ${测试用户}
    captures:
        新用户ID: ["jsonpath", "$.id"]
'''

# === 第三步：验证用户创建成功 ===
[断言], 条件: "\"${新用户ID}\" != \"\"", 消息: "用户创建后应返回有效ID"
```

## 自定义关键字设计

### 关键字命名原则

```python
# 好的关键字名称 - 动词+名词，清晰表达意图
function 创建新用户 (用户数据, 验证邮箱="True") do
    # 实现
end

function 验证API响应结构 (期望字段列表) do
    # 实现
end

function 等待订单状态变更 (订单ID, 目标状态, 超时秒数=30) do
    # 实现
end

# 避免的命名 - 含糊不清
function 处理用户 (数据) do
    # 不明确要处理什么
end

function 检查 (内容) do
    # 不明确要检查什么
end
```

### 参数设计最佳实践

```python
# 1. 必需参数在前，可选参数在后
function 发送HTTP请求 (方法, URL, 数据="", 头部JSON="", 超时=30) do
    # 实现
end

# 2. 使用有意义的默认值
function 等待元素出现 (定位器, 超时秒数=10, 检查间隔=0.5) do
    # 实现
end

# 3. 参数数量控制在5个以内
function 创建订单 (客户ID, 商品列表, 配送地址, 支付方式="credit_card", 备注="") do
    # 如果参数过多，考虑使用字典参数
end

# 更好的方式 - 使用结构化参数
function 创建订单 (订单数据) do
    # 订单数据包含所有必要信息
    客户ID = ${订单数据.customer_id}
    商品列表 = ${订单数据.items}
    配送地址 = ${订单数据.shipping_address}
    # ...
end
```

## 资源文件管理

### 分层组织原则

```python
# 基础层 - 最通用的工具
# resources/common/base_utilities.resource
@name: "基础工具函数"

function 格式化时间戳 (时间戳格式="yyyy-MM-dd HH:mm:ss") do
    # 基础时间处理
end

function 生成随机字符串 (长度=8, 包含特殊字符="False") do
    # 基础字符串生成
end
```

```python
# 功能层 - 特定领域的功能
# resources/api/http_utilities.resource
@name: "HTTP工具函数"
@import: "../common/base_utilities.resource"

function 构建认证头部 (token类型="Bearer", token值) do
    时间戳 = [格式化时间戳]
    [打印], 内容: "构建认证头部 - ${时间戳}"
    
    return {
        "Authorization": "${token类型} ${token值}",
        "X-Request-Time": ${时间戳}
    }
end
```

```python
# 业务层 - 具体业务流程
# resources/business/user_workflows.resource
@name: "用户业务流程"
@import: "../api/http_utilities.resource"

function 完整用户注册流程 (用户信息) do
    # 1. 注册用户
    注册结果 = [注册新用户], 用户数据: ${用户信息}
    
    # 2. 验证邮箱
    验证结果 = [验证用户邮箱], 用户ID: ${注册结果.user_id}
    
    # 3. 首次登录
    登录结果 = [用户登录], 用户名: ${用户信息.username}, 密码: ${用户信息.password}
    
    return {
        "registration": ${注册结果},
        "verification": ${验证结果},
        "login": ${登录结果}
    }
end
```

### 资源文件版本管理

```python
# 在资源文件中添加版本信息
@name: "用户管理API工具"
@version: "2.1.0"
@description: "提供用户相关API操作的关键字集合"
@changelog: "v2.1.0: 添加批量用户操作支持; v2.0.0: 重构认证机制"
@author: "API测试团队"
@date: "2024-01-15"
```

## 测试数据管理

### 数据分类策略

```
data/
├── static/                    # 静态引用数据
│   ├── countries.json        # 国家代码
│   ├── currencies.csv        # 货币信息
│   └── timezones.json        # 时区数据
├── templates/                 # 数据模板
│   ├── user_template.json    # 用户数据模板
│   ├── order_template.json   # 订单数据模板
│   └── product_template.json # 商品数据模板
├── scenarios/                 # 测试场景数据
│   ├── positive_cases/       # 正向用例
│   ├── negative_cases/       # 负向用例
│   └── edge_cases/           # 边界用例
└── environments/             # 环境特定数据
    ├── dev_data/
    ├── test_data/
    └── staging_data/
```

### 数据模板化

```json
// data/templates/user_template.json
{
    "username": "{{USERNAME_PREFIX}}_{{RANDOM_STRING}}",
    "email": "{{USERNAME_PREFIX}}_{{RANDOM_STRING}}@{{EMAIL_DOMAIN}}",
    "profile": {
        "firstName": "{{FIRST_NAME}}",
        "lastName": "{{LAST_NAME}}",
        "age": "{{AGE_RANGE}}"
    },
    "preferences": {
        "language": "{{DEFAULT_LANGUAGE}}",
        "timezone": "{{DEFAULT_TIMEZONE}}"
    }
}
```

```python
# 在测试中使用模板
function 生成用户数据 (用户类型="standard") do
    模板变量 = {
        "USERNAME_PREFIX": "${用户类型}",
        "RANDOM_STRING": [生成随机字符串], 长度: 6,
        "EMAIL_DOMAIN": "testdomain.com",
        "FIRST_NAME": "测试",
        "LAST_NAME": "用户",
        "AGE_RANGE": 25,
        "DEFAULT_LANGUAGE": "zh-CN",
        "DEFAULT_TIMEZONE": "Asia/Shanghai"
    }
    
    # 使用模板生成实际数据
    用户数据 = [应用数据模板], 模板文件: "user_template.json", 变量: ${模板变量}
    return ${用户数据}
end
```

### 测试数据清理策略

```python
# 测试数据清理资源文件
# resources/common/data_cleanup.resource
@name: "测试数据清理工具"

function 清理测试用户 (用户名前缀="test_") do
    [打印], 内容: "开始清理测试用户，前缀: ${用户名前缀}"
    
    # 获取需要清理的用户列表
    [HTTP请求], 客户端: "admin", 配置: '''
        method: GET
        url: /api/admin/users
        request:
            params:
                username_prefix: "${用户名前缀}"
        captures:
            测试用户列表: ["jsonpath", "$.users[*]"]
    '''
    
    # 批量删除测试用户
    for 用户 in ${测试用户列表} do
        [删除用户], 用户ID: ${用户.id}
        [打印], 内容: "删除测试用户: ${用户.username}"
    end
    
    [打印], 内容: "测试用户清理完成"
end

function 重置测试环境 () do
    [打印], 内容: "开始重置测试环境"
    
    # 清理各种测试数据
    [清理测试用户], 用户名前缀: "test_"
    [清理测试订单], 状态: "draft"
    [清理上传文件], 目录: "/test_uploads"
    
    # 重置计数器
    [重置自增ID], 表名: "users"
    [重置自增ID], 表名: "orders"
    
    [打印], 内容: "测试环境重置完成"
end
```

## 环境管理最佳实践

### 配置文件分离

```yaml
# config/environments/base.yaml - 基础配置
http_clients:
  default:
    timeout: 30
    headers:
      User-Agent: "pytest-dsl-client/1.0"
      Accept: "application/json"

test_settings:
  max_retry_count: 3
  default_wait_time: 5
```

```yaml
# config/environments/dev.yaml - 开发环境
extends: base.yaml

http_clients:
  default:
    base_url: "https://dev-api.example.com"
    headers:
      X-Environment: "development"
  
  admin:
    base_url: "https://dev-admin.example.com"
    auth:
      type: "basic"
      username: "admin"
      password: "dev_admin_pass"

database:
  host: "dev-db.example.com"
  name: "dev_database"
```

```yaml
# config/environments/prod.yaml - 生产环境
extends: base.yaml

http_clients:
  default:
    base_url: "https://api.example.com"
    timeout: 60  # 生产环境超时时间更长
    headers:
      X-Environment: "production"

test_settings:
  max_retry_count: 5  # 生产环境更多重试
  default_wait_time: 10
```

### 环境切换机制

```python
# resources/common/environment_manager.resource
@name: "环境管理器"

# 全局环境配置
ENVIRONMENT_CONFIGS = {
    "dev": {
        "api_base": "https://dev-api.example.com",
        "admin_user": "dev_admin",
        "data_prefix": "dev_test_"
    },
    "test": {
        "api_base": "https://test-api.example.com", 
        "admin_user": "test_admin",
        "data_prefix": "test_"
    },
    "staging": {
        "api_base": "https://staging-api.example.com",
        "admin_user": "staging_admin", 
        "data_prefix": "staging_test_"
    }
}

function 初始化测试环境 (环境名称="test") do
    if ${环境名称} not in ${ENVIRONMENT_CONFIGS} do
        [打印], 内容: "错误: 不支持的环境 '${环境名称}'"
        return False
    end
    
    环境配置 = ${ENVIRONMENT_CONFIGS[环境名称]}
    
    # 设置全局环境变量
    [设置全局变量], 变量名: "current_environment", 值: ${环境名称}
    [设置全局变量], 变量名: "api_base_url", 值: ${环境配置.api_base}
    [设置全局变量], 变量名: "admin_user", 值: ${环境配置.admin_user}
    [设置全局变量], 变量名: "data_prefix", 值: ${环境配置.data_prefix}
    
    [打印], 内容: "✓ 环境初始化完成: ${环境名称}"
    [打印], 内容: "  API地址: ${环境配置.api_base}"
    [打印], 内容: "  管理员用户: ${环境配置.admin_user}"
    
    return True
end

function 获取环境变量 (变量名, 默认值="") do
    环境变量值 = [获取全局变量], 变量名: ${变量名}
    
    if "${环境变量值}" == "" and "${默认值}" != "" do
        return ${默认值}
    end
    
    return ${环境变量值}
end
```

## 测试执行策略

### 使用pytest标记管理测试（推荐）

利用pytest的标记系统对测试进行分类和管理：

```python
# test_runner.py
import pytest
from pytest_dsl.core.auto_decorator import auto_dsl

@pytest.mark.smoke
@pytest.mark.api
@auto_dsl("./tests/api/auth")
class TestAPIAuth:
    """认证API测试 - 冒烟测试"""
    pass

@pytest.mark.regression
@pytest.mark.api
@auto_dsl("./tests/api/users")
class TestAPIUsers:
    """用户API测试 - 回归测试"""
    pass

@pytest.mark.integration
@pytest.mark.slow
@auto_dsl("./tests/integration")
class TestIntegration:
    """集成测试 - 耗时较长"""
    pass
```

**pytest.ini配置：**

```ini
# pytest.ini
[tool:pytest]
markers =
    smoke: 冒烟测试，快速验证核心功能
    regression: 回归测试，全面功能验证
    integration: 集成测试，跨系统测试
    api: API接口测试
    ui: 用户界面测试
    slow: 执行时间较长的测试
    critical: 关键业务流程测试
    auth: 认证相关测试
    data_driven: 数据驱动测试
```

### 测试套件执行策略

**使用pytest命令（推荐）：**

```bash
# 运行不同类型的测试
pytest test_runner.py -m smoke                      # 冒烟测试
pytest test_runner.py -m "regression and not slow"  # 回归测试（排除慢速）
pytest test_runner.py -m "api and critical"         # 关键API测试
pytest test_runner.py -m integration                # 集成测试

# 并行执行（需要pytest-xdist）
pytest test_runner.py -m smoke -n auto              # 并行冒烟测试
pytest test_runner.py -m regression -n 4            # 4个进程并行回归测试

# 生成报告
pytest test_runner.py -m smoke --html=smoke_report.html
pytest test_runner.py -m regression --alluredir=allure-results
```

**自动化脚本示例（基于pytest）：**

```bash
# scripts/run_tests.sh
#!/bin/bash

# 冒烟测试 - 快速验证
echo "=== 运行冒烟测试 ==="
pytest test_runner.py -m smoke --tb=short

# 回归测试 - 详细验证
echo "=== 运行回归测试 ==="
pytest test_runner.py -m regression --html=regression_report.html --self-contained-html

# 集成测试 - 完整流程
echo "=== 运行集成测试 ==="
pytest test_runner.py -m integration --maxfail=1
```

### 并行执行优化

```python
# 设计支持并行执行的测试
@name: "并行安全的用户测试"
@tags: ["parallel_safe"]

# 使用独特的测试数据避免冲突
测试时间戳 = [获取当前时间]
独特用户名 = "test_user_${测试时间戳}_${random()}"

用户数据 = {
    "username": ${独特用户名},
    "email": "${独特用户名}@example.com"
}

# 测试逻辑...

# 清理创建的数据
teardown do
    [删除测试用户], 用户名: ${独特用户名}
end
```

## 报告和监控

### 测试结果报告

```python
# 在测试中添加详细的报告信息
@name: "订单创建流程测试"

# 添加测试步骤说明
[打印], 内容: "步骤1: 准备测试数据"
订单数据 = [生成订单数据]

[打印], 内容: "步骤2: 创建订单"
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: /api/orders
    request:
        json: ${订单数据}
    captures:
        订单ID: ["jsonpath", "$.order_id"]
        创建时间: ["jsonpath", "$.created_at"]
''', 步骤名称: "创建新订单"

[打印], 内容: "步骤3: 验证订单创建成功"
[断言], 条件: "\"${订单ID}\" != \"\"", 消息: "订单ID不应为空"

# 添加测试结果总结
[打印], 内容: "✓ 测试完成 - 订单ID: ${订单ID}, 创建时间: ${创建时间}"
```

### 性能监控

```python
# resources/common/performance_monitor.resource
@name: "性能监控工具"

function 监控API性能 (API名称, 请求配置) do
    开始时间 = [获取当前时间]
    
    # 执行API请求
    [HTTP请求], 客户端: "default", 配置: ${请求配置}
    
    结束时间 = [获取当前时间] 
    响应时间 = ${结束时间} - ${开始时间}
    
    # 记录性能数据
    [打印], 内容: "API性能 - ${API名称}: ${响应时间}ms"
    
    # 性能告警
    if ${响应时间} > 5000 do
        [打印], 内容: "⚠️ 性能告警: ${API名称} 响应时间过长 (${响应时间}ms)"
    end
    
    return {
        "api_name": ${API名称},
        "response_time": ${响应时间},
        "timestamp": ${结束时间}
    }
end
```

## 自动化运行最佳实践

### 自动化管道配置（基于pytest）

**利用pytest的标准能力：**

```yaml
# .github/workflows/test.yml
name: pytest-dsl自动化测试

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  smoke-tests:
    name: 冒烟测试
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: 设置Python环境
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          
      - name: 安装依赖
        run: |
          pip install pytest pytest-dsl pytest-html pytest-xdist
          
      - name: 运行冒烟测试
        run: |
          pytest test_runner.py -m smoke -v --tb=short --html=smoke_report.html
          
      - name: 上传冒烟测试报告
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: smoke-test-report
          path: smoke_report.html

  regression-tests:
    name: 回归测试
    runs-on: ubuntu-latest
    needs: smoke-tests
    if: github.event_name == 'push'
    strategy:
      matrix:
        test-group: [api, ui, integration]
    steps:
      - uses: actions/checkout@v3
      
      - name: 设置Python环境
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          
      - name: 安装依赖
        run: |
          pip install pytest pytest-dsl pytest-html allure-pytest pytest-xdist
          
      - name: 运行回归测试
        run: |
          pytest test_runner.py -m "regression and ${{ matrix.test-group }}" \
                 -n auto --alluredir=allure-results-${{ matrix.test-group }}
          
      - name: 生成Allure报告
        if: always()
        run: |
          allure generate allure-results-${{ matrix.test-group }} \
                 -o allure-report-${{ matrix.test-group }} --clean
          
      - name: 上传回归测试报告
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: regression-report-${{ matrix.test-group }}
          path: allure-report-${{ matrix.test-group }}

  integration-tests:
    name: 集成测试
    runs-on: ubuntu-latest
    needs: [smoke-tests, regression-tests]
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      
      - name: 设置Python环境
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          
      - name: 运行集成测试
        run: |
          pytest test_runner.py -m integration --maxfail=1 \
                 --html=integration_report.html --self-contained-html
```

### 测试数据准备

```python
# scripts/prepare_test_data.py
"""
测试数据准备脚本
在CI/CD管道中运行，为测试环境准备必要的数据
"""

def prepare_test_users():
    """准备测试用户数据"""
    users = [
        {"username": "test_admin", "role": "admin"},
        {"username": "test_user", "role": "user"},
        {"username": "test_guest", "role": "guest"}
    ]
    
    for user in users:
        # 调用API创建用户
        pass

def prepare_test_products():
    """准备测试商品数据"""
    pass

if __name__ == "__main__":
    prepare_test_users()
    prepare_test_products()
    print("测试数据准备完成")
```

## 团队协作规范

### 代码审查清单

- [ ] 测试文件命名遵循规范
- [ ] 包含完整的元信息标签
- [ ] 变量命名清晰有意义
- [ ] 关键字调用格式正确
- [ ] 包含适当的断言验证
- [ ] 添加了必要的注释说明
- [ ] 测试数据独立且可重复
- [ ] 包含适当的清理操作
- [ ] 错误处理完善
- [ ] 性能考虑合理

### 文档维护

```python
# 在每个重要的资源文件中维护变更日志
@name: "用户管理API工具"
@version: "2.1.0"
@changelog: '''
v2.1.0 (2024-01-15):
  - 添加: 批量用户操作支持
  - 修复: 用户角色验证逻辑
  - 优化: 提升用户查询性能

v2.0.0 (2024-01-01):
  - 重构: 全新的认证机制
  - 添加: 用户权限管理
  - 移除: 已废弃的旧版API支持
'''
```

## 故障排除指南

### 常见问题诊断

```python
# resources/common/diagnostics.resource
@name: "诊断工具"

function 诊断环境连通性 () do
    [打印], 内容: "=== 环境连通性诊断 ==="
    
    # 检查API服务可达性
    [HTTP请求], 客户端: "default", 配置: '''
        method: GET
        url: /health
        asserts:
            - ["status", "eq", 200]
    '''
    [打印], 内容: "✓ API服务连通正常"
    
    # 检查数据库连接
    [执行命令], 命令: "ping -c 1 db.example.com"
    [打印], 内容: "✓ 数据库连接正常"
    
    # 检查认证服务
    [HTTP请求], 客户端: "auth", 配置: '''
        method: GET
        url: /auth/status
        asserts:
            - ["status", "eq", 200]
    '''
    [打印], 内容: "✓ 认证服务正常"
end

function 收集系统信息 () do
    [打印], 内容: "=== 系统信息收集 ==="
    
    # 收集环境变量
    当前环境 = [获取全局变量], 变量名: "current_environment"
    [打印], 内容: "当前环境: ${当前环境}"
    
    # 收集版本信息
    [执行命令], 命令: "pytest-dsl --version"
    
    # 收集系统时间
    [执行命令], 命令: "date"
end
```

### 调试模式

```python
# 在测试中添加调试模式
@name: "调试模式测试"

调试模式 = [获取环境变量], 变量名: "DEBUG_MODE", 默认值: False

if ${调试模式} do
    [打印], 内容: "=== 调试模式已启用 ==="
    [收集系统信息]
    [诊断环境连通性]
end

# 测试逻辑...

if ${调试模式} do
    [打印], 内容: "=== 调试信息 ==="
    [打印], 内容: "变量状态: ${locals()}"
end
```

## 性能优化建议

### 测试执行优化

1. **并行执行**: 使用`--parallel`参数提高执行效率
2. **选择性执行**: 使用标签选择需要执行的测试
3. **数据预加载**: 在测试套件开始前准备共享数据
4. **资源复用**: 避免重复的环境初始化
5. **合理超时**: 设置适当的等待和超时时间

### 内存和资源管理

```python
# 在资源密集型测试中进行适当的清理
@name: "大数据量测试"

# 分批处理大量数据
批次大小 = 100
数据总量 = 10000

for 批次起始 in range(0, ${数据总量}, ${批次大小}) do
    批次结束 = min(${批次起始} + ${批次大小}, ${数据总量})
    
    [打印], 内容: "处理批次: ${批次起始}-${批次结束}"
    
    # 处理当前批次
    [处理数据批次], 起始: ${批次起始}, 结束: ${批次结束}
    
    # 适当休息，避免资源耗尽
    [等待], 秒数: 1
end

# 清理临时资源
teardown do
    [清理临时文件]
    [释放连接池]
end
```

## 总结

### 🎯 最佳实践要点

1. **优先使用pytest集成** - 获得完整的测试框架能力
2. **善用auto_dsl装饰器** - 简化DSL文件管理，自动转换为pytest测试
3. **合理选择组织策略** - 简单场景用目录形式，复杂场景可细化拆分  
4. **充分利用pytest生态** - fixture、标记、参数化、报告、插件
5. **数据驱动必须pytest** - `@data`指令只在pytest方式下生效

### 📈 价值体现

**通过pytest集成，pytest-dsl从单纯的DSL执行工具升级为完整的测试解决方案：**

```bash
# 🚀 强大的测试执行能力
pytest test_runner.py -m "smoke and api" -n auto --html=report.html

# 📊 丰富的报告和分析  
pytest test_runner.py --alluredir=results --tb=short --durations=10

# 🔧 灵活的测试控制
pytest test_runner.py --lf --pdb -k "auth"

# 🎯 精确的测试过滤
pytest test_runner.py -m "not slow" --maxfail=3
```

**核心优势总结：**

| 能力 | 直接运行DSL | pytest集成 |
|------|------------|------------|
| 定位 | 📝 DSL验证工具 | 🎯 完整测试框架 |
| 数据驱动 | ❌ 不支持 | ✅ 完全支持 |
| 测试组织 | ❌ 基础 | ✅ 专业化 |  
| 并行执行 | ❌ 不支持 | ✅ 多进程 |
| 测试报告 | ❌ 简单输出 | ✅ 专业报告 |
| 生态集成 | ❌ 无 | ✅ 完整生态 |

### 🎉 实施建议

1. **新项目** - 直接采用pytest集成方式，使用`auto_dsl`装饰器
2. **现有项目** - 逐步迁移到pytest方式，优先迁移数据驱动测试
3. **团队协作** - 建立pytest集成的规范和培训
4. **CI/CD** - 利用pytest的标记和过滤能力优化构建管道

通过遵循这些最佳实践，您可以构建高质量、可维护、易扩展的pytest-dsl测试项目，充分发挥pytest生态系统的强大能力，提高团队的测试效率和代码质量。 
