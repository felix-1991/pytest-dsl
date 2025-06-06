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

## 第七步：批量运行测试

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
pytest-dsl my-tests/ --yaml-vars config.yaml --alluredir=reports
```

## 常用命令速查

```bash
# 基本运行
pytest-dsl test.dsl                    # 运行单个文件
pytest-dsl tests/                      # 运行目录
pytest-dsl tests/ -v                   # 详细输出

# 使用配置
pytest-dsl tests/ --yaml-vars config.yaml

# 生成报告
pytest-dsl tests/ --alluredir=reports  # Allure报告
pytest-dsl tests/ --html=report.html   # HTML报告

# 过滤测试
pytest-dsl tests/ -k "api"             # 运行名称包含"api"的测试
pytest-dsl tests/ --tags "smoke"       # 运行标记为"smoke"的测试

# 调试模式
pytest-dsl tests/ --debug              # 启用调试输出
pytest-dsl tests/ -s                   # 显示打印输出
```

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
pytest-dsl --list-keywords
```

### Q: 如何调试DSL文件？

A: 使用调试模式：

```bash
pytest-dsl test.dsl --debug -s
```

### Q: 如何在团队中共享自定义关键字？

A: 创建资源文件（`.resource`），详见[资源文件](./resource-files)章节。

### Q: 支持哪些数据格式？

A: 支持CSV、JSON、YAML等格式的数据驱动测试，详见[数据驱动测试](./data-driven)章节。

---

🎉 **恭喜您完成了快速开始教程！** 现在您已经掌握了pytest-dsl的基本使用方法，可以开始创建自己的测试项目了。 