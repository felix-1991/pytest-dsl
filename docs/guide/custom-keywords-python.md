# Python代码自定义关键字

Python代码自定义关键字是使用纯Python代码定义的高级自定义功能，它提供了最大的灵活性和功能性，适合有编程基础的用户创建复杂的测试逻辑。

## 什么是Python代码自定义关键字

Python代码自定义关键字是通过`@keyword_manager.register`装饰器在Python文件中定义的关键字，具有以下特点：

- 🚀 **功能强大** - 可以使用完整的Python生态系统
- 🔧 **高度灵活** - 支持复杂的业务逻辑和数据处理
- 🌐 **远程支持** - 支持分布式执行和远程调用
- 📦 **易于分发** - 可以打包成Python模块分享
- 🛡️ **类型安全** - 支持参数验证和类型检查

## 基本语法

### 注册关键字

```python
from pytest_dsl.core.keyword_manager import keyword_manager

@keyword_manager.register('关键字名称', [
    {'name': '参数显示名', 'mapping': 'param_name', 'description': '参数描述'},
    {'name': '可选参数', 'mapping': 'optional_param', 'description': '可选参数', 'default': '默认值'}
])
def keyword_function(**kwargs):
    """关键字功能描述"""
    # 获取参数
    param_value = kwargs.get('param_name')
    optional_value = kwargs.get('optional_param', '默认值')
    
    # 实现逻辑
    result = f"处理结果: {param_value}"
    
    return result
```

### 参数配置详解

参数配置是一个字典列表，每个字典包含以下字段：

- `name`: 在DSL中显示的参数名称（中文）
- `mapping`: Python函数中的参数名（英文）
- `description`: 参数描述
- `default`: 默认值（可选）

## 快速入门示例

### 项目关键字组织

对于本地项目，推荐使用如下目录结构：

```
my-project/
├── tests/                   # 测试用例目录
│   ├── test_web.dsl
│   ├── test_api.dsl
│   └── config/
├── keywords/                # 关键字目录
│   ├── __init__.py          # 可选，如果要作为包使用
│   ├── text_utils.py        # 文本处理关键字
│   ├── web_utils.py         # Web测试关键字
│   └── api_utils.py         # API测试关键字
├── config/                  # 配置文件
│   ├── test_config.yaml
│   └── environments.yaml
└── requirements.txt
```

### 简单的文本处理关键字

```python
# keywords/text_utils.py
from pytest_dsl.core.keyword_manager import keyword_manager

@keyword_manager.register('文本处理', [
    {'name': '文本内容', 'mapping': 'text', 'description': '要处理的文本'},
    {'name': '操作类型', 'mapping': 'operation', 'description': '处理类型：upper/lower/title'},
    {'name': '去除空格', 'mapping': 'strip_spaces', 'description': '是否去除首尾空格', 'default': True}
])
def text_processor(**kwargs):
    """文本处理关键字"""
    text = kwargs.get('text', '')
    operation = kwargs.get('operation', 'upper')
    strip_spaces = kwargs.get('strip_spaces', True)
    
    # 去除空格
    if strip_spaces:
        text = text.strip()
    
    # 执行操作
    if operation == 'upper':
        result = text.upper()
    elif operation == 'lower':
        result = text.lower()
    elif operation == 'title':
        result = text.title()
    else:
        result = text
    
    return result

@keyword_manager.register('生成随机字符串', [
    {'name': '长度', 'mapping': 'length', 'description': '字符串长度', 'default': 8},
    {'name': '类型', 'mapping': 'char_type', 'description': '字符类型：letters/digits/mixed', 'default': 'mixed'}
])
def generate_random_string(**kwargs):
    """生成随机字符串"""
    import random
    import string
    
    length = kwargs.get('length', 8)
    char_type = kwargs.get('char_type', 'mixed')
    
    if char_type == 'letters':
        chars = string.ascii_letters
    elif char_type == 'digits':
        chars = string.digits
    else:  # mixed
        chars = string.ascii_letters + string.digits
    
    result = ''.join(random.choice(chars) for _ in range(length))
    return result
```

### 在DSL中使用

```python
@name: "Python自定义关键字示例"

# 使用文本处理关键字
结果1 = [文本处理], 文本内容: "  hello world  ", 操作类型: "title"
结果2 = [文本处理], 文本内容: "PYTHON DSL", 操作类型: "lower", 去除空格: False

# 使用随机字符串生成
随机字符串1 = [生成随机字符串], 长度: 12, 类型: "letters"
随机字符串2 = [生成随机字符串]  # 使用默认值

[打印], 内容: "处理结果1: ${结果1}"
[打印], 内容: "处理结果2: ${结果2}"
[打印], 内容: "随机字符串1: ${随机字符串1}"
[打印], 内容: "随机字符串2: ${随机字符串2}"
```

## 高级功能

### HTTP请求关键字

