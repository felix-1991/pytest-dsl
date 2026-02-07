# 快速开始

欢迎来到pytest-dsl！本指南将在5分钟内带您体验pytest-dsl的核心功能。

## 第一步：安装

选择您喜欢的包管理器：

::: code-group

```bash [pip]
pip install pytest-dsl
```

```bash [uv (推荐)]
uv pip install pytest-dsl
```

```bash [pipx (全局安装)]
pipx install pytest-dsl
```

:::

::: tip 推荐使用uv
[uv](https://github.com/astral-sh/uv)是一个快速的Python包管理器，安装速度比pip快10-100倍。
:::

## 第二步：创建第一个测试

创建文件 `hello.dsl`：

```python
@name: "我的第一个测试"
@description: "学习pytest-dsl的第一步"

# 定义变量
message = "Hello, pytest-dsl!"
count = 3

# 打印欢迎消息
[打印], 内容: ${message}

# 简单循环
for i in range(1, ${count} + 1) do
    [打印], 内容: "第 ${i} 次循环"
end

# 测试断言
[断言], 条件: "${count} == 3", 消息: "计数器应该等于3"

teardown do
    [打印], 内容: "测试完成！"
end
```

## 第三步：运行测试

```bash
# 直接运行DSL文件
pytest-dsl hello.dsl
```

您应该看到类似这样的输出：

```
==================== pytest-dsl test session starts ====================
Running: hello.dsl

我的第一个测试
Hello, pytest-dsl!
第 1 次循环
第 2 次循环
第 3 次循环
测试完成！

==================== 1 passed in 0.05s ====================
```

🎉 **恭喜！** 您已经成功运行了第一个pytest-dsl测试！

## 第四步：尝试API测试

现在让我们尝试一个更实际的例子 - API测试。创建文件 `api_test.dsl`：

```python
@name: "API测试示例"
@description: "测试JSONPlaceholder API"

# 获取用户信息
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/users/1
    captures:
        user_name: ["jsonpath", "$.name"]
        user_email: ["jsonpath", "$.email"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.name", "exists"]
        - ["jsonpath", "$.email", "contains", "@"]
''', 步骤名称: "获取用户信息"

# 使用捕获的变量
[打印], 内容: "用户名: ${user_name}"
[打印], 内容: "邮箱: ${user_email}"

# 获取用户的文章
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts
    request:
        params:
            userId: 1
            _limit: 3
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$", "length", "eq", 3]
''', 步骤名称: "获取用户文章"

[打印], 内容: "API测试完成！"
```

运行API测试：

```bash
pytest-dsl api_test.dsl
```

## 第五步：创建自定义关键字

让我们创建一个可复用的关键字。创建文件 `custom_test.dsl`：

```python
@name: "自定义关键字示例"
@description: "学习如何创建和使用自定义关键字"

# 定义一个自定义关键字
function 获取用户信息 (用户ID=1) do
    [HTTP请求], 客户端: "default", 配置: '''
        method: GET
        url: https://jsonplaceholder.typicode.com/users/${用户ID}
        captures:
            user_name: ["jsonpath", "$.name"]
            user_email: ["jsonpath", "$.email"]
        asserts:
            - ["status", "eq", 200]
    ''', 步骤名称: "获取用户${用户ID}的信息"
    
    [打印], 内容: "用户${用户ID}: ${user_name} (${user_email})"
    return ${user_name}
end

# 使用自定义关键字
name1 = [获取用户信息], 用户ID: 1
name2 = [获取用户信息], 用户ID: 2
name3 = [获取用户信息]  # 使用默认值

[打印], 内容: "获取了3个用户的信息"
```

运行自定义关键字测试：

```bash
pytest-dsl custom_test.dsl
```

## 第六步：使用配置文件

创建配置文件 `config.yaml`：

```yaml
# 环境配置
environment: "development"
api_base_url: "https://jsonplaceholder.typicode.com"

# HTTP客户端配置
http_clients:
  default:
    base_url: "${api_base_url}"
    timeout: 30
    headers:
      User-Agent: "pytest-dsl/1.0"
      Accept: "application/json"

# 测试数据
test_users:
  - id: 1
    name: "admin"
  - id: 2
    name: "user"
```

创建使用配置的测试文件 `config_test.dsl`：

```python
@name: "配置文件示例"
@description: "使用YAML配置文件"

# 使用配置中的变量
[打印], 内容: "当前环境: ${environment}"
[打印], 内容: "API地址: ${api_base_url}"

# 循环测试多个用户
for user in ${test_users} do
    [HTTP请求], 客户端: "default", 配置: '''
        method: GET
        url: /users/${user.id}
        captures:
            user_name: ["jsonpath", "$.name"]
        asserts:
            - ["status", "eq", 200]
    ''', 步骤名称: "测试用户${user.name}"
    
    [打印], 内容: "用户${user.name}的真实姓名: ${user_name}"
end
```

使用配置文件运行：

```bash
pytest-dsl config_test.dsl --yaml-vars config.yaml
```

## 第七步：pytest集成（推荐方式）

### 为什么使用pytest集成？

**pytest-dsl是用于测试DSL文件的工具**，核心的自动化测试能力还是依靠pytest生态系统。使用pytest集成有以下优势：

- 🎯 **数据驱动支持**：只有pytest方式才支持数据驱动测试
- 📊 **丰富报告**：支持HTML、Allure等专业测试报告  
- 🔧 **灵活配置**：利用pytest的fixture、参数化等功能
- 🚀 **自动发现**：使用`auto_dsl`装饰器自动转换DSL文件为pytest测试
- ⚙️ **生态集成**：充分利用pytest插件生态系统

### 创建pytest测试运行器

创建文件 `test_runner.py`：

```python
# test_runner.py
from pytest_dsl.core.auto_decorator import auto_dsl

@auto_dsl("./tests")
class TestAPI:
    """自动加载tests目录下的所有DSL文件"""
    pass
```

### 目录结构

```
project/
├── test_runner.py           # pytest测试运行器
├── config.yaml              # 配置文件
└── tests/                   # DSL测试目录
    ├── hello.dsl
    ├── api_test.dsl
    ├── custom_test.dsl
    └── data_driven_test.dsl  # 数据驱动测试
```

### 运行pytest集成测试

```bash
# 基本运行
pytest test_runner.py -v

# 使用配置文件运行
pytest test_runner.py -v --yaml-vars config.yaml

# 生成HTML报告
pytest test_runner.py --html=report.html --self-contained-html

# 并行运行（需要安装pytest-xdist）
pip install pytest-xdist
pytest test_runner.py -n auto
```

## 第八步：数据驱动测试（仅限pytest方式）

::: warning 重要提示
**数据驱动测试只有在使用pytest方式运行时才会生效！**
使用`pytest-dsl`命令直接运行DSL文件时，数据驱动功能不会工作。
:::

### 创建测试数据

创建数据文件 `test_data.csv`：

```csv
username,password,expected_status,test_description
admin,admin123,200,管理员登录成功
user1,password123,200,普通用户登录成功
guest,guest123,403,访客权限不足
invalid_user,wrong_pass,401,无效用户登录失败
```

### 创建数据驱动测试

创建文件 `tests/data_driven_test.dsl`：

```python
@name: "数据驱动登录测试"
@description: "使用CSV数据测试不同用户的登录场景"
@data: "test_data.csv" using csv

[打印], 内容: "测试场景: ${test_description}"
[打印], 内容: "测试用户: ${username}"

# 模拟登录API调用
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: https://jsonplaceholder.typicode.com/posts
    request:
        json:
            username: "${username}"
            password: "${password}"
            title: "Login Test for ${username}"
    captures:
        response_status: ["status"]
    asserts:
        - ["status", "eq", ${expected_status}]
'''

[打印], 内容: "✓ ${test_description} - 期望状态码: ${expected_status}"
```

### 运行数据驱动测试

```bash
# 必须使用pytest方式运行，数据驱动才会生效
pytest test_runner.py -v --yaml-vars config.yaml

# 输出示例：
# test_runner.py::TestAPI::test_data_driven_test[admin-admin123-200-管理员登录成功] PASSED
# test_runner.py::TestAPI::test_data_driven_test[user1-password123-200-普通用户登录成功] PASSED
# test_runner.py::TestAPI::test_data_driven_test[guest-guest123-403-访客权限不足] PASSED
# test_runner.py::TestAPI::test_data_driven_test[invalid_user-wrong_pass-401-无效用户登录失败] PASSED
```

### 对比：直接运行vs pytest运行

```bash
# ❌ 直接运行DSL文件 - 数据驱动不生效，只执行一次
pytest-dsl tests/data_driven_test.dsl --yaml-vars config.yaml

# ✅ 使用pytest运行 - 数据驱动生效，每行数据执行一次
pytest test_runner.py -v --yaml-vars config.yaml
```

## 第九步：批量运行测试

创建测试目录结构：

```
my-tests/
├── config.yaml
├── basic/
│   ├── hello.dsl
│   └── variables.dsl
└── api/
    ├── users.dsl
    └── posts.dsl
```

运行整个目录的测试：

```bash
# 运行所有测试
pytest-dsl my-tests/ --yaml-vars config.yaml

# 只运行API测试
pytest-dsl my-tests/api/ --yaml-vars config.yaml

# 运行测试并生成报告
pytest-dsl my-tests/ --yaml-vars config.yaml
```

## 常用命令速查

### pytest方式运行（推荐）

```bash
# 基本运行（支持数据驱动）
pytest test_runner.py -v              # 详细输出
pytest test_runner.py --yaml-vars config.yaml  # 使用配置文件

# 高级功能
pytest test_runner.py --html=report.html --self-contained-html  # HTML报告
pytest test_runner.py --alluredir=reports  # Allure报告
pytest test_runner.py -k "api"        # 过滤测试
pytest test_runner.py -m "smoke"      # 运行标记测试
pytest test_runner.py -n auto         # 并行运行（需要pytest-xdist）

# 调试和详细输出
pytest test_runner.py -v -s           # 显示打印输出
pytest test_runner.py --pdb           # 失败时进入调试器
```

### 直接运行DSL文件（限制较多）

```bash
# 基本运行（不支持数据驱动）
pytest-dsl test.dsl                   # 运行单个文件
pytest-dsl tests/                     # 运行目录

# 使用配置
pytest-dsl tests/ --yaml-vars config.yaml
pytest-dsl tests/ --yaml-vars-dir config/
```

### 工具命令

```bash
# 查看关键字
pytest-dsl-list                       # 查看所有关键字
pytest-dsl-list --format text         # 文本格式输出
pytest-dsl-list --format html         # HTML格式输出
pytest-dsl-list --filter "HTTP"       # 过滤关键字
pytest-dsl-list --category builtin    # 查看内置关键字

# 远程服务器
pytest-dsl-server                     # 启动远程服务器
pytest-dsl-server --host 0.0.0.0 --port 8270  # 指定地址和端口
```

### 运行方式对比

**说明**：pytest-dsl是用于测试DSL文件的工具，核心自动化测试能力依靠pytest

| 功能 | pytest方式（推荐） | 直接运行方式（有限） |
|------|------------|-------------|
| 定位 | 🎯 完整的自动化测试框架 | 📝 DSL文件验证工具 |
| 数据驱动测试 | ✅ 支持 | ❌ 不支持 |
| 测试报告 | ✅ 丰富（HTML、Allure等） | ❌ 基础控制台输出 |
| 并行执行 | ✅ 支持 | ❌ 不支持 |
| 测试过滤 | ✅ 支持 | ❌ 不支持 |
| Fixture集成 | ✅ 支持 | ❌ 不支持 |
| CI/CD集成 | ✅ 依托pytest工作流 | ❌ 不支持 |
| 插件生态 | ✅ 完整pytest生态 | ❌ 无 |

## 下一步学习

现在您已经体验了pytest-dsl的基本功能，可以继续深入学习：

### 基础学习路径
1. **[安装配置](./installation)** - 详细的安装和环境配置
2. **[第一个测试](./first-test)** - 深入理解测试结构
3. **[DSL语法基础](./dsl-syntax)** - 学习完整的语法规则

### 进阶学习路径
1. **[HTTP API测试](./http-testing)** - 掌握API测试的完整流程
2. **[自定义关键字](./custom-keywords)** - 创建可复用的测试组件
3. **[环境配置管理](./configuration)** - 管理多环境配置

### 实际应用
1. **[示例库](/examples/)** - 查看更多实际应用案例
2. **[最佳实践](./best-practices)** - 学习项目组织和团队协作
3. **[pytest集成](./pytest-integration)** - 与现有项目集成

## 常见问题

### Q: 如何查看所有可用的关键字？

A: 使用帮助命令：

```bash
pytest-dsl-list
```

### Q: 为什么推荐使用pytest方式而不是直接运行DSL？

A: **pytest-dsl是用于测试DSL文件的工具，核心自动化测试能力来自pytest**。pytest方式支持更多高级功能：
- ✅ **数据驱动测试**：只有pytest方式才支持`@data`指令
- ✅ **专业报告**：HTML、Allure等丰富的测试报告
- ✅ **并行执行**：使用`pytest-xdist`进行并行测试
- ✅ **灵活过滤**：使用`-k`、`-m`等参数过滤测试
- ✅ **生态集成**：利用整个pytest插件生态系统

### Q: 数据驱动测试为什么不生效？

A: 请确保使用pytest方式运行：

```bash
# ❌ 错误方式 - 数据驱动不生效
pytest-dsl tests/data_driven_test.dsl

# ✅ 正确方式 - 数据驱动生效
pytest test_runner.py -v
```

### Q: 如何调试DSL文件？

A: 使用pytest的调试功能：

```bash
# 详细输出模式
pytest test_runner.py -v -s

# 失败时进入调试器
pytest test_runner.py --pdb

# 指定调试特定测试
pytest test_runner.py -k "test_name" -v -s
```

### Q: 如何在团队中共享自定义关键字？

A: 创建资源文件（`.resource`），详见[资源文件](./resource-files)章节。

### Q: 支持哪些数据格式？

A: 当前稳定支持CSV格式的数据驱动测试（**仅pytest方式**）。JSON、Excel等格式仍在规划中，详见[数据驱动测试](./data-driven)章节。

---

## 📝 重要总结

**pytest-dsl的定位**：
- 🎯 **DSL文件测试工具** - 专门用于测试DSL格式的测试文件
- ⚙️ **pytest增强器** - 为pytest添加DSL文件支持能力
- 🚀 **桥梁工具** - 连接DSL语法和pytest生态系统

**推荐使用方式**：
- ✅ **生产环境**：使用pytest集成方式，获得完整功能
- 📝 **快速验证**：使用直接运行方式，验证DSL文件语法
- 📊 **数据驱动**：必须使用pytest方式，直接运行不支持

🎉 **恭喜您完成了快速开始教程！** 现在您已经掌握了pytest-dsl的正确使用方法，可以开始创建自己的自动化测试项目了。 
