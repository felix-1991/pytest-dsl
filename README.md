# pytest-dsl 项目介绍

我将为您创建一个README.md文件，介绍您的pytest-dsl项目的DSL语法和使用方法。

```markdown:/Users/chenshuanglin/code/python/pytest-dsl/README.md
# pytest-dsl

pytest-dsl是一个基于pytest的测试框架，它使用自定义的领域特定语言(DSL)来编写测试用例，使测试更加直观、易读和易维护。

## 特性

- 使用简洁直观的DSL语法编写测试用例
- 支持中文关键字和参数，提高可读性
- 自动集成到pytest测试框架
- 支持测试用例元数据管理（名称、描述、标签等）
- 支持变量、循环等基本编程结构
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

### 变量声明与使用

```
# 变量赋值
number = 5

# 变量引用
[打印内容],内容:${number}
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
- `keywords/`: 内置关键字实现
- `conftest.py`: pytest集成
- `tests/`: 测试用例目录

## 贡献

欢迎提交问题和功能请求！
```

您可以使用以下命令创建README.md文件：

```bash
touch /Users/chenshuanglin/code/python/pytest-dsl/README.md
```

然后将上述内容复制到该文件中。这个README文件全面介绍了您的DSL语法和使用方法，包括：

1. 项目概述和特性
2. 安装说明
3. 详细的DSL语法说明（元信息、变量、循环、关键字调用、清理操作）
4. 目录结构说明
5. 使用方法和示例
6. 扩展方法
7. 项目结构

这个文档应该能够帮助新用户快速理解和使用您的pytest-dsl框架。