```python
# keywords/http_utils.py
import requests
from pytest_dsl.core.keyword_manager import keyword_manager

@keyword_manager.register('HTTP请求', [
    {'name': '地址', 'mapping': 'url', 'description': '请求地址'},
    {'name': '方法', 'mapping': 'method', 'description': 'HTTP方法', 'default': 'GET'},
    {'name': '请求头', 'mapping': 'headers', 'description': '请求头字典', 'default': {}},
    {'name': '请求体', 'mapping': 'data', 'description': '请求体数据', 'default': None},
    {'name': '超时', 'mapping': 'timeout', 'description': '超时时间（秒）', 'default': 30},
    {'name': '重试次数', 'mapping': 'retries', 'description': '重试次数', 'default': 3},
    {'name': '验证SSL', 'mapping': 'verify_ssl', 'description': '是否验证SSL证书', 'default': True}
])
def http_request(**kwargs):
    """HTTP请求关键字，支持重试和错误处理"""
    url = kwargs.get('url')
    method = kwargs.get('method', 'GET').upper()
    headers = kwargs.get('headers', {})
    data = kwargs.get('data')
    timeout = kwargs.get('timeout', 30)
    retries = kwargs.get('retries', 3)
    verify_ssl = kwargs.get('verify_ssl', True)
    
    # 参数验证
    if not url:
        raise ValueError("URL不能为空")
    
    # 重试逻辑
    last_exception = None
    for attempt in range(retries + 1):
        try:
            # 发送请求
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data if isinstance(data, dict) else None,
                data=data if not isinstance(data, dict) else None,
                timeout=timeout,
                verify=verify_ssl
            )
            
            # 构建返回结果
            result = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'text': response.text,
                'url': response.url,
                'elapsed': response.elapsed.total_seconds()
            }
            
            # 尝试解析JSON
            try:
                result['json'] = response.json()
            except:
                result['json'] = None
            
            return result
            
        except Exception as e:
            last_exception = e
            if attempt < retries:
                print(f"请求失败，第{attempt + 1}次重试: {str(e)}")
                import time
                time.sleep(1)  # 重试间隔
            else:
                raise Exception(f"HTTP请求失败，已重试{retries}次: {str(last_exception)}")

@keyword_manager.register('API断言', [
    {'name': '响应', 'mapping': 'response', 'description': 'HTTP响应对象'},
    {'name': '期望状态码', 'mapping': 'expected_status', 'description': '期望的状态码', 'default': 200},
    {'name': 'JSON路径', 'mapping': 'json_path', 'description': 'JSONPath表达式', 'default': None},
    {'name': '期望值', 'mapping': 'expected_value', 'description': '期望的值', 'default': None}
])
def api_assert(**kwargs):
    """API响应断言"""
    response = kwargs.get('response')
    expected_status = kwargs.get('expected_status', 200)
    json_path = kwargs.get('json_path')
    expected_value = kwargs.get('expected_value')
    
    # 状态码断言
    if response['status_code'] != expected_status:
        raise AssertionError(f"状态码不匹配: 期望{expected_status}, 实际{response['status_code']}")
    
    # JSON路径断言
    if json_path and expected_value is not None:
        from jsonpath_ng import parse
        
        if not response.get('json'):
            raise AssertionError("响应不包含JSON数据")
        
        jsonpath_expr = parse(json_path)
        matches = [match.value for match in jsonpath_expr.find(response['json'])]
        
        if not matches:
            raise AssertionError(f"JSONPath '{json_path}' 未找到匹配项")
        
        actual_value = matches[0]
        if actual_value != expected_value:
            raise AssertionError(f"JSON值不匹配: 期望{expected_value}, 实际{actual_value}")
    
    return True
```

### 数据库操作关键字

```python
# keywords/database_utils.py
import sqlite3
import json
from pytest_dsl.core.keyword_manager import keyword_manager

@keyword_manager.register('数据库查询', [
    {'name': '数据库路径', 'mapping': 'db_path', 'description': '数据库文件路径'},
    {'name': 'SQL语句', 'mapping': 'sql', 'description': 'SQL查询语句'},
    {'name': '参数', 'mapping': 'params', 'description': 'SQL参数', 'default': []},
    {'name': '返回格式', 'mapping': 'format', 'description': '返回格式：dict/list', 'default': 'dict'}
])
def database_query(**kwargs):
    """数据库查询关键字"""
    db_path = kwargs.get('db_path')
    sql = kwargs.get('sql')
    params = kwargs.get('params', [])
    format_type = kwargs.get('format', 'dict')
    
    if not db_path or not sql:
        raise ValueError("数据库路径和SQL语句不能为空")
    
    try:
        conn = sqlite3.connect(db_path)
        
        if format_type == 'dict':
            conn.row_factory = sqlite3.Row
        
        cursor = conn.cursor()
        cursor.execute(sql, params)
        
        if sql.strip().upper().startswith('SELECT'):
            results = cursor.fetchall()
            if format_type == 'dict':
                results = [dict(row) for row in results]
            return results
        else:
            conn.commit()
            return cursor.rowcount
            
    except Exception as e:
        raise Exception(f"数据库操作失败: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

@keyword_manager.register('创建测试数据', [
    {'name': '数据库路径', 'mapping': 'db_path', 'description': '数据库文件路径'},
    {'name': '表名', 'mapping': 'table_name', 'description': '表名'},
    {'name': '数据', 'mapping': 'data', 'description': '要插入的数据（字典或字典列表）'},
    {'name': '清空表', 'mapping': 'clear_table', 'description': '插入前是否清空表', 'default': False}
])
def create_test_data(**kwargs):
    """创建测试数据"""
    db_path = kwargs.get('db_path')
    table_name = kwargs.get('table_name')
    data = kwargs.get('data')
    clear_table = kwargs.get('clear_table', False)
    
    if not all([db_path, table_name, data]):
        raise ValueError("数据库路径、表名和数据不能为空")
    
    # 确保data是列表
    if isinstance(data, dict):
        data = [data]
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 清空表
        if clear_table:
            cursor.execute(f"DELETE FROM {table_name}")
        
        # 插入数据
        if data:
            columns = list(data[0].keys())
            placeholders = ', '.join(['?' for _ in columns])
            sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            
            for row in data:
                values = [row.get(col) for col in columns]
                cursor.execute(sql, values)
        
        conn.commit()
        return len(data)
        
    except Exception as e:
        raise Exception(f"创建测试数据失败: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()
```

