# 远程关键字返回处理器设计

## 概述

为了解决远程关键字返回值处理过于专用化的问题，我们设计了一个通用的返回处理器机制。这个机制允许不同类型的远程关键字自定义其返回数据的处理方式，而不需要在核心代码中硬编码特定的处理逻辑。

## 设计原则

1. **通用性**：支持任意类型的远程关键字扩展
2. **可扩展性**：通过插件化机制支持自定义处理器
3. **向后兼容**：保持与现有代码的兼容性
4. **解耦**：将特定类型的处理逻辑从核心代码中分离

## 核心组件

### 1. 返回处理器基类

```python
class RemoteReturnHandler(ABC):
    @abstractmethod
    def can_handle(self, return_data: Dict[str, Any]) -> bool:
        """判断是否能处理此返回数据"""
        pass
    
    @abstractmethod
    def process(self, return_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
        """处理返回数据"""
        pass
    
    @property
    @abstractmethod
    def priority(self) -> int:
        """处理器优先级，数字越小优先级越高"""
        pass
```

### 2. 通用返回格式

新的通用返回格式支持副作用处理：

```python
{
    "result": actual_result,           # 主要返回值
    "side_effects": {                  # 副作用处理
        "variables": {...},            # 变量注入
        "context_updates": {...}       # 上下文更新
    },
    "metadata": {...}                  # 元数据
}
```

### 3. 注册机制

```python
from pytest_dsl.remote.return_handlers import register_return_handler

# 注册自定义处理器
register_return_handler(MyCustomHandler())
```

## 内置处理器

### HTTPReturnHandler
处理HTTP请求关键字的返回数据，支持：
- 变量捕获 (`captures`)
- 会话状态 (`session_state`)
- 响应数据 (`response`)

### AssertionReturnHandler
处理断言关键字的返回数据，支持：
- JSONPath变量捕获
- 断言元数据

### DefaultReturnHandler
默认处理器，处理简单的返回格式，作为兜底机制。

## 使用示例

### 1. 创建自定义处理器

```python
class DatabaseReturnHandler(RemoteReturnHandler):
    def can_handle(self, return_data: Dict[str, Any]) -> bool:
        return (isinstance(return_data, dict) and 
                'db_result' in return_data)
    
    def process(self, return_data: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
        return {
            'result': return_data['db_result'],
            'side_effects': {
                'variables': return_data.get('query_variables', {}),
                'context_updates': {
                    'db_connection': return_data.get('connection_info', {})
                }
            },
            'metadata': {
                'affected_rows': return_data.get('affected_rows', 0),
                'keyword_type': 'database_operation'
            }
        }
    
    @property
    def priority(self) -> int:
        return 15
```

### 2. 注册处理器

```python
from pytest_dsl.remote.return_handlers import register_return_handler

register_return_handler(DatabaseReturnHandler())
```

### 3. 在远程关键字中使用新格式

```python
def my_database_keyword(query: str):
    # 执行数据库操作
    result = execute_query(query)
    
    # 返回新格式
    return {
        "result": result,
        "side_effects": {
            "variables": {"last_query_result": result},
            "context_updates": {
                "db_connection": {"status": "active"}
            }
        },
        "metadata": {
            "affected_rows": len(result),
            "keyword_type": "database_operation"
        }
    }
```

## 统一格式处理

系统统一使用新的格式，不再需要兼容层：

```python
# 统一的新格式
{
    "result": value,
    "side_effects": {
        "variables": {"var1": "value1"},
        "context_updates": {"session_state": {...}}
    },
    "metadata": {...}
}
```

远程关键字客户端会直接处理 `side_effects` 中的内容：
- `variables` 中的变量会被注入到执行器上下文
- `context_updates` 中的信息会更新相关上下文状态

## 扩展指南

### 1. 确定处理器类型
根据你的关键字类型，确定需要处理的特殊返回数据。

### 2. 实现处理器
继承 `RemoteReturnHandler` 并实现必要的方法。

### 3. 设置优先级
- 1-10: 高优先级（核心系统处理器）
- 11-50: 中等优先级（业务特定处理器）
- 51-99: 低优先级（通用处理器）
- 100+: 兜底处理器

### 4. 注册处理器
在适当的位置注册你的处理器。

### 5. 测试
确保你的处理器能正确处理预期的返回数据格式。

## 最佳实践

1. **明确职责**：每个处理器应该只处理特定类型的返回数据
2. **优先级设计**：合理设置优先级，避免冲突
3. **错误处理**：在处理器中添加适当的错误处理
4. **文档化**：为自定义处理器编写清晰的文档
5. **测试覆盖**：为处理器编写单元测试

## 使用指南

### 新关键字开发

所有新的远程关键字都应该使用统一的新格式：

```python
def my_remote_keyword():
    # 执行关键字逻辑
    result = do_something()

    # 返回新格式
    return {
        "result": result,
        "side_effects": {
            "variables": {"extracted_value": result},
            "context_updates": {
                "session_state": {...}
            }
        },
        "metadata": {
            "keyword_type": "my_keyword",
            "execution_time": 0.1
        }
    }
```

### 简化的处理流程

1. 远程关键字返回新格式数据
2. 返回处理器识别并处理数据
3. 客户端直接处理 `side_effects`：
   - 注入 `variables` 中的变量
   - 更新 `context_updates` 中的上下文
4. 返回 `result` 给调用方

## 总结

新的返回处理器机制提供了：

- **通用性**：不再局限于HTTP请求特定的字段
- **扩展性**：支持任意类型的自定义处理器
- **解耦**：将特定处理逻辑从核心代码中分离
- **兼容性**：保持与现有代码的完全兼容

这个设计解决了原有系统过于专用化的问题，为未来的扩展提供了良好的基础。
