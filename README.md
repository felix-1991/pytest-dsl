# pytest-dsl: 强大的关键字驱动测试自动化框架

pytest-dsl是一个基于pytest的关键字驱动测试框架，使用自定义的领域特定语言(DSL)来编写测试用例，使测试更加直观、易读和易维护。它不仅限于API测试，更是一个可以应对各种测试场景的通用自动化框架。

## 快速入门

### 安装

```bash
# 使用 pip 安装
pip install pytest-dsl

# 或使用 uv 安装（推荐）
uv pip install pytest-dsl
```

### 第一个DSL测试

创建第一个DSL文件，命名为`hello.dsl`：

```python
message = "Hello, pytest-dsl!"

# 使用[打印]关键字输出消息
[打印],内容: ${message}

# 使用简单循环结构
for i in range(1, 3) do
    [打印],内容: "循环次数: ${i}"
end

@teardown do
    [打印],内容: "测试完成!"
end
```

### 直接运行DSL文件

安装pytest-dsl后，无需其他配置即可通过命令行直接执行DSL文件：

```bash
# 运行单个DSL文件
pytest-dsl hello.dsl

# 也可以执行目录下的所有DSL文件
pytest-dsl tests/
```

### 简单算术示例

创建`arithmetic.dsl`文件，测试基本运算：

```python
@name: "算术运算示例"

# 基本运算
a = 10
b = 5
sum = a + b
product = a * b

# 输出结果
[打印],内容: "a + b = ${sum}"
[打印],内容: "a * b = ${product}"

# 条件判断
if a > b do
    [打印],内容: "a 大于 b"
end
```

## 基础语法

### 变量与流程控制

pytest-dsl支持变量定义、条件判断和循环结构：

```python
@name: "测试变量定义、条件判断和循环结构"
# 变量定义
name = "pytest-dsl"
version = "1.0.0"

# 条件判断
if version == "1.0.0" do
    [打印],内容: "当前是正式版"
else
    [打印],内容: "当前是开发版"
end

# 循环结构
count = 3
for i in range(1, ${count}) do
    [打印],内容: "循环次数: ${i}"
end
```

### 内置关键字

DSL提供多种内置关键字满足基本测试需求：

```python
@name: 使用内置关键字
# 打印输出
[打印],内容: "测试开始执行"

# 断言测试
[断言],条件: "1 + 1 == 2",消息: "基本算术断言失败"
```

### 自定义关键字（函数）

pytest-dsl允许在DSL文件中直接定义自定义关键字，类似于编程语言中的函数：

```python
@name: "自定义关键字示例"

# 定义一个简单的关键字（函数）
@keyword 拼接字符串 (前缀, 后缀="默认后缀") do
    # 直接使用关键字参数
    [打印],内容: "拼接前缀: ${前缀} 和后缀: ${后缀}"
    
    # 保存到变量中
    结果变量 = "${前缀}${后缀}"
    [打印],内容: "拼接结果: ${结果变量}"
    
    # 返回结果
    return ${结果变量}
end

# 使用自定义关键字
问候语 = [拼接字符串],前缀: "你好, ",后缀: "世界"
[打印],内容: ${问候语}  # 输出: 你好, 世界

# 只传递必要参数，使用默认值
简单问候 = [拼接字符串],前缀: "你好"
[打印],内容: ${简单问候}  # 输出: 你好默认后缀
```

自定义关键字可以保存在独立的资源文件中（`.resource`），通过`@import`导入使用：

```python
# 导入资源文件
@import: "path/to/common_utils.resource"

# 使用导入的关键字
结果 = [拼接字符串],前缀: "开始",后缀: "结束"
```

资源文件的定义示例（`common_utils.resource`）：

```python
@name: 通用工具关键字
@description: 包含一些常用的工具关键字
@author: Felix
@date: 2024-06-11

@keyword 拼接字符串 (前缀, 后缀="我是默认值哦") do
    # 直接使用关键字参数
    [打印],内容:'拼接前缀: ${前缀} 和后缀: ${后缀}'
    
    # 保存到变量中
    结果变量 = "${前缀}${后缀}"
    [打印],内容:'拼接结果: ${结果变量}'
    
    # 返回结果
    return ${结果变量}
end

@keyword 计算长度 (文本) do
    # 在实际场景中，可能会使用更复杂的逻辑
    [打印],内容:'计算文本: ${文本} 的长度'
    长度 = 10  # 为简化示例，这里使用固定值
    [打印],内容:'计算得到长度: ${长度}'
    return ${长度}
end
```

## API测试示例

创建`api_test.dsl`文件进行简单的API测试：

```python
@name: "API测试示例"
@description: "演示基本的API接口测试"
@tags: ["API", "HTTP"]

# 执行GET请求
[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/1
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.id", "eq", 1]
''',步骤名称: "获取文章详情"

# 捕获响应数据
[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts
    request:
        params:
            userId: 1
    captures:
        post_count: ["jsonpath", "$", "length"]
    asserts:
        - ["status", "eq", 200]
''',步骤名称: "获取用户文章列表"

# 输出捕获的变量
[打印],内容: "用户文章数量: ${post_count}"
```