### 文件操作关键字

```python
# keywords/file_utils.py
import os
import json
import csv
from pytest_dsl.core.keyword_manager import keyword_manager

@keyword_manager.register('文件操作', [
    {'name': '操作类型', 'mapping': 'operation', 'description': '操作类型：read/write/delete/exists'},
    {'name': '文件路径', 'mapping': 'file_path', 'description': '文件路径'},
    {'name': '内容', 'mapping': 'content', 'description': '文件内容（写入时使用）', 'default': ''},
    {'name': '编码', 'mapping': 'encoding', 'description': '文件编码', 'default': 'utf-8'}
])
def file_operation(**kwargs):
    """文件操作关键字"""
    operation = kwargs.get('operation')
    file_path = kwargs.get('file_path')
    content = kwargs.get('content', '')
    encoding = kwargs.get('encoding', 'utf-8')
    
    if not operation or not file_path:
        raise ValueError("操作类型和文件路径不能为空")
    
    try:
        if operation == 'read':
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
                
        elif operation == 'write':
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
            return True
            
        elif operation == 'delete':
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
            
        elif operation == 'exists':
            return os.path.exists(file_path)
            
        else:
            raise ValueError(f"不支持的操作类型: {operation}")
            
    except Exception as e:
        raise Exception(f"文件操作失败: {str(e)}")

@keyword_manager.register('JSON文件处理', [
    {'name': '操作类型', 'mapping': 'operation', 'description': '操作类型：load/save'},
    {'name': '文件路径', 'mapping': 'file_path', 'description': 'JSON文件路径'},
    {'name': '数据', 'mapping': 'data', 'description': 'JSON数据（保存时使用）', 'default': None},
    {'name': '格式化', 'mapping': 'indent', 'description': '格式化缩进', 'default': 2}
])
def json_file_handler(**kwargs):
    """JSON文件处理"""
    operation = kwargs.get('operation')
    file_path = kwargs.get('file_path')
    data = kwargs.get('data')
    indent = kwargs.get('indent', 2)
    
    try:
        if operation == 'load':
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        elif operation == 'save':
            if data is None:
                raise ValueError("保存JSON时数据不能为空")
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)
            return True
            
        else:
            raise ValueError(f"不支持的操作类型: {operation}")
            
    except Exception as e:
        raise Exception(f"JSON文件处理失败: {str(e)}")

@keyword_manager.register('CSV文件处理', [
    {'name': '操作类型', 'mapping': 'operation', 'description': '操作类型：read/write'},
    {'name': '文件路径', 'mapping': 'file_path', 'description': 'CSV文件路径'},
    {'name': '数据', 'mapping': 'data', 'description': 'CSV数据（写入时使用）', 'default': []},
    {'name': '表头', 'mapping': 'headers', 'description': 'CSV表头', 'default': None}
])
def csv_file_handler(**kwargs):
    """CSV文件处理"""
    operation = kwargs.get('operation')
    file_path = kwargs.get('file_path')
    data = kwargs.get('data', [])
    headers = kwargs.get('headers')
    
    try:
        if operation == 'read':
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                return list(reader)
                
        elif operation == 'write':
            if not data:
                raise ValueError("写入CSV时数据不能为空")
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 如果没有指定表头，使用第一行数据的键
            if headers is None and isinstance(data[0], dict):
                headers = list(data[0].keys())
            
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                if headers:
                    writer = csv.DictWriter(f, fieldnames=headers)
                    writer.writeheader()
                    writer.writerows(data)
                else:
                    writer = csv.writer(f)
                    writer.writerows(data)
            return True
            
        else:
            raise ValueError(f"不支持的操作类型: {operation}")
            
    except Exception as e:
        raise Exception(f"CSV文件处理失败: {str(e)}")
```

## 远程关键字支持

Python代码自定义关键字完全支持远程执行，这是其相对于DSL内关键字的重要优势：

