# pytest-dsl

pytest-dsl是一个基于pytest的测试框架，它使用自定义的领域特定语言(DSL)来编写测试用例，使测试更加直观、易读和易维护。

## 特性

- 使用简洁直观的DSL语法编写测试用例
- 支持中文关键字和参数，提高可读性
- 自动集成到pytest测试框架
- 支持测试用例元数据管理（名称、描述、标签等）
- 支持变量、循环等基本编程结构
- 支持YAML格式的外部变量文件
- 支持数据驱动测试（CSV格式）
- 支持setup和teardown机制
- 支持并行测试执行(pytest-xdist)
- 集成Allure报告
- 支持配置式HTTP断言重试（支持全局和断言级别重试策略）

## 包安装与使用

### 安装

pytest-dsl 现在已经采用标准的 Python 包结构，支持使用 pip 或 uv 进行安装：

```bash
# 使用 uv 安装（推荐）
uv pip install pytest-dsl

# 或使用传统的 pip 安装
pip install pytest-dsl
```

开发模式安装：

```bash
# 克隆仓库
git clone https://github.com/yourusername/pytest-dsl.git
cd pytest-dsl

# 使用 uv 安装（推荐）
uv pip install -e .

# 或使用传统的 pip 安装
pip install -e .
```

### 命令行工具

安装后可以直接使用命令行工具执行 DSL 文件：

```bash
pytest-dsl your_test_file.auto
```

### 配置虚拟环境

如果你是项目贡献者，可以使用提供的脚本快速设置开发环境：

```bash
bash setup_env.sh
```

## 项目结构

```
pytest-dsl/
├── pytest_dsl/         # 主包目录
│   ├── core/           # 核心模块（解析器、执行器等）
│   ├── keywords/       # 关键字定义模块
│   ├── examples/       # 示例代码
│   ├── docs/           # 文档
│   ├── __init__.py     # 包初始化文件
│   ├── plugin.py       # pytest 插件入口
│   └── cli.py          # 命令行工具入口
├── tests/              # 测试目录
│   ├── test_core/      # 核心模块测试
│   └── test_keywords/  # 关键字模块测试
├── pyproject.toml      # 项目元数据和构建配置
├── setup.py            # 兼容旧版安装工具
├── MANIFEST.in         # 包含非Python文件的配置
└── README.md           # 项目说明文档
```

## 自定义关键字

除了使用内置关键字外，pytest-dsl还支持以下方式创建和使用自定义关键字：

1. **项目本地关键字**：在项目根目录下创建`keywords`目录，添加自定义关键字模块
2. **插件式关键字**：通过Python的entry_points机制注册的第三方插件

### 项目本地关键字（推荐）

当您将pytest-dsl用于自己的项目时，只需在项目根目录创建一个`keywords`目录，添加您的关键字模块即可：

```
您的项目/
├── keywords/           # 自定义关键字目录
│   ├── __init__.py     # 可选
│   ├── web_keywords.py # Web测试关键字
│   └── db_keywords.py  # 数据库测试关键字
├── tests/              # 测试目录
│   └── test_cases.auto # DSL测试用例
└── pytest.ini          # pytest配置
```

pytest-dsl会自动发现并加载您项目中的关键字，无需额外配置。

### 关键字编写示例

关键字模块中使用`keyword_manager.register`装饰器来注册自定义关键字：

```python
# keywords/db_keywords.py
from pytest_dsl.core.keyword_manager import keyword_manager

@keyword_manager.register('数据库查询', [
    {'name': 'SQL', 'mapping': 'sql', 'description': 'SQL查询语句'},
    {'name': '数据库', 'mapping': 'db', 'description': '数据库连接名称'}
])
def query_database(**kwargs):
    """执行数据库查询
    
    Args:
        sql: SQL查询语句
        db: 数据库连接名称
        context: 测试上下文(自动传入)
    """
    sql = kwargs.get('sql')
    db = kwargs.get('db', 'default')
    context = kwargs.get('context')
    
    # 实现数据库查询逻辑
    # ...
    
    return result
```

详细文档请参阅 [自定义关键字指南](./pytest_dsl/docs/custom_keywords.md)。

## DSL语法

### 基本结构

测试用例使用`.auto`文件编写，基本结构如下：

```
@name: 测试用例名称
@description: 测试用例描述
@tags: [标签1, 标签2]
@author: 作者
@date: 创建日期

# 测试步骤
[关键字],参数1:值1,参数2:值2

@teardown do
    # 清理操作
end
```

### 元信息

元信息部分用于描述测试用例的基本信息：

```
@name: 登录功能测试
@description: 验证用户登录功能
@tags: [BVT, 自动化]
@author: Felix
@date: 2023-01-01
```

### 变量管理