在实际测试文件中使用导入的关键字示例（`custom_test.dsl`）：

```python
@name: 自定义关键字测试
@description: 测试自定义关键字功能
@tags: [测试, 自定义关键字]
@author: Felix
@date: 2024-06-11

# 导入资源文件
@import: "resources/common_utils.resource"

# 定义测试输入参数
前缀值 = "你好, "
后缀值 = "世界"

# 测试拼接字符串关键字
[打印],内容:'测试拼接字符串关键字'
拼接结果 = [拼接字符串],前缀:${前缀值},后缀:${后缀值}
[打印],内容:'获取到拼接结果: ${拼接结果}'

# 使用默认参数
拼接结果2 = [拼接字符串],前缀:"hello"
[打印],内容:'获取到拼接结果2: ${拼接结果2}'

# 测试第二个关键字
[打印],内容:'测试计算长度关键字'
测试文本 = "这是测试文本"
文本长度 = [计算长度],文本:${测试文本}
[打印],内容:'获取到文本长度: ${文本长度}'

# 测试断言
[断言],条件:'${拼接结果} == "你好, 世界"',消息:'字符串拼接不匹配'
[断言],条件:'${文本长度} == 10',消息:'长度不匹配'

@teardown do
    [打印],内容:'自定义关键字测试完成'
end
```

## 使用YAML变量文件

创建`variables.yaml`文件管理测试配置：

```yaml
# variables.yaml
api:
  base_url: "https://jsonplaceholder.typicode.com"
  timeout: 30
```

执行测试时加载变量文件：

```bash
pytest-dsl api_test.dsl --yaml-vars variables.yaml
```

## 与pytest集成

除了直接使用命令行工具外，pytest-dsl还可以与pytest无缝集成，扩展测试能力。

### 创建pytest测试类

```python
# test_api.py
from pytest_dsl.core.auto_decorator import auto_dsl

@auto_dsl("./api_tests")  # 加载指定目录下所有的.auto或.dsl文件
class TestAPI:
    """API测试类
    
    该类将自动加载api_tests目录下的所有DSL文件作为测试方法
    """
    pass
```

### 使用pytest运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest test_api.py

# 使用pytest参数和插件
pytest -v --alluredir=./reports
```

## 更多功能

### 断言重试功能

对于异步API或需要一定处理时间的请求，可以使用断言重试功能：

```python
[HTTP请求],客户端: "default",配置: '''
    method: GET
    url: https://httpbin.org/delay/2
    asserts:
        - ["status", "eq", 200]
        - ["response_time", "lt", 1000]  # 这个断言可能失败
''',断言重试次数: 3,断言重试间隔: 1
```

### 数据驱动测试

使用CSV文件测试多组数据：

```python
@name: "批量测试"
@data: "test_data.csv" using csv

# 使用CSV数据中的"username"和"password"列
[HTTP请求],客户端: "default",配置: '''
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

## 自定义关键字

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
    """调用内部微服务接口"""
    service = kwargs.get('service_name')
    method = kwargs.get('method_name')
    params = kwargs.get('params', {})
    context = kwargs.get('context')
    
    # 实现微服务调用逻辑
    result = your_microservice_client.call(service, method, params)
    return result
```

## 完整项目结构

```
测试项目/
├── keywords/          # 自定义关键字
│   └── api_keywords.py
├── tests/             # 测试用例
│   ├── test_api.py    # 使用@auto_dsl装饰器的测试类
│   └── api_tests/     # DSL测试文件目录
│       ├── login.dsl
│       └── users.dsl
├── vars/              # 变量文件
│   ├── dev.yaml       # 开发环境配置
│   └── prod.yaml      # 生产环境配置
└── pytest.ini         # pytest配置
```

## 为什么选择pytest-dsl？

- **降低自动化门槛**：不需要专业编程技能也能编写自动化测试
- **关注测试逻辑**：不必纠结于编程细节，专注业务测试逻辑
- **统一测试框架**：通过扩展关键字包覆盖多种测试类型
- **无缝集成pytest**：兼容pytest的所有插件和功能
- **可定制性强**：通过自定义关键字实现任何特定领域的测试需求
- **旁路模式扩展**：不干扰现有测试代码，可平滑演进

## 核心优势

- **关键字驱动架构**：使用高级抽象关键字描述测试步骤，无需编写复杂代码
- **易读的DSL语法**：自然语言风格的测试描述，降低学习门槛
- **高度可扩展**：轻松创建自定义关键字满足特定领域需求
- **统一测试框架**：通过扩展关键字包支持多种测试类型
- **完整测试生命周期**：内置teardown、变量管理和断言机制
- **非侵入式设计**：以"旁路模式"扩展现有pytest项目，不影响原有测试代码

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