```python
# keywords/remote_utils.py
from pytest_dsl.core.keyword_manager import keyword_manager

@keyword_manager.register('远程文件操作', [
    {'name': '服务器', 'mapping': 'server', 'description': '远程服务器名称'},
    {'name': '操作类型', 'mapping': 'operation', 'description': '操作类型：upload/download/delete'},
    {'name': '本地路径', 'mapping': 'local_path', 'description': '本地文件路径'},
    {'name': '远程路径', 'mapping': 'remote_path', 'description': '远程文件路径'}
])
def remote_file_operation(**kwargs):
    """远程文件操作关键字"""
    server = kwargs.get('server')
    operation = kwargs.get('operation')
    local_path = kwargs.get('local_path')
    remote_path = kwargs.get('remote_path')
    
    # 这个关键字可以在远程服务器上执行
    # 具体的远程文件操作逻辑
    if operation == 'upload':
        # 上传文件到远程服务器
        return f"文件已上传到 {server}:{remote_path}"
    elif operation == 'download':
        # 从远程服务器下载文件
        return f"文件已从 {server}:{remote_path} 下载到 {local_path}"
    elif operation == 'delete':
        # 删除远程服务器文件
        return f"已删除 {server}:{remote_path}"
    
    return f"在服务器 {server} 上执行 {operation} 操作"

@keyword_manager.register('远程数据库操作', [
    {'name': '数据库连接', 'mapping': 'db_config', 'description': '数据库连接配置'},
    {'name': 'SQL语句', 'mapping': 'sql', 'description': 'SQL语句'},
    {'name': '参数', 'mapping': 'params', 'description': 'SQL参数', 'default': []}
])
def remote_database_operation(**kwargs):
    """远程数据库操作关键字"""
    db_config = kwargs.get('db_config')
    sql = kwargs.get('sql')
    params = kwargs.get('params', [])
    
    # 这个关键字可以在远程服务器上执行数据库操作
    # 避免网络延迟和安全问题
    
    # 模拟数据库操作
    return {
        "executed_sql": sql,
        "params": params,
        "rows_affected": 1,
        "server": "remote_db_server"
    }
```

## 上下文和全局变量访问

Python关键字可以访问测试上下文和全局变量：

```python
# keywords/context_utils.py
from pytest_dsl.core.keyword_manager import keyword_manager

@keyword_manager.register('设置全局变量', [
    {'name': '变量名', 'mapping': 'var_name', 'description': '变量名称'},
    {'name': '变量值', 'mapping': 'var_value', 'description': '变量值'}
])
def set_global_variable(**kwargs):
    """设置全局变量"""
    var_name = kwargs.get('var_name')
    var_value = kwargs.get('var_value')
    
    # 获取当前测试上下文
    from pytest_dsl.core.context import get_current_context
    context = get_current_context()
    
    # 设置全局变量
    context.set_variable(var_name, var_value)
    
    return f"已设置全局变量 {var_name} = {var_value}"

@keyword_manager.register('获取全局变量', [
    {'name': '变量名', 'mapping': 'var_name', 'description': '变量名称'},
    {'name': '默认值', 'mapping': 'default_value', 'description': '默认值', 'default': None}
])
def get_global_variable(**kwargs):
    """获取全局变量"""
    var_name = kwargs.get('var_name')
    default_value = kwargs.get('default_value')
    
    from pytest_dsl.core.context import get_current_context
    context = get_current_context()
    
    return context.get_variable(var_name, default_value)

@keyword_manager.register('获取测试信息', [])
def get_test_info(**kwargs):
    """获取当前测试信息"""
    from pytest_dsl.core.context import get_current_context
    context = get_current_context()
    
    return {
        "test_name": context.test_name,
        "test_file": context.test_file,
        "start_time": str(context.start_time),
        "variables": dict(context.variables)
    }
```

## 错误处理和日志

```python
# keywords/error_handling.py
import logging
from pytest_dsl.core.keyword_manager import keyword_manager

# 配置日志
logger = logging.getLogger(__name__)

@keyword_manager.register('安全执行', [
    {'name': '操作函数', 'mapping': 'operation_func', 'description': '要执行的操作函数'},
    {'name': '参数', 'mapping': 'args', 'description': '函数参数', 'default': []},
    {'name': '重试次数', 'mapping': 'max_retries', 'description': '最大重试次数', 'default': 3},
    {'name': '重试间隔', 'mapping': 'retry_delay', 'description': '重试间隔（秒）', 'default': 1}
])
def safe_execute(**kwargs):
    """安全执行操作，支持重试和错误处理"""
    operation_func = kwargs.get('operation_func')
    args = kwargs.get('args', [])
    max_retries = kwargs.get('max_retries', 3)
    retry_delay = kwargs.get('retry_delay', 1)
    
    import time
    
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"执行操作，第 {attempt + 1} 次尝试")
            
            # 执行操作
            if callable(operation_func):
                result = operation_func(*args)
            else:
                result = operation_func
            
            logger.info(f"操作执行成功")
            return {
                "success": True,
                "result": result,
                "attempts": attempt + 1
            }
            
        except Exception as e:
            last_exception = e
            logger.warning(f"操作执行失败，第 {attempt + 1} 次尝试: {str(e)}")
            
            if attempt < max_retries:
                logger.info(f"等待 {retry_delay} 秒后重试")
                time.sleep(retry_delay)
            else:
                logger.error(f"所有重试都失败了，最后错误: {str(e)}")
    
    return {
        "success": False,
        "error": str(last_exception),
        "attempts": max_retries + 1
    }

@keyword_manager.register('记录日志', [
    {'name': '日志级别', 'mapping': 'level', 'description': '日志级别：DEBUG/INFO/WARNING/ERROR', 'default': 'INFO'},
    {'name': '消息', 'mapping': 'message', 'description': '日志消息'},
    {'name': '额外数据', 'mapping': 'extra_data', 'description': '额外的日志数据', 'default': None}
])
def log_message(**kwargs):
    """记录日志消息"""
    level = kwargs.get('level', 'INFO').upper()
    message = kwargs.get('message')
    extra_data = kwargs.get('extra_data')
    
    # 构建完整的日志消息
    full_message = message
    if extra_data:
        full_message += f" | 额外数据: {extra_data}"
    
    # 根据级别记录日志
    if level == 'DEBUG':
        logger.debug(full_message)
    elif level == 'INFO':
        logger.info(full_message)
    elif level == 'WARNING':
        logger.warning(full_message)
    elif level == 'ERROR':
        logger.error(full_message)
    else:
        logger.info(full_message)
    
    return f"已记录 {level} 级别日志: {message}"
```

