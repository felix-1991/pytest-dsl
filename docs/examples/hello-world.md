# Hello World

这是pytest-dsl最简单的入门示例，展示了框架的基本结构和核心概念。

## 学习目标

通过这个示例，您将学会：

- pytest-dsl文件的基本结构
- 如何定义和使用变量
- 如何调用内置关键字
- 如何运行DSL测试

## 示例代码

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

## 代码解析

### 元信息部分

```python
@name: "我的第一个测试"
@description: "学习pytest-dsl的第一步"
```

- `@name` - 定义测试用例的名称
- `@description` - 描述测试用例的目的

### 变量定义

```python
message = "Hello, pytest-dsl!"
count = 3
```

- 支持字符串、数字等基本数据类型
- 变量名使用下划线命名风格

### 关键字调用

```python
[打印], 内容: ${message}
```

- 使用方括号 `[]` 包围关键字名称
- 参数使用 `参数名: 值` 的格式
- 变量引用使用 `${变量名}` 语法

### 流程控制

```python
for i in range(1, ${count} + 1) do
    [打印], 内容: "第 ${i} 次循环"
end
```

- 支持Python风格的range循环
- 使用 `do...end` 包围循环体
- 循环变量可以在循环体内使用

### 断言验证

```python
[断言], 条件: "${count} == 3", 消息: "计数器应该等于3"
```

- 使用断言关键字进行验证
- 条件表达式使用字符串格式
- 可以提供自定义错误消息

### 清理操作

```python
teardown do
    [打印], 内容: "测试完成！"
end
```

- `teardown` 块在测试结束后执行
- 无论测试成功还是失败都会执行

## 运行示例

### 方法一：直接运行

```bash
pytest-dsl hello.dsl
```

### 方法二：使用pytest

```bash
# 创建pytest集成文件
echo 'from pytest_dsl.core.auto_decorator import auto_dsl

@auto_dsl("./")
class TestHello:
    pass' > test_hello.py

# 运行
pytest test_hello.py -v
```

## 预期输出

运行成功后，您应该看到类似这样的输出：

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

## 常见问题

### Q: 为什么要使用 `${变量名}` 语法？

A: 这是pytest-dsl的变量引用语法，类似于shell脚本中的变量引用。它让变量使用更加明确和安全。

### Q: 可以不写 `@name` 吗？

A: `@name` 是必需的，它定义了测试用例的名称，会在测试报告中显示。

### Q: `teardown` 是必需的吗？

A: `teardown` 是可选的，只有在需要清理操作时才使用。

## 练习建议

### 练习1：修改变量

尝试修改变量的值，观察输出变化：

```python
message = "你好，pytest-dsl！"
count = 5
```

### 练习2：添加更多变量

添加更多类型的变量：

```python
name = "张三"
age = 25
is_student = True
hobbies = ["编程", "阅读", "运动"]
```

### 练习3：使用变量

在打印中使用这些变量：

```python
[打印], 内容: "姓名: ${name}, 年龄: ${age}"
[打印], 内容: "是学生: ${is_student}"

# 注意：当前不支持 ${len(hobbies)} 语法，需要预定义长度
hobbies_length = 3

for i in range(0, ${hobbies_length}) do
    [打印], 内容: "爱好: ${hobbies[i]}"
end
```

### 练习4：添加更多断言

添加更多的断言验证：

```python
[断言], 条件: "${age} > 18", 消息: "年龄应该大于18"
[断言], 条件: "${is_student} == True", 消息: "应该是学生"
```

## 下一步

恭喜您完成了第一个pytest-dsl示例！现在您可以继续学习：

- **[基本语法](./basic-syntax)** - 深入了解DSL语法规则
- **[远程Hook机制](./remote-hooks)** - 了解高级功能

## 相关资源

- [DSL语法基础](/guide/dsl-syntax) - 完整的语法参考
- [内置关键字](/guide/builtin-keywords) - 了解所有可用的关键字
- [快速开始](/guide/getting-started) - 更多入门指导 