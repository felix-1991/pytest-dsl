# pytest-dsl: 强大的关键字驱动测试自动化框架

pytest-dsl是一个基于pytest的关键字驱动测试框架，使用自定义的领域特定语言(DSL)来编写测试用例，使测试更加直观、易读和易维护。它不仅限于API测试，更是一个可以应对各种测试场景的通用自动化框架。

## 核心优势

- **关键字驱动架构**：使用高级抽象关键字描述测试步骤，无需编写复杂代码
- **易读的DSL语法**：自然语言风格的测试描述，降低学习门槛
- **高度可扩展**：轻松创建自定义关键字满足特定领域需求
- **统一测试框架**：通过扩展关键字包支持多种测试类型
- **完整测试生命周期**：内置teardown、变量管理和断言机制
- **非侵入式设计**：以"旁路模式"扩展现有pytest项目，不影响原有测试代码

## 与pytest的无缝集成

pytest-dsl采用装饰器模式与pytest框架无缝集成，这意味着：

1. **保留pytest的全部能力**：所有pytest的插件、钩子、参数化等功能都可以继续使用
2. **非侵入式设计**：可以在不修改现有测试代码的情况下，添加DSL测试
3. **混合测试模式**：可以在同一个项目中同时使用传统pytest测试和DSL测试

### 装饰器加载模式

```python
# test_api.py
from pytest_dsl.core.auto_decorator import auto_dsl

@auto_dsl("./api_tests")  # 加载指定目录下所有的.auto文件
class TestAPI:
    """API测试类
    
    该类将自动加载api_tests目录下的所有.auto文件作为测试方法
    """
    pass
```

这种模式类似于BDD（行为驱动开发）框架，通过装饰器将DSL文件转换为标准的pytest测试方法，使其能被pytest识别和执行。

## 执行测试

pytest-dsl提供了两种方式执行测试：

### 1. 通过pytest命令

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest test_api.py

# 使用pytest参数
pytest -v --alluredir=./reports
```

### 2. 通过命令行工具

```bash
# 直接执行单个DSL文件
pytest-dsl path/to/test_file.auto

# 执行目录中的所有DSL文件
pytest-dsl path/to/test_dir/
```

### 加载YAML变量文件

```bash
# 加载单个变量文件
pytest --yaml-vars vars.yaml

# 加载多个变量文件
pytest --yaml-vars common_vars.yaml --yaml-vars env_vars.yaml

# 加载目录中的所有YAML文件
pytest --yaml-vars-dir ./test_vars
```

## 入门示例：API测试

让我们通过一个实际可运行的API测试例子快速了解pytest-dsl的语法风格：

```python
@name: API测试入门示例
@description: 演示基本的API接口测试用法
@tags: [API, HTTP, 入门]
@author: Felix
@date: 2024-01-01

# 基本GET请求
[HTTP请求],客户端:'default',配置:'''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/1
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.id", "eq", 1]
        - ["jsonpath", "$.title", "exists"]
''',步骤名称:'获取文章详情'

# 响应数据捕获与使用
[HTTP请求],客户端:'default',配置:'''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts
    request:
        params:
            userId: 1
    captures:
        first_post_id: ["jsonpath", "$[0].id"]
        post_count: ["jsonpath", "$", "length"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$", "type", "array"]
''',步骤名称:'获取用户文章列表'

# 打印捕获的变量
[打印],内容:'第一篇文章ID: ${first_post_id}, 文章总数: ${post_count}'

# POST请求创建资源
[HTTP请求],客户端:'default',配置:'''
    method: POST
    url: https://jsonplaceholder.typicode.com/posts
    request:
        headers:
            Content-Type: application/json
        json:
            title: 测试标题
            body: 测试内容
            userId: 1
    captures:
        new_post_id: ["jsonpath", "$.id"]
    asserts:
        - ["status", "eq", 201]
        - ["jsonpath", "$.title", "eq", "测试标题"]
''',步骤名称:'创建新文章'

@teardown do
    [打印],内容:'API测试完成!'
end
```

## 入门示例：变量与循环

loops.auto 文件展示了如何在测试中使用变量和循环结构：

```python
@name: 变量和循环示例
@description: 演示变量使用和循环结构
@tags: [变量, 循环, 入门]
@author: Felix
@date: 2024-01-01