## 关键字组织和模块化

### 创建关键字包

```python
# keywords/__init__.py
"""
自定义关键字包
"""

# 导入所有关键字模块
from . import text_utils
from . import http_utils
from . import database_utils
from . import file_utils
from . import remote_utils
from . import context_utils
from . import error_handling

__all__ = [
    'text_utils',
    'http_utils', 
    'database_utils',
    'file_utils',
    'remote_utils',
    'context_utils',
    'error_handling'
]
```

### 关键字配置文件

```python
# keywords/config.py
"""
关键字配置
"""

# 默认配置
DEFAULT_CONFIG = {
    'http': {
        'timeout': 30,
        'retries': 3,
        'verify_ssl': True
    },
    'database': {
        'default_format': 'dict',
        'connection_timeout': 10
    },
    'file': {
        'default_encoding': 'utf-8',
        'create_dirs': True
    }
}

def get_config(section, key, default=None):
    """获取配置值"""
    return DEFAULT_CONFIG.get(section, {}).get(key, default)
```

## 在DSL中使用Python关键字

```python
@name: "Python关键字综合示例"

# 文本处理
处理结果 = [文本处理], 文本内容: "  Hello World  ", 操作类型: "title", 去除空格: True

# HTTP请求
响应 = [HTTP请求], 地址: "https://api.github.com/users/octocat", 方法: "GET"
[JSON断言], JSON数据: ${响应}, JSONPath: "$.login", 预期值: "octocat"
[数据比较], 实际值: ${响应["status_code"]}, 预期值: 200

# 文件操作
[文件操作], 操作类型: "write", 文件路径: "test_output.txt", 内容: "测试内容"
文件内容 = [文件操作], 操作类型: "read", 文件路径: "test_output.txt"

# JSON处理
测试数据 = {"name": "测试", "value": 123}
[JSON文件处理], 操作类型: "save", 文件路径: "test_data.json", 数据: ${测试数据}
加载数据 = [JSON文件处理], 操作类型: "load", 文件路径: "test_data.json"

# 全局变量操作
[设置全局变量], 变量名: "test_counter", 变量值: 100
计数器值 = [获取全局变量], 变量名: "test_counter"

# 测试信息
测试信息 = [获取测试信息]

# 日志记录
[记录日志], 日志级别: "INFO", 消息: "测试执行完成", 额外数据: ${测试信息}

# 清理
[文件操作], 操作类型: "delete", 文件路径: "test_output.txt"
[文件操作], 操作类型: "delete", 文件路径: "test_data.json"

[打印], 内容: "所有Python关键字测试完成"
```

## 最佳实践

### 1. 参数验证

```python
@keyword_manager.register('示例关键字', [
    {'name': '必需参数', 'mapping': 'required_param', 'description': '必需参数'},
    {'name': '可选参数', 'mapping': 'optional_param', 'description': '可选参数', 'default': 'default_value'}
])
def example_keyword(**kwargs):
    """示例关键字，展示参数验证最佳实践"""
    # 获取参数
    required_param = kwargs.get('required_param')
    optional_param = kwargs.get('optional_param', 'default_value')
    
    # 参数验证
    if not required_param:
        raise ValueError("必需参数不能为空")
    
    if not isinstance(required_param, str):
        raise TypeError("必需参数必须是字符串类型")
    
    # 业务逻辑
    result = f"处理结果: {required_param} - {optional_param}"
    return result
```

### 2. 错误处理

```python
@keyword_manager.register('健壮关键字', [
    {'name': '输入数据', 'mapping': 'input_data', 'description': '输入数据'}
])
def robust_keyword(**kwargs):
    """健壮的关键字，包含完整的错误处理"""
    try:
        input_data = kwargs.get('input_data')
        
        # 参数验证
        if input_data is None:
            raise ValueError("输入数据不能为空")
        
        # 业务逻辑
        result = process_data(input_data)
        
        return {
            "success": True,
            "data": result
        }
        
    except ValueError as e:
        logger.error(f"参数错误: {str(e)}")
        return {
            "success": False,
            "error": f"参数错误: {str(e)}"
        }
    except Exception as e:
        logger.error(f"未知错误: {str(e)}")
        return {
            "success": False,
            "error": f"执行失败: {str(e)}"
        }

def process_data(data):
    """辅助函数"""
    return f"处理后的数据: {data}"
```

### 3. 文档和类型提示

