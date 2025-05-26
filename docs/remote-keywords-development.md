# 远程关键字开发指南

本文档指导开发者如何新增一个支持远程模式的关键字，以及在开发过程中需要注意的事项。

## 目录

- [概述](#概述)
- [设计原则](#设计原则)
- [开发步骤](#开发步骤)
- [返回格式规范](#返回格式规范)
- [最佳实践](#最佳实践)
- [测试验证](#测试验证)
- [常见问题](#常见问题)

## 概述

远程关键字允许在分布式环境中执行关键字，支持跨网络的测试执行。为了确保关键字在本地和远程模式下都能正常工作，需要遵循特定的设计规范。

## 设计原则

### 1. 解耦原则
- 移除通用逻辑中的特殊处理
- 每个关键字负责自己的特殊需求
- 避免在RemoteKeywordServer中添加针对特定关键字的逻辑

### 2. 主动返回原则
- 需要传递给客户端的数据应该主动作为返回值返回
- 不依赖被动的上下文处理机制
- 确保所有重要数据都能跨网络传输

### 3. 统一接口原则
- 所有关键字都应该遵循相同的输入输出接口规范
- 保持向后兼容性
- 支持本地和远程两种执行模式

## 开发步骤

### 步骤1: 定义关键字基本结构

```python
from pytest_dsl.core.keyword_manager import keyword_manager

@keyword_manager.register('新关键字名称', [
    {'name': '参数1', 'mapping': 'param1', 'description': '参数1描述'},
    {'name': '参数2', 'mapping': 'param2', 'description': '参数2描述'},
    # ... 更多参数
])
def new_keyword(**kwargs):
    """新关键字的实现
    
    Args:
        param1: 参数1说明
        param2: 参数2说明
        context: 测试上下文（自动注入）
        
    Returns:
        统一格式的返回值
    """
    # 关键字实现逻辑
    pass
```

### 步骤2: 实现关键字逻辑

```python
def new_keyword(**kwargs):
    # 获取参数
    param1 = kwargs.get('param1')
    param2 = kwargs.get('param2')
    context = kwargs.get('context')
    
    # 执行关键字的核心逻辑
    result = perform_operation(param1, param2)
    
    # 处理变量捕获（如果需要）
    captured_vars = {}
    if some_condition:
        captured_vars['captured_var'] = extracted_value
        # 在本地模式下设置到上下文
        if context:
            context.set('captured_var', extracted_value)
    
    # 处理会话状态（如果需要）
    session_state = {}
    if has_session:
        session_state = get_session_state()
    
    # 返回统一格式
    return {
        "result": result,
        "captures": captured_vars,
        "session_state": session_state,
        "metadata": {
            "operation": "new_keyword",
            "timestamp": get_current_time()
        }
    }
```

### 步骤3: 处理特殊情况

#### 变量捕获
如果关键字需要捕获变量：

```python
# 捕获变量的处理
captured_values = {}
if capture_condition:
    captured_values['var_name'] = extracted_value
    
    # 本地模式：设置到上下文
    if context:
        context.set('var_name', extracted_value)

# 在返回值中包含捕获的变量
return {
    "result": main_result,
    "captures": captured_values,
    # ...
}
```

#### 会话管理
如果关键字涉及会话状态：

```python
# 会话状态的处理
session_state = {}
if session_name:
    session_client = get_session_client(session_name)
    session_state = {
        session_name: {
            "cookies": dict(session_client.cookies),
            "headers": dict(session_client.headers)
        }
    }

return {
    "result": main_result,
    "session_state": session_state,
    # ...
}
```

## 返回格式规范

### 标准返回格式

所有支持远程模式的关键字都应该返回以下格式：

```python
{
    "result": "主要返回值",           # 必需：关键字的主要返回值
    "captures": {                   # 可选：捕获的变量
        "变量名1": "值1",
        "变量名2": "值2"
    },
    "session_state": {              # 可选：会话状态
        "会话名": {
            "cookies": {...},
            "headers": {...}
        }
    },
    "metadata": {                   # 可选：元数据信息
        "operation": "关键字名称",
        "timestamp": "时间戳",
        "additional_info": "其他信息"
    }
}
```

### 字段说明

- **result**: 关键字的主要返回值，保持向后兼容性
- **captures**: 需要传递给客户端的捕获变量
- **session_state**: 会话相关的状态信息
- **metadata**: 额外的元数据信息，用于调试和监控

### 简单关键字的返回

对于不需要特殊处理的简单关键字，可以直接返回主要值：

```python
def simple_keyword(**kwargs):
    result = simple_operation()
    return result  # 系统会自动包装成标准格式
```

## 最佳实践

### 1. 错误处理

```python
def robust_keyword(**kwargs):
    try:
        # 关键字逻辑
        result = perform_operation()
        return {
            "result": result,
            "captures": {},
            "session_state": {},
            "metadata": {"status": "success"}
        }
    except Exception as e:
        # 记录错误信息
        logger.error(f"关键字执行失败: {str(e)}")
        raise  # 重新抛出异常，让框架处理
```

### 2. 参数验证

```python
def validated_keyword(**kwargs):
    # 验证必需参数
    required_param = kwargs.get('required_param')
    if not required_param:
        raise ValueError("缺少必需参数: required_param")
    
    # 验证参数类型
    if not isinstance(required_param, str):
        raise TypeError("参数类型错误: required_param 必须是字符串")
    
    # 继续执行关键字逻辑
    # ...
```

### 3. 日志记录

```python
import logging

logger = logging.getLogger(__name__)

def logged_keyword(**kwargs):
    logger.info(f"开始执行关键字: {kwargs}")
    
    try:
        result = perform_operation()
        logger.info(f"关键字执行成功: {result}")
        return result
    except Exception as e:
        logger.error(f"关键字执行失败: {str(e)}")
        raise
```

### 4. 性能考虑

```python
def optimized_keyword(**kwargs):
    # 避免不必要的序列化
    large_data = get_large_data()
    
    # 只返回必要的数据
    summary = summarize_data(large_data)
    
    return {
        "result": summary,  # 返回摘要而不是完整数据
        "metadata": {
            "data_size": len(large_data),
            "summary_size": len(summary)
        }
    }
```

## 测试验证

### 1. 创建测试文件

```dsl
@name: "新关键字测试"
@remote: "http://localhost:8270/" as remote_server

# 本地测试
local_result = [新关键字名称],参数1: "值1",参数2: "值2"
[打印],内容: "本地结果: ${local_result}"

# 远程测试
remote_result = remote_server|[新关键字名称],参数1: "值1",参数2: "值2"
[打印],内容: "远程结果: ${remote_result}"

# 验证结果一致性
[断言],条件: "${local_result} == ${remote_result}",消息: "本地和远程结果应该一致"
```

### 2. 运行测试

```bash
# 启动远程服务器
python -m pytest_dsl.remote.keyword_server --host localhost --port 8270

# 运行测试
pytest-dsl test_new_keyword.dsl
```

## 常见问题

### Q1: 关键字在远程模式下无法正确返回捕获的变量？

**A**: 确保关键字返回了标准格式，并在`captures`字段中包含了所有需要捕获的变量。

```python
# 错误的做法
def bad_keyword(**kwargs):
    context = kwargs.get('context')
    context.set('var', 'value')  # 只设置到远程上下文
    return 'result'

# 正确的做法
def good_keyword(**kwargs):
    context = kwargs.get('context')
    if context:
        context.set('var', 'value')  # 本地模式
    
    return {
        "result": 'result',
        "captures": {'var': 'value'}  # 远程模式
    }
```

### Q2: 会话状态在远程模式下丢失？

**A**: 确保在返回值的`session_state`字段中包含了会话信息。

```python
def session_keyword(**kwargs):
    session_name = kwargs.get('session')
    
    # 执行操作...
    
    # 获取会话状态
    session_state = {}
    if session_name:
        session_client = get_session_client(session_name)
        session_state = {
            session_name: {
                "cookies": dict(session_client.cookies),
                "headers": dict(session_client.headers)
            }
        }
    
    return {
        "result": result,
        "session_state": session_state
    }
```

### Q3: 关键字返回的数据无法序列化？

**A**: 确保返回的数据都是可JSON序列化的。

```python
def serializable_keyword(**kwargs):
    # 避免返回复杂对象
    complex_object = get_complex_object()
    
    # 转换为可序列化的格式
    serializable_data = {
        "id": complex_object.id,
        "name": complex_object.name,
        "status": str(complex_object.status)
    }
    
    return {
        "result": serializable_data,
        "metadata": {
            "object_type": type(complex_object).__name__
        }
    }
```

### Q4: 如何处理大量数据的传输？

**A**: 避免传输大量数据，考虑使用摘要或引用。

```python
def efficient_keyword(**kwargs):
    large_dataset = process_large_data()
    
    # 不要直接返回大数据集
    # return {"result": large_dataset}  # 错误
    
    # 返回摘要信息
    summary = {
        "count": len(large_dataset),
        "first_item": large_dataset[0] if large_dataset else None,
        "last_item": large_dataset[-1] if large_dataset else None
    }
    
    return {
        "result": summary,
        "metadata": {
            "total_size": len(large_dataset)
        }
    }
```

---

## 相关文档

- [远程关键字使用指南](remote-keywords-usage.md)
- [关键字开发指南](keyword-development.md)
- [API参考文档](api-reference.md)