# 基本变量定义和使用
name = "pytest-dsl"
version = "1.0.0"
[打印],内容:'测试框架: ${name}, 版本: ${version}'

# 循环结构示例
[打印],内容:'开始循环测试'
count = 3

for i in range(1, ${count}) do
    [打印],内容:'循环次数: ${i}'
end

[打印],内容:'循环结束'

@teardown do
    [打印],内容:'变量和循环测试完成!'
end
```

## 完整项目示例

下面是一个完整的项目结构，展示了如何组织pytest-dsl测试：

```
测试项目/
├── keywords/          # 自定义关键字
│   └── api_keywords.py
├── tests/
│   ├── test_api.py    # 使用@auto_dsl装饰器的测试类
│   └── api_tests/     # DSL测试文件目录
│       ├── login.auto
│       ├── user_management.auto
│       └── orders.auto
├── vars/
│   ├── dev.yaml       # 开发环境配置
│   └── prod.yaml      # 生产环境配置
└── pytest.ini         # pytest配置
```

其中`test_api.py`的内容可能如下：

```python
from pytest_dsl.core.auto_decorator import auto_dsl

@auto_dsl("./api_tests")
class TestAPI:
    """API测试类
    
    自动加载api_tests目录下的所有.auto文件作为测试方法
    """
    pass
```

## 当前内置关键字

pytest-dsl目前内置了以下几类关键字：

### 1. HTTP请求关键字

用于执行API接口测试，支持各种HTTP方法、请求配置、数据捕获和断言。

```python
# 完整的HTTP请求示例
[HTTP请求],客户端:'default',配置:'''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts
    request:
        params:
            _limit: 5
        headers:
            Accept: application/json
    captures:
        items: ["jsonpath", "$"]
        count: ["jsonpath", "$", "length"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$", "length", "lte", 5]
        - ["response_time", "lt", 3000]
''',步骤名称:'获取文章列表'
```

### 2. 断言关键字

用于验证测试结果是否符合预期，支持多种断言类型。

```python
# 基本断言
[断言],条件:'1 + 1 == 2',消息:'基本算术断言失败'

# 数字比较
num1 = 10
num2 = 5
[断言],条件:'${num1} > ${num2}',消息:'数字比较断言失败'

# JSON数据处理
json_data = '{"user": {"name": "张三", "age": 30, "roles": ["admin", "user"]}}'

# JSON断言示例
[JSON断言],JSON数据:${json_data},JSONPath:'$.user.age',预期值:30,操作符:'==',消息:'JSON断言失败：年龄不匹配'

# 类型断言
[类型断言],值:${json_data},类型:'string',消息:'类型断言失败'
```

### 3. 全局关键字

用于基本操作和流程控制。

```python
# 打印输出
[打印],内容:'测试开始执行'

# 暂停执行
[等待],时间:2  # 等待2秒

# 简单变量赋值和使用
result = 53
[打印],内容:'结果: ${result}'
```

## HTTP断言重试功能

对于异步API或需要一定处理时间的请求，pytest-dsl提供了断言重试功能：

```python
# 断言重试示例 - 模拟处理延迟
[HTTP请求],客户端:'default',配置:'''
    method: GET
    url: https://httpbin.org/delay/2
    request:
        params:
            task_id: ${task_id}
            _: ${timestamp}  # 添加时间戳防止缓存
    captures:
        url: ["jsonpath", "$.url"]
        task_details: ["jsonpath", "$.args"]
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.args.task_id", "eq", "${task_id}"]  # 这个断言一定会通过
        - ["response_time", "lt", 1000]  # 这个断言可能失败，因为延迟是2秒
''',断言重试次数: 3,断言重试间隔: 1
```

## 自定义关键字 - 框架的核心力量

pytest-dsl的真正强大之处在于能够轻松创建自定义关键字，扩展测试能力到任何领域：

```python
# keywords/my_keywords.py
from pytest_dsl.core.keyword_manager import keyword_manager