```python
from typing import Dict, List, Optional, Union
from pytest_dsl.core.keyword_manager import keyword_manager

@keyword_manager.register('类型安全关键字', [
    {'name': '字符串参数', 'mapping': 'str_param', 'description': '字符串类型参数'},
    {'name': '数字参数', 'mapping': 'num_param', 'description': '数字类型参数', 'default': 0},
    {'name': '列表参数', 'mapping': 'list_param', 'description': '列表类型参数', 'default': []}
])
def type_safe_keyword(**kwargs) -> Dict[str, Union[str, int, List]]:
    """
    类型安全的关键字示例
    
    Args:
        **kwargs: 关键字参数
            - str_param (str): 字符串参数
            - num_param (int): 数字参数，默认为0
            - list_param (List): 列表参数，默认为空列表
    
    Returns:
        Dict[str, Union[str, int, List]]: 包含处理结果的字典
        
    Raises:
        ValueError: 当参数类型不正确时
        TypeError: 当参数类型不匹配时
    """
    # 获取并验证参数
    str_param: str = kwargs.get('str_param')
    num_param: int = kwargs.get('num_param', 0)
    list_param: List = kwargs.get('list_param', [])
    
    # 类型检查
    if not isinstance(str_param, str):
        raise TypeError("str_param 必须是字符串类型")
    
    if not isinstance(num_param, (int, float)):
        raise TypeError("num_param 必须是数字类型")
    
    if not isinstance(list_param, list):
        raise TypeError("list_param 必须是列表类型")
    
    # 业务逻辑
    result = {
        "processed_string": str_param.upper(),
        "calculated_number": num_param * 2,
        "list_length": len(list_param)
    }
    
    return result
```

### 4. 性能优化

```python
import functools
import time
from pytest_dsl.core.keyword_manager import keyword_manager

# 缓存装饰器
def cache_result(ttl_seconds=300):
    """结果缓存装饰器"""
    def decorator(func):
        cache = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = str(args) + str(sorted(kwargs.items()))
            current_time = time.time()
            
            # 检查缓存
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if current_time - timestamp < ttl_seconds:
                    return result
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache[cache_key] = (result, current_time)
            
            return result
        return wrapper
    return decorator

@keyword_manager.register('缓存关键字', [
    {'name': '计算参数', 'mapping': 'calc_param', 'description': '计算参数'}
])
@cache_result(ttl_seconds=60)  # 缓存60秒
def cached_keyword(**kwargs):
    """带缓存的关键字，避免重复计算"""
    calc_param = kwargs.get('calc_param')
    
    # 模拟耗时计算
    time.sleep(1)
    result = f"计算结果: {calc_param} * 2 = {calc_param * 2}"
    
    return result
```

## 与DSL内关键字的对比

| 特性 | DSL内关键字 | Python代码关键字 |
|------|-------------|------------------|
| **学习门槛** | 低，无需编程基础 | 中等，需要Python基础 |
| **功能强大程度** | 中等，受DSL语法限制 | 高，可使用完整Python生态 |
| **远程执行** | 不支持 | 完全支持 |
| **类型安全** | 基础支持 | 完整支持 |
| **错误处理** | 基础 | 完整的异常处理 |
| **性能优化** | 有限 | 支持缓存、异步等 |
| **代码复用** | 仅在当前文件 | 可打包分发 |
| **调试能力** | 基础 | 完整的调试支持 |
| **第三方库** | 不支持 | 完全支持 |

## 插件开发和分发 🚀

pytest-dsl支持将Python自定义关键字封装成独立的Python库进行分发，这样可以让关键字在不同项目间复用，并通过PyPI等渠道分享给社区。

### 插件发现机制

pytest-dsl使用Python的`entry_points`机制来自动发现和加载已安装的关键字插件：

1. **自动扫描** - 启动时自动扫描所有声明了`pytest_dsl.keywords`入口点的包
2. **动态加载** - 自动导入插件包中的关键字模块
3. **来源标识** - 自动标记关键字的来源信息，便于管理

### 创建关键字插件

#### 1. 项目结构

```
my-pytest-dsl-plugin/
├── setup.py                 # 包配置文件（可选）
├── pyproject.toml           # 现代包配置文件（推荐）
├── README.md                # 项目说明
├── LICENSE                  # 许可证
├── requirements.txt         # 依赖列表
├── tests/                   # 测试目录
│   ├── __init__.py
│   ├── test_plugin.py       # 插件测试
│   └── test_integration.dsl # DSL集成测试
└── my_plugin/
    ├── __init__.py          # 插件入口
    └── keywords/            # 关键字目录
        ├── __init__.py      # 关键字包初始化
        ├── web_keywords.py  # Web测试关键字
        ├── api_keywords.py  # API测试关键字
        └── db_keywords.py   # 数据库测试关键字
```

#### 2. 插件入口文件

```python
# my_plugin/__init__.py
"""
我的pytest-dsl关键字插件

提供Web、API和数据库测试相关的关键字集合
"""

__version__ = "1.0.0"

def register_keywords(keyword_manager):
    """
    插件关键字注册函数
    
    这个函数会被pytest-dsl自动调用，用于注册插件中的所有关键字
    
    Args:
        keyword_manager: pytest-dsl提供的关键字管理器，已包装插件来源信息
    """
    # 方式1：使用集中注册函数
    from .keywords import web_keywords
    from .keywords import api_keywords
    from .keywords import db_keywords
    
    # 注册Web关键字
    web_keywords.register_web_keywords(keyword_manager)
    
    # 注册API关键字
    api_keywords.register_api_keywords(keyword_manager)
    
    # 注册数据库关键字
    db_keywords.register_db_keywords(keyword_manager)
    
    print("成功注册我的pytest-dsl插件关键字")

# 方式2：也可以直接导入模块，让装饰器自动工作
# 如果使用这种方式，可以不提供register_keywords函数
# from .keywords import web_keywords
# from .keywords import api_keywords  
# from .keywords import db_keywords
```