#### DSL内变量声明与使用

```
# 变量赋值
number = 5

# 变量引用
[打印],内容:${number}
```

#### YAML变量文件

您可以使用YAML文件来管理测试变量，支持多文件和目录方式加载。YAML变量优先级高于DSL中定义的变量。

##### YAML文件格式

```yaml
# vars.yaml
test_data:
  username: "testuser"
  password: "password123"
  
api_config:
  base_url: "https://api.example.com"
  timeout: 30

environment: "staging"
```

##### 使用YAML变量

在DSL文件中可以直接引用YAML文件中定义的变量：

```
# test.auto
[API接口调用],
    URL:'${api_config.base_url}/login',
    请求参数:'{"username":"${test_data.username}","password":"${test_data.password}"}'
```

##### 加载YAML变量文件

可以通过命令行参数指定YAML变量文件：

```bash
# 加载单个变量文件
pytest --yaml-vars vars.yaml

# 加载多个变量文件（后加载的文件会覆盖先加载文件中的同名变量）
pytest --yaml-vars common_vars.yaml --yaml-vars env_vars.yaml

# 加载目录中的所有YAML文件
pytest --yaml-vars-dir ./test_vars

# 同时使用文件和目录
pytest --yaml-vars-dir ./common_vars --yaml-vars specific_vars.yaml
```

### 循环结构

```
for i in range(1, 5) do
    [打印],内容:'第${i}次循环'
end
```

### 关键字调用

```
# 基本格式：[关键字],参数名1:值1,参数名2:值2
[打印],输出:'Hello World'
[API接口调用],方法:GET,URL:'https://api.example.com',请求头:'{"Content-Type":"application/json"}'

# 使用自定义步骤名称
[HTTP请求],客户端:'default',配置:'...',步骤名称:'获取用户信息'
[HTTP请求],客户端:'default',配置:'...',步骤名称:'创建新文章'
```

### 自定义步骤名称

在 DSL 中，每个关键字调用都可以通过 `步骤名称` 参数来自定义在测试报告中显示的步骤名称。这对于提高测试报告的可读性和维护性非常有帮助。

#### 使用场景

1. 为 HTTP 请求添加有意义的步骤名称：
```
[HTTP请求],客户端:'default',配置:'''
    method: GET
    url: https://api.example.com/users/1
''',步骤名称:'获取用户详细信息'
```

2. 为断言添加描述性名称：
```
[HTTP请求],客户端:'default',配置:'''
    method: GET
    url: https://api.example.com/posts
    asserts:
        - ["status", "eq", 200]
        - ["jsonpath", "$.length()", "gt", 0]
''',步骤名称:'验证文章列表API'
```

3. 为复杂操作添加清晰的步骤说明：
```
[HTTP请求],客户端:'default',配置:'''
    method: POST
    url: https://api.example.com/tasks
    request:
        json:
            type: "data_analysis"
            dataset: "sample123"
''',步骤名称:'创建数据分析任务'
```

自定义步骤名称会显示在 Allure 测试报告中，使测试步骤更加清晰易懂。如果不指定步骤名称，将使用默认的关键字名称作为步骤名称。

### 清理操作

```
@teardown do
    [打印],内容:'测试结束，开始清理'
    [删除文件],路径:'/tmp/test.txt'
end
```

### 数据驱动测试

DSL支持使用CSV文件进行数据驱动测试。在测试用例中使用`@data`标记指定数据源：

```
@name: 用户注册测试
@description: 验证不同用户数据的注册功能
@tags: [数据驱动, 自动化]
@author: Felix
@date: 2024-03-05
@data: 'test_data/register_users.csv' using csv

# 使用CSV中的数据进行注册
[API接口调用],
    方法:POST,
    URL:'https://example.com/register',
    请求头:'{"Content-Type":"application/json"}',
    请求参数:'{"username":"${username}","email":"${email}","password":"${password}"}'

# 验证注册结果
result = [获取响应状态码]
[断言],条件:'${result} == 200',消息:'注册失败'

@teardown do
    [打印],内容:'清理用户数据'
end
```

#### CSV文件格式

数据文件 `test_data/register_users.csv` 的内容示例：

```csv
username,email,password
user1,user1@example.com,pass123
user2,user2@example.com,pass456
user3,user3@example.com,pass789
```

测试框架会自动读取CSV文件，并为每组数据执行一次测试用例。CSV文件的列名会自动映射为测试用例中可用的变量。

## 目录结构

测试目录可以包含以下特殊文件：

- `setup.auto`: 目录级别的setup，在该目录下所有测试执行前运行一次
- `teardown.auto`: 目录级别的teardown，在该目录下所有测试执行后运行一次
- `*.auto`: 普通测试文件，每个文件会被转换为一个测试用例

## 使用方法

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定目录下的测试
pytest tests/login/

```

### 示例

以下是一个完整的测试用例示例：

```
@name: 断言关键字示例
@description: 演示不同断言关键字的使用方法
@tags: [断言, JSON, 示例]
@author: Felix
@date: 2024-01-01

# 基本断言示例
[断言],条件:'1 + 1 == 2',消息:'基本算术断言失败'

# 字符串断言
str_value = "Hello, World!"
[断言],条件:'${str_value} contains "Hello"',消息:'字符串包含断言失败'

# 数字比较
num1 = 10
num2 = 5
[数据比较],实际值:${num1},预期值:${num2},操作符:'>',消息:'数字比较断言失败'

# 类型断言
[类型断言],值:${str_value},类型:'string',消息:'类型断言失败'
[类型断言],值:${num1},类型:'number',消息:'类型断言失败'

# JSON数据处理
json_data = '{"user": {"name": "张三", "age": 30, "roles": ["admin", "user"], "address": {"city": "北京", "country": "中国"}}}'

# JSON提取示例
username = [JSON提取],JSON数据:${json_data},JSONPath:'$.user.name',变量名:'username'
[断言],条件:'${username} == "张三"',消息:'JSON提取断言失败'

# JSON断言示例
[JSON断言],JSON数据:${json_data},JSONPath:'$.user.age',预期值:30,操作符:'==',消息:'JSON断言失败：年龄不匹配'

[JSON断言],JSON数据:${json_data},JSONPath:'$.user.roles[0]',预期值:'admin',消息:'JSON断言失败：角色不匹配'

# 复杂JSON断言
[JSON断言],JSON数据:${json_data},JSONPath:'$.user.address.city',预期值:'北京',消息:'JSON断言失败：城市不匹配'

# 布尔值断言
bool_value = True
[断言],条件:'${bool_value} == True',消息:'布尔值断言失败'

@teardown do
    [打印],内容:'所有断言测试通过!'
end 
```

## 扩展关键字

您可以通过在`keywords`目录下添加新的Python模块来扩展关键字库。每个关键字需要使用`@keyword`装饰器注册。


## 测试上下文（Context）

测试上下文是一个在测试用例生命周期内共享的对象，用于在关键字之间传递和共享数据。每个测试用例都有自己独立的上下文，并在测试结束时自动清理。

### 上下文的生命周期

- 创建：每个测试用例开始执行时创建新的上下文
- 共享：测试用例中的所有关键字都可以访问同一个上下文
- 清理：测试用例结束时（包括teardown之后）自动清理

### 在关键字中使用上下文

每个关键字都会自动接收到 `context` 参数，可以通过以下方法操作上下文：

```python
def my_keyword(context, **kwargs):
    # 存储数据到上下文
    context.set('key', value)
    
    # 从上下文获取数据
    value = context.get('key')
    
    # 检查键是否存在
    if context.has('key'):
        # 处理逻辑
        pass
```

### 注意事项

1. 上下文对象在测试用例之间是相互隔离的
2. teardown 执行后上下文会被自动清理
3. 建议在 teardown 中主动清理重要资源
4. 上下文中的数据仅在当前测试用例中有效



## 贡献

欢迎提交问题和功能请求！

### 开发流程

1. Fork 存储库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开 Pull Request

### 编码规范

- 使用 [black](https://github.com/psf/black) 进行代码格式化
- 使用 [isort](https://github.com/PyCQA/isort) 对导入语句排序
- 编写适当的测试用例

### 断言重试功能

pytest-dsl支持强大的HTTP断言重试功能，特别适用于测试异步API或状态变化的场景。现在提供了更清晰的配置方式：

1. 使用独立的`retry_assertions`配置块（推荐）
2. 为特定断言设置独立的重试策略
3. 混合使用全局和断言级别的重试配置

#### 示例：独立的断言重试配置

```yaml
# HTTP请求配置
method: GET
url: https://api.example.com/tasks/123

# 断言定义
asserts:
  - ["status", "eq", 200]  # 索引0
  - ["jsonpath", "$.status", "eq", "completed"]  # 索引1
  - ["jsonpath", "$.result", "exists"]  # 索引2

# 独立的断言重试配置（推荐）
retry_assertions:
  count: 3                # 全局重试次数
  interval: 1             # 全局重试间隔（秒）
  all: true               # 是否重试所有断言
  indices: [1, 2]         # 指定要重试的断言索引
  specific:               # 针对特定断言的重试配置
    "1": {                # 索引1的断言特定配置
      count: 5,           # 特定重试次数
      interval: 2         # 特定重试间隔
    }
```
详细文档请参阅 [HTTP断言重试指南](./docs/http_assertion_retry.md)。