@keyword_manager.register('调用微服务', [
    {'name': '服务名', 'mapping': 'service_name', 'description': '微服务名称'},
    {'name': '方法名', 'mapping': 'method_name', 'description': '要调用的方法'},
    {'name': '参数', 'mapping': 'params', 'description': '调用参数'}
])
def call_microservice(**kwargs):
    """调用内部微服务接口
    
    Args:
        service_name: 微服务名称
        method_name: 方法名称
        params: 调用参数
        context: 测试上下文(自动传入)
    """
    service = kwargs.get('service_name')
    method = kwargs.get('method_name')
    params = kwargs.get('params', {})
    context = kwargs.get('context')
    
    # 实现微服务调用逻辑
    result = your_microservice_client.call(service, method, params)
    return result
```

通过自定义关键字，您可以轻松扩展框架能力，实现：
- 数据库测试
- UI自动化测试
- 文件系统操作
- 微服务测试
- 等更多领域的测试需求

## 快速安装

```bash
# 使用 pip 安装
pip install pytest-dsl

# 或使用 uv 安装（推荐）
uv pip install pytest-dsl
```

## 框架核心特性

### DSL语法结构

```python
@name: 测试用例名称
@description: 测试用例描述
@tags: [标签1, 标签2]
@author: 作者名
@date: 2024-05-01

# 变量定义
name = "pytest-dsl"
version = "1.0.0"
[打印],内容:'测试框架: ${name}, 版本: ${version}'

# 循环结构
count = 3
for i in range(1, ${count}) do
    [打印],内容:'循环次数: ${i}'
end

# 关键字调用示例
[HTTP请求],客户端:'default',配置:'''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/1
    asserts:
        - ["status", "eq", 200]
''',步骤名称:'获取数据'

@teardown do
    # 清理操作
    [打印],内容:'测试完成!'
end
```

### 数据驱动测试

使用CSV文件测试多组数据：

```python
@name: 批量测试
@data: 'test_data.csv' using csv

# 使用CSV数据中的"username"和"password"列
[HTTP请求],客户端:'default',配置:'''
    method: POST
    url: https://example.com/api/login
    request:
        json:
            username: "${username}"
            password: "${password}"
    asserts:
        - ["status", "eq", ${expected_status}]
'''
```

### 变量管理

使用YAML文件管理不同环境的配置：

```yaml
# environments.yaml
test:
  base_url: "https://test-api.example.com"
  credentials:
    username: "test_user"
    password: "test_pass"

production:
  base_url: "https://api.example.com"
  credentials:
    username: "${PROD_USERNAME}"  # 从环境变量获取
    password: "${PROD_PASSWORD}"
```

## 测试项目结构

```
测试项目/
├── keywords/          # 自定义关键字
│   └── api/           # API测试关键字
├── tests/             # 测试用例
│   ├── test_api.py    # 使用@auto_dsl装饰器的测试类
│   └── api/           # DSL测试文件目录
│       ├── login.auto
│       └── users.auto
├── vars/              # 变量文件
│   ├── dev.yaml       # 开发环境配置
│   └── prod.yaml      # 生产环境配置
└── pytest.ini         # pytest配置
```

## 未来扩展性

pytest-dsl的架构设计支持通过安装关键字包的方式进行扩展，未来将提供：

- 数据库测试关键字包
- UI自动化测试关键字包
- 文件系统操作关键字包
- 更多垂直领域的专用关键字包

## 为什么选择pytest-dsl？

- **降低自动化门槛**：不需要专业编程技能也能编写自动化测试
- **关注测试逻辑**：不必纠结于编程细节，专注业务测试逻辑
- **统一测试框架**：通过扩展关键字包覆盖多种测试类型
- **无缝集成pytest**：兼容pytest的所有插件和功能
- **可定制性强**：通过自定义关键字实现任何特定领域的测试需求
- **旁路模式扩展**：不干扰现有测试代码，可平滑演进

## 进阶文档

- [完整DSL语法指南](./docs/自动化关键字DSL语法设计.md)
- [创建自定义关键字](./pytest_dsl/docs/custom_keywords.md) 
- [HTTP测试关键字](./docs/api.md)
- [断言关键字详解](./docs/assertion_keywords.md)
- [HTTP断言重试机制](./docs/http_assertion_retry.md)

## 贡献与支持

我们欢迎您的贡献和反馈！如有问题，请提交issue或PR。

## 许可证

MIT License

---

开始使用pytest-dsl，释放测试自动化的无限可能！ 