#### 3. 关键字模块示例

首先创建关键字包的初始化文件：

```python
# my_plugin/keywords/__init__.py
"""
关键字包初始化文件

该包包含了插件的所有关键字模块
"""

# 可以在这里进行包级别的初始化
# 或者导入所有关键字模块（如果使用装饰器自动注册方式）

# from . import web_keywords
# from . import api_keywords  
# from . import db_keywords
```

然后创建具体的关键字模块：

```python
# my_plugin/keywords/web_keywords.py
from pytest_dsl.core.keyword_manager import keyword_manager

def register_web_keywords(km):
    """注册Web相关关键字"""
    
    @km.register('浏览器操作', [
        {'name': '操作类型', 'mapping': 'action', 'description': '操作类型：open/close/refresh'},
        {'name': '地址', 'mapping': 'url', 'description': '网页地址', 'default': None},
        {'name': '浏览器', 'mapping': 'browser', 'description': '浏览器类型', 'default': 'chrome'}
    ])
    def browser_action(**kwargs):
        """浏览器操作关键字"""
        action = kwargs.get('action')
        url = kwargs.get('url')
        browser = kwargs.get('browser', 'chrome')
        
        if action == 'open':
            return f"使用{browser}打开页面: {url}"
        elif action == 'close':
            return "关闭浏览器"
        elif action == 'refresh':
            return "刷新页面"
        else:
            raise ValueError(f"不支持的操作: {action}")
    
    @km.register('元素操作', [
        {'name': '操作类型', 'mapping': 'action', 'description': '操作类型：click/input/get_text'},
        {'name': '选择器', 'mapping': 'selector', 'description': '元素选择器'},
        {'name': '内容', 'mapping': 'content', 'description': '输入内容', 'default': None}
    ])
    def element_action(**kwargs):
        """元素操作关键字"""
        action = kwargs.get('action')
        selector = kwargs.get('selector')
        content = kwargs.get('content')
        
        if action == 'click':
            return f"点击元素: {selector}"
        elif action == 'input':
            return f"在{selector}中输入: {content}"
        elif action == 'get_text':
            return f"获取{selector}的文本内容"
        else:
            raise ValueError(f"不支持的操作: {action}")

# 或者直接使用装饰器（需要从外部导入keyword_manager）
# from pytest_dsl.core.keyword_manager import keyword_manager
# 
# @keyword_manager.register('页面断言', [...])
# def page_assertion(**kwargs):
#     ...
```

#### 4. 包配置文件

##### 使用 pyproject.toml（推荐）

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=45", "setuptools_scm[toml]>=6.2"]
build-backend = "setuptools.build_meta"

[project]
name = "my-pytest-dsl-plugin"
version = "1.0.0"
description = "我的pytest-dsl关键字插件"
readme = "README.md"
license = {text = "MIT"}
authors = [
    {name = "你的名字", email = "your.email@example.com"},
]
classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Topic :: Software Development :: Testing",
]
requires-python = ">=3.8"
dependencies = [
    "pytest-dsl>=1.0.0",
    "selenium>=4.0.0",
    "requests>=2.25.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=6.0",
    "black",
    "flake8",
    "mypy",
]

[project.urls]
Homepage = "https://github.com/yourusername/my-pytest-dsl-plugin"
Documentation = "https://my-pytest-dsl-plugin.readthedocs.io/"
Repository = "https://github.com/yourusername/my-pytest-dsl-plugin.git"
"Bug Reports" = "https://github.com/yourusername/my-pytest-dsl-plugin/issues"

# 关键：entry_points配置
[project.entry-points."pytest_dsl.keywords"]
my_plugin = "my_plugin"
```

##### 使用 setup.py（传统方式）

```python
# setup.py
from setuptools import setup, find_packages

setup(
    name="my-pytest-dsl-plugin",
    version="1.0.0",
    description="我的pytest-dsl关键字插件",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="你的名字",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/my-pytest-dsl-plugin",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers", 
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Testing",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pytest-dsl>=1.0.0",
        "selenium>=4.0.0", 
        "requests>=2.25.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black",
            "flake8", 
            "mypy",
        ],
    },
    # 关键：entry_points配置
    entry_points={
        "pytest_dsl.keywords": [
            "my_plugin = my_plugin",
        ],
    },
)
```

### 插件测试

#### 创建测试用例

```python
# tests/test_plugin.py
import pytest
from my_plugin import register_keywords
from pytest_dsl.core.keyword_manager import keyword_manager

class MockKeywordManager:
    """模拟关键字管理器用于测试"""
    def __init__(self):
        self.registered_keywords = {}
    
    def register(self, name, parameters):
        def decorator(func):
            self.registered_keywords[name] = {
                'function': func,
                'parameters': parameters
            }
            return func
        return decorator

