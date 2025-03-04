# pytest-dsl

pytest-dsl是一个基于pytest的测试框架，它使用自定义的领域特定语言(DSL)来编写测试用例，使测试更加直观、易读和易维护。

## 特性

- 使用简洁直观的DSL语法编写测试用例
- 支持中文关键字和参数，提高可读性
- 自动集成到pytest测试框架
- 支持测试用例元数据管理（名称、描述、标签等）
- 支持变量、循环等基本编程结构
- 支持YAML格式的外部变量文件
- 支持setup和teardown机制
- 支持并行测试执行(pytest-xdist)
- 集成Allure报告

## 安装

```bash
pip install -r requirements.txt
```

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
@author: 陈双麟
@date: 2023-01-01
```

### 变量管理

#### DSL内变量声明与使用

```
# 变量赋值
number = 5

# 变量引用
[打印内容],内容:${number}
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
    [打印内容],内容:'第${i}次循环'
end
```

### 关键字调用

```
# 基本格式：[关键字],参数名1:值1,参数名2:值2
[打印],输出:'Hello World'
[API接口调用],方法:GET,URL:'https://api.example.com',请求头:'{"Content-Type":"application/json"}'
```

### 清理操作

```
@teardown do
    [打印内容],内容:'测试结束，开始清理'
    [删除文件],路径:'/tmp/test.txt'
end
```

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

# 并行运行测试
pytest -n 4
```

### 示例

以下是一个完整的测试用例示例：

```
@name: 登录功能测试
@description: 验证用户登录功能
@tags: [BVT, 自动化]
@author: 陈双麟
@date: 2023-01-01

# 设置测试数据
username = "testuser"
password = "password123"

# 执行登录操作
[API接口调用],方法:POST,URL:'https://example.com/login',请求头:'{"Content-Type":"application/json"}',请求参数:'{"username":"${username}","password":"${password}"}'

# 验证登录结果
result = [获取响应状态码]
[断言],条件:'${result} == 200',消息:'登录失败'

@teardown do
    [打印内容],内容:'测试结束，清理会话'
    [API接口调用],方法:POST,URL:'https://example.com/logout'
end
```

## 扩展关键字

您可以通过在`keywords`目录下添加新的Python模块来扩展关键字库。每个关键字需要使用`@keyword`装饰器注册。

## 项目结构

- `core/`: 核心实现，包括DSL解析器、执行器等
  - `global_context.py`: 全局变量管理
  - `yaml_vars.py`: YAML变量文件支持
  - `dsl_executor.py`: DSL执行器
  - `parser.py`: DSL解析器
  - `lexer.py`: DSL词法分析器
- `keywords/`: 内置关键字实现
- `conftest.py`: pytest集成
- `tests/`: 测试用例目录

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

### 实际应用示例

#### UI自动化测试

在UI自动化测试中，上下文可以用来存储和共享浏览器、页面对象等：

```
# test_login.auto
@name: 登录测试
@description: 测试用户登录功能

# 打开登录页面，自动将页面对象存储在上下文中
[打开页面],地址:'https://example.com/login',页面名称:'登录页面'

# 后续步骤可以直接获取已存在的页面对象
page = [获取页面],页面名称:'登录页面'

@teardown do
    # 清理浏览器资源
    [关闭浏览器]
end
```

在这个例子中：
1. `打开页面` 关键字会在上下文中存储：
   - 浏览器实例 (`browser`)
   - Playwright实例 (`playwright`)
   - 页面对象 (使用指定的页面名称)

2. `获取页面` 关键字可以从上下文中获取之前创建的页面对象
3. `关闭浏览器` 关键字会清理上下文中的所有资源

#### API测试中的会话管理

在API测试中，上下文可以用来管理会话信息：

```
# test_api.auto
@name: API测试
@description: 测试API接口

# 登录并将token存储在上下文中
[登录],用户名:'admin',密码:'123456'

# 后续请求使用上下文中的token
[API接口调用],
    方法:'GET',
    URL:'https://api.example.com/data',
    请求头:'{"Authorization": "${token}"}'
```

#### 数据库测试

在数据库测试中，上下文可以用来共享数据库连接：

```
# test_db.auto
@name: 数据库测试
@description: 测试数据库操作

# 创建数据库连接并存储在上下文中
[连接数据库],
    主机:'localhost',
    端口:'5432',
    数据库:'testdb'

# 使用同一个数据库连接执行查询
[执行查询],SQL:'SELECT * FROM users'

@teardown do
    # 关闭数据库连接
    [关闭数据库连接]
end
```

### 最佳实践

1. **资源管理**
   - 在测试开始时创建资源并存储在上下文中
   - 在teardown中清理资源
   - 使用有意义的键名存储对象

2. **命名约定**
   - 使用描述性的名称作为上下文键
   - 对于页面对象，使用 `page_name` 作为标识
   - 对于共享资源，使用统一的命名（如 `db_connection`, `api_client` 等）

3. **错误处理**
   - 在获取不存在的对象时提供清晰的错误信息
   - 在资源创建失败时及时清理已创建的资源

4. **性能考虑**
   - 避免在上下文中存储过大的数据
   - 及时清理不再需要的资源
   - 复用已创建的资源（如浏览器实例）

### 注意事项

1. 上下文对象在测试用例之间是相互隔离的
2. teardown 执行后上下文会被自动清理
3. 建议在 teardown 中主动清理重要资源
4. 上下文中的数据仅在当前测试用例中有效

## 贡献

欢迎提交问题和功能请求！