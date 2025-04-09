# 创建自定义关键字

## 概述

pytest-dsl 允许用户在自己的项目中创建自定义关键字，无需修改插件本身的代码。这使得您可以针对自己的项目需求，扩展 DSL 的功能。

## 自动扫描机制

pytest-dsl 会自动扫描并导入以下位置的关键字：

1. 内置关键字（插件自带的）
2. 通过 `entry_points` 机制注册的第三方插件关键字
3. **用户项目中的 `keywords` 目录下的关键字模块**

## 目录结构

要创建自定义关键字，只需在您的项目根目录下创建一个 `keywords` 目录，并在其中添加 Python 模块：

```
项目根目录/
  ├── keywords/                 # 关键字根目录
  │   ├── __init__.py          # 可选，如果要作为包导入
  │   ├── my_keywords.py       # 顶层关键字模块
  │   ├── another_module.py    # 顶层关键字模块
  │   └── web/                 # 子目录（可选作为子包）
  │       ├── __init__.py      # 可选，如果要作为子包导入
  │       └── selenium_keywords.py  # 子目录中的关键字模块
  ├── tests/                    # 测试目录
  │   └── test_dsl.py          # 使用 pytest-dsl 运行的测试
  └── pytest.ini               # pytest 配置文件
```

## 创建自定义关键字

在 `keywords` 目录下的任何 Python 文件中，您都可以使用 `keyword_manager.register` 装饰器来注册自定义关键字。

### 基本示例

```python
from pytest_dsl.core.keyword_manager import keyword_manager

@keyword_manager.register('打印消息', [
    {'name': '消息', 'mapping': 'message', 'description': '要打印的消息内容'},
])
def print_message(**kwargs):
    """打印一条消息到控制台
    
    Args:
        message: 要打印的消息
        context: 测试上下文 (自动传入)
    """
    message = kwargs.get('message', '')
    print(f"自定义关键字消息: {message}")
    return True
```

### 带返回值的关键字

```python
@keyword_manager.register('生成随机数', [
    {'name': '最小值', 'mapping': 'min_value', 'description': '随机数范围最小值'},
    {'name': '最大值', 'mapping': 'max_value', 'description': '随机数范围最大值'},
])
def generate_random(**kwargs):
    """生成指定范围内的随机整数
    
    Args:
        min_value: 最小值
        max_value: 最大值
        context: 测试上下文 (自动传入)
        
    Returns:
        随机整数
    """
    import random
    min_value = int(kwargs.get('min_value', 1))
    max_value = int(kwargs.get('max_value', 100))
    
    result = random.randint(min_value, max_value)
    return result
```

## 参数说明

在注册关键字时，您需要提供参数的定义列表：

```python
@keyword_manager.register('关键字名称', [
    {'name': '中文参数名', 'mapping': '英文参数名', 'description': '参数描述'},
    # 更多参数...
])
```

- `name`: 中文参数名，用在 DSL 文件中调用该关键字时使用
- `mapping`: 英文参数名，映射到函数参数名
- `description`: 参数描述，用于生成文档

## 使用上下文

每个关键字函数都会自动接收一个 `context` 参数，这是测试运行时的上下文对象：

```python
@keyword_manager.register('保存到上下文', [
    {'name': '键名', 'mapping': 'key', 'description': '保存在上下文中的键名'},
    {'name': '值', 'mapping': 'value', 'description': '要保存的值'},
])
def save_to_context(**kwargs):
    """将值保存到测试上下文中"""
    key = kwargs.get('key')
    value = kwargs.get('value')
    context = kwargs.get('context')
    
    if key and context:
        context.set(key, value)
        return True
    return False
```

## 在 DSL 中使用自定义关键字

一旦您注册了自定义关键字，就可以在 DSL 文件中使用它们：

```
# 测试: 自定义关键字演示
@name 自定义关键字测试
@description 演示如何使用自定义关键字

# 使用自定义关键字
打印消息 消息="这是一条自定义消息"

# 带返回值的关键字
随机数 = 生成随机数 最小值=1 最大值=100

# 打印结果
打印消息 消息="生成的随机数是: ${随机数}"
```

## 更多示例

查看 `pytest_dsl/examples/keyword_example.py` 文件获取更多示例。 