def test_plugin_registration():
    """测试插件关键字注册"""
    mock_km = MockKeywordManager()
    register_keywords(mock_km)
    
    # 验证关键字是否正确注册
    assert '浏览器操作' in mock_km.registered_keywords
    assert '元素操作' in mock_km.registered_keywords
    
    # 测试关键字功能
    browser_func = mock_km.registered_keywords['浏览器操作']['function']
    result = browser_func(action='open', url='https://example.com')
    assert 'chrome' in result
    assert 'https://example.com' in result

def test_browser_action_keyword():
    """测试浏览器操作关键字"""
    from my_plugin.keywords.web_keywords import browser_action
    
    # 测试打开页面
    result = browser_action(action='open', url='https://example.com', browser='firefox')
    assert result == "使用firefox打开页面: https://example.com"
    
    # 测试关闭浏览器
    result = browser_action(action='close')
    assert result == "关闭浏览器"
    
    # 测试无效操作
    with pytest.raises(ValueError):
        browser_action(action='invalid')
```

#### DSL集成测试

```python
# tests/test_integration.dsl
@name: "插件关键字集成测试"

# 测试浏览器操作
打开结果 = [浏览器操作], 操作类型: "open", 地址: "https://example.com"
[打印], 内容: "浏览器操作结果: ${打开结果}"

# 测试元素操作
点击结果 = [元素操作], 操作类型: "click", 选择器: "#submit-button"
[打印], 内容: "元素操作结果: ${点击结果}"

# 验证结果
[数据比较], 实际值: ${打开结果}, 预期值: "使用chrome打开页面: https://example.com"
[断言], 条件: "'submit-button' in '${点击结果}'"
```

### 发布插件

#### 1. 构建分发包

```bash
# 安装构建工具
pip install build twine

# 构建分发包
python -m build

# 检查包的完整性
python -m twine check dist/*
```

#### 2. 发布到PyPI

```bash
# 发布到测试PyPI（推荐先测试）
python -m twine upload --repository testpypi dist/*

# 发布到正式PyPI
python -m twine upload dist/*
```

#### 3. 安装和使用

```bash
# 其他用户安装你的插件
pip install my-pytest-dsl-plugin

# pytest-dsl会自动发现并加载插件
# 无需任何额外配置
```

### 插件最佳实践

#### 1. 命名规范

```python
# ✅ 好的插件名称
"pytest-dsl-web"       # Web测试相关
"pytest-dsl-api"       # API测试相关
"pytest-dsl-mobile"    # 移动测试相关
"pytest-dsl-database"  # 数据库测试相关

# ✅ 好的关键字名称
"启动浏览器"           # 清晰描述功能
"发送HTTP请求"         # 功能明确
"查询数据库"           # 领域特定

# ❌ 避免的命名
"plugin1"              # 名称不明确
"测试"                 # 过于宽泛
"处理数据"             # 功能不明确
```

#### 2. 版本管理

```python
# __init__.py
__version__ = "1.2.0"

# 使用语义化版本号
# MAJOR.MINOR.PATCH
# 1.2.0 - 新增功能，向后兼容
# 2.0.0 - 破坏性变更
# 1.2.1 - 修复bug
```

#### 3. 依赖管理

```toml
# pyproject.toml
dependencies = [
    "pytest-dsl>=1.0.0,<2.0.0",  # 明确版本范围
    "requests>=2.25.0",          # 第三方依赖
]

# 可选依赖
[project.optional-dependencies]
selenium = ["selenium>=4.0.0"]
database = ["sqlalchemy>=1.4.0", "psycopg2>=2.8.0"]
all = ["selenium>=4.0.0", "sqlalchemy>=1.4.0", "psycopg2>=2.8.0"]
```

#### 4. 文档和示例

```markdown
# README.md

## 安装

```bash
pip install my-pytest-dsl-plugin
```

## 快速开始

```python
@name: "Web测试示例"

[浏览器操作], 操作类型: "open", 地址: "https://example.com"
[元素操作], 操作类型: "click", 选择器: "#submit"
```

## 关键字列表

| 关键字名称 | 功能描述 | 参数 |
|-----------|----------|------|
| 浏览器操作 | 控制浏览器 | 操作类型, 地址, 浏览器 |
| 元素操作 | 操作页面元素 | 操作类型, 选择器, 内容 |
```

### 社区插件生态

通过插件机制，pytest-dsl可以构建丰富的关键字生态系统：

#### 热门插件类型

1. **Web自动化** - Selenium、Playwright等Web测试
2. **API测试** - REST API、GraphQL、gRPC等接口测试
3. **移动测试** - Android、iOS移动应用测试
4. **数据库测试** - MySQL、PostgreSQL、MongoDB等数据库操作
5. **性能测试** - 负载测试、压力测试相关关键字
6. **安全测试** - 漏洞扫描、安全检查相关关键字
7. **云服务** - AWS、Azure、GCP等云平台操作
8. **监控告警** - 监控系统集成、告警处理

#### 插件发现和管理

```bash
# 查看已安装的pytest-dsl插件
pip list | grep pytest-dsl

# 搜索可用插件
pip search pytest-dsl

# 管理插件依赖
pip install pytest-dsl-web[selenium]
pip install pytest-dsl-api[all] 
pip install pytest-dsl-database[postgresql]
```

## 下一步

- 学习 [资源文件](./resource-files.md) 了解如何组织Python关键字
- 查看 [远程关键字](./remote-keywords.md) 了解分布式测试
- 阅读 [最佳实践](./best-practices.md) 了解项目组织方法 