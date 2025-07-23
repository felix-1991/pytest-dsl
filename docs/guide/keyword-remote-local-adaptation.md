# 关键字远程与本地适配指南

本指南详细说明如何设计和优化自定义Python关键字，使其能够在远程和本地两种执行模式下都能正常工作。

## 执行模式对比

### 本地执行模式

- **执行环境**：当前Python进程
- **变量共享**：直接内存访问
- **文件系统**：本地文件系统
- **依赖库**：本地安装的库
- **性能**：无网络延迟

### 远程执行模式

- **执行环境**：远程服务器进程
- **变量共享**：通过序列化传递
- **文件系统**：远程服务器文件系统
- **依赖库**：远程服务器安装的库
- **性能**：存在网络延迟

## 核心适配原则

### 1. 参数和返回值序列化

```python
# ✅ 推荐：使用可序列化类型
def good_keyword(**kwargs):
    data = kwargs.get('data')  # str, int, float, list, dict
    config = kwargs.get('config', {})  # dict
    
    return {
        'result': 'success',
        'data': [1, 2, 3],
        'metadata': {'key': 'value'}
    }

# ❌ 避免：不可序列化类型
def bad_keyword(**kwargs):
    file_obj = kwargs.get('file')  # 文件对象
    callback = kwargs.get('callback')  # 函数对象
    
    import io
    return io.StringIO("data")  # IO对象
```

### 2. 依赖库管理

```python
# ✅ 推荐：函数内导入
@keyword_manager.register('HTTP请求', [...])
def http_request(**kwargs):
    # 在函数内部导入，确保远程服务器也能访问
    try:
        import requests
    except ImportError:
        return {'error': 'requests库未安装'}
    
    # 使用requests进行HTTP请求
    response = requests.get(kwargs.get('url'))
    return {'status_code': response.status_code}

# ❌ 避免：模块级导入
import some_local_library  # 远程服务器可能没有

@keyword_manager.register('错误示例', [...])
def bad_example(**kwargs):
    return some_local_library.process()
```

### 3. 文件路径处理

```python
@keyword_manager.register('文件操作', [
    {'name': '文件路径', 'mapping': 'file_path', 'description': '文件路径'},
    {'name': '操作', 'mapping': 'operation', 'description': '操作类型'}
])
def file_operation(**kwargs):
    from pathlib import Path
    import os
    
    file_path = kwargs.get('file_path')
    operation = kwargs.get('operation')
    
    # 处理相对路径，使其在远程环境中也能正确解析
    if not os.path.isabs(file_path):
        file_path = Path.cwd() / file_path
    else:
        file_path = Path(file_path)
    
    if operation == 'read':
        try:
            content = file_path.read_text(encoding='utf-8')
            return {'success': True, 'content': content}
        except FileNotFoundError:
            return {'success': False, 'error': f'文件不存在: {file_path}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    elif operation == 'write':
        content = kwargs.get('content', '')
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding='utf-8')
            return {'success': True, 'message': f'文件写入成功: {file_path}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    return {'success': False, 'error': f'不支持的操作: {operation}'}
```

### 4. 环境检测

```python
@keyword_manager.register('环境感知操作', [
    {'name': '操作类型', 'mapping': 'operation', 'description': '操作类型'}
])
def environment_aware_operation(**kwargs):
    import os
    import platform
    
    operation = kwargs.get('operation')
    
    # 检测执行环境
    is_remote = os.getenv('PYTEST_DSL_REMOTE_MODE', 'false').lower() == 'true'
    
    env_info = {
        'is_remote': is_remote,
        'platform': platform.system(),
        'python_version': platform.python_version(),
        'working_directory': os.getcwd()
    }
    
    if operation == 'get_env_info':
        return {
            'success': True,
            'environment': env_info
        }
    
    elif operation == 'adaptive_behavior':
        if is_remote:
            # 远程环境的特殊处理
            result = "远程环境执行逻辑"
        else:
            # 本地环境的特殊处理
            result = "本地环境执行逻辑"
        
        return {
            'success': True,
            'result': result,
            'environment': env_info
        }
    
    return {'success': False, 'error': f'不支持的操作: {operation}'}
```

## 变量和上下文处理

### 变量传递机制

在远程模式下，变量通过以下机制传递：

1. **全局变量同步**：客户端的全局变量会在连接时同步到远程服务器
2. **YAML变量同步**：配置文件中的变量会自动同步
3. **参数传递**：关键字参数通过序列化传递
4. **返回值传递**：关键字返回值通过序列化传回客户端

```python
@keyword_manager.register('变量处理示例', [
    {'name': '变量名', 'mapping': 'var_name', 'description': '变量名称'},
    {'name': '变量值', 'mapping': 'var_value', 'description': '变量值'},
    {'name': '操作', 'mapping': 'operation', 'description': '操作类型'}
])
def variable_handling_example(**kwargs):
    """演示变量处理的关键字"""
    var_name = kwargs.get('var_name')
    var_value = kwargs.get('var_value')
    operation = kwargs.get('operation')
    
    if operation == 'process':
        # 处理变量值
        processed_value = f"处理后的{var_value}"
        
        return {
            'success': True,
            'original_value': var_value,
            'processed_value': processed_value,
            'variable_name': var_name
        }
    
    elif operation == 'validate':
        # 验证变量值
        is_valid = var_value is not None and str(var_value).strip() != ''
        
        return {
            'success': True,
            'is_valid': is_valid,
            'variable_name': var_name,
            'variable_value': var_value
        }
    
    return {'success': False, 'error': f'不支持的操作: {operation}'}
```

## 性能优化策略

### 1. 批量操作

```python
@keyword_manager.register('批量数据处理', [
    {'name': '数据列表', 'mapping': 'data_list', 'description': '要处理的数据列表'},
    {'name': '处理类型', 'mapping': 'process_type', 'description': '处理类型'}
])
def batch_data_processing(**kwargs):
    """批量处理数据，减少远程调用次数"""
    data_list = kwargs.get('data_list', [])
    process_type = kwargs.get('process_type')
    
    results = []
    
    for item in data_list:
        if process_type == 'uppercase':
            result = str(item).upper()
        elif process_type == 'lowercase':
            result = str(item).lower()
        elif process_type == 'reverse':
            result = str(item)[::-1]
        else:
            result = str(item)
        
        results.append({
            'original': item,
            'processed': result
        })
    
    return {
        'success': True,
        'results': results,
        'processed_count': len(results),
        'process_type': process_type
    }
```

### 2. 缓存机制

```python
@keyword_manager.register('缓存数据获取', [
    {'name': '数据键', 'mapping': 'data_key', 'description': '数据键名'},
    {'name': '强制刷新', 'mapping': 'force_refresh', 'description': '是否强制刷新', 'default': False}
])
def cached_data_retrieval(**kwargs):
    """带缓存的数据获取，提高远程调用性能"""
    data_key = kwargs.get('data_key')
    force_refresh = kwargs.get('force_refresh', False)
    
    # 使用函数属性作为缓存存储
    if not hasattr(cached_data_retrieval, '_cache'):
        cached_data_retrieval._cache = {}
    
    cache = cached_data_retrieval._cache
    
    # 检查缓存
    if not force_refresh and data_key in cache:
        return {
            'success': True,
            'data': cache[data_key],
            'from_cache': True,
            'cache_size': len(cache)
        }
    
    # 模拟数据获取（实际应用中可能是数据库查询、API调用等）
    import time
    time.sleep(0.1)  # 模拟耗时操作
    
    data = f"数据_{data_key}_{int(time.time())}"
    cache[data_key] = data
    
    return {
        'success': True,
        'data': data,
        'from_cache': False,
        'cache_size': len(cache)
    }
```

## 错误处理和调试

### 统一错误处理

```python
@keyword_manager.register('健壮操作示例', [
    {'name': '操作参数', 'mapping': 'operation_params', 'description': '操作参数'},
    {'name': '调试模式', 'mapping': 'debug_mode', 'description': '调试模式', 'default': False}
])
def robust_operation_example(**kwargs):
    """健壮的操作示例，包含完整的错误处理"""
    import traceback
    from datetime import datetime
    
    operation_params = kwargs.get('operation_params', {})
    debug_mode = kwargs.get('debug_mode', False)
    
    debug_info = {
        'timestamp': datetime.now().isoformat(),
        'params': operation_params,
        'debug_mode': debug_mode
    }
    
    try:
        # 模拟可能出错的操作
        if not operation_params:
            raise ValueError("操作参数不能为空")
        
        if 'error' in operation_params:
            raise RuntimeError(f"模拟错误: {operation_params['error']}")
        
        # 正常处理逻辑
        result = f"处理成功: {operation_params}"
        
        debug_info['success'] = True
        debug_info['result'] = result
        
        response = {
            'success': True,
            'result': result
        }
        
        if debug_mode:
            response['debug_info'] = debug_info
        
        return response
        
    except Exception as e:
        error_info = {
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc() if debug_mode else None
        }
        
        debug_info['success'] = False
        debug_info['error'] = error_info
        
        response = {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }
        
        if debug_mode:
            response['debug_info'] = debug_info
        
        return response
```

## 测试和验证

### 本地测试

```python
# test_keyword_compatibility.py
import pytest
from keywords.my_keywords import file_operation, batch_data_processing

class TestKeywordCompatibility:
    """测试关键字的本地和远程兼容性"""

    def test_file_operation_local(self, tmp_path):
        """测试文件操作在本地环境的功能"""
        test_file = tmp_path / "test.txt"
        test_content = "测试内容"

        # 测试写入
        result = file_operation(
            file_path=str(test_file),
            operation="write",
            content=test_content
        )
        assert result['success'] is True

        # 测试读取
        result = file_operation(
            file_path=str(test_file),
            operation="read"
        )
        assert result['success'] is True
        assert result['content'] == test_content

    def test_batch_processing_serialization(self):
        """测试批量处理的序列化兼容性"""
        import json

        # 测试数据
        test_data = ["hello", "world", "test"]

        result = batch_data_processing(
            data_list=test_data,
            process_type="uppercase"
        )

        # 验证结果可以序列化
        serialized = json.dumps(result)
        deserialized = json.loads(serialized)

        assert deserialized['success'] is True
        assert len(deserialized['results']) == 3
        assert deserialized['results'][0]['processed'] == "HELLO"
```

### 远程测试

```python
# test_remote_keywords.dsl
@name: "远程关键字兼容性测试"
@remote: "http://localhost:8270/" as test_server

# 测试本地执行
本地结果 = [文件操作], 文件路径: "local_test.txt", 操作: "write", 内容: "本地测试内容"
[断言], 条件: "${本地结果['success']} == True"

# 测试远程执行
远程结果 = test_server|[文件操作], 文件路径: "remote_test.txt", 操作: "write", 内容: "远程测试内容"
[断言], 条件: "${远程结果['success']} == True"

# 测试批量处理
测试数据 = ["apple", "banana", "cherry"]
批量结果 = test_server|[批量数据处理], 数据列表: ${测试数据}, 处理类型: "uppercase"
[断言], 条件: "${批量结果['processed_count']} == 3"
```

## 部署指南

### 1. 确保依赖一致性

```bash
# requirements.txt
pytest-dsl>=0.16.0
requests>=2.25.0
pyyaml>=5.4.0
# 其他项目依赖...

# 在远程服务器上安装相同的依赖
pip install -r requirements.txt
```

### 2. 关键字模块同步

```bash
# 将关键字模块复制到远程服务器
scp -r keywords/ user@remote-server:/path/to/project/keywords/

# 或者使用Git同步
git clone https://github.com/your-repo/project.git
cd project
pip install -r requirements.txt
```

### 3. 启动远程服务器

```bash
# 基本启动
pytest-dsl-server --host 0.0.0.0 --port 8270

# 带配置文件启动
pytest-dsl-server --config server_config.yaml

# 后台运行
nohup pytest-dsl-server --host 0.0.0.0 --port 8270 > server.log 2>&1 &
```

### 4. 客户端配置

```yaml
# config/test_config.yaml
remote_servers:
  test_server:
    url: "http://remote-server:8270/"
    api_key: "your_secret_key"
    sync_config:
      sync_global_vars: true
      sync_yaml_vars: true
```

## 最佳实践清单

### ✅ 推荐做法

1. **参数设计**
   - 使用基本数据类型（str, int, float, bool）
   - 使用容器类型（list, dict）存储复杂数据
   - 提供合理的默认值

2. **依赖管理**
   - 在函数内部导入第三方库
   - 处理导入失败的情况
   - 使用标准库优先

3. **错误处理**
   - 总是返回结构化的结果
   - 包含success字段指示操作状态
   - 提供详细的错误信息

4. **性能优化**
   - 设计批量操作接口
   - 实现适当的缓存机制
   - 减少不必要的远程调用

5. **调试支持**
   - 提供调试模式参数
   - 记录详细的执行信息
   - 支持本地直接测试

### ❌ 避免做法

1. **参数设计**
   - 传递文件对象、函数对象等不可序列化类型
   - 使用复杂的自定义类实例
   - 依赖全局状态

2. **依赖管理**
   - 在模块级导入可能不存在的库
   - 假设远程环境与本地环境完全一致
   - 硬编码本地路径

3. **错误处理**
   - 让异常直接抛出而不处理
   - 返回不一致的数据结构
   - 忽略错误情况

4. **性能问题**
   - 设计需要多次调用的细粒度接口
   - 重复执行相同的耗时操作
   - 忽略网络延迟影响

## 故障排查

### 常见问题

1. **序列化错误**
   ```
   TypeError: Object of type 'xxx' is not JSON serializable
   ```
   **解决方案**：检查参数和返回值，确保使用可序列化类型

2. **导入错误**
   ```
   ModuleNotFoundError: No module named 'xxx'
   ```
   **解决方案**：在远程服务器上安装缺失的依赖库

3. **路径错误**
   ```
   FileNotFoundError: [Errno 2] No such file or directory
   ```
   **解决方案**：使用绝对路径或正确处理相对路径

4. **权限错误**
   ```
   PermissionError: [Errno 13] Permission denied
   ```
   **解决方案**：检查远程服务器的文件权限设置

### 调试技巧

1. **启用调试模式**
   ```python
   result = my_keyword(debug_mode=True, ...)
   print(result['debug_info'])
   ```

2. **检查环境差异**
   ```python
   env_result = environment_aware_operation(operation="get_env_info")
   print(env_result['environment'])
   ```

3. **测试序列化**
   ```python
   import json
   test_data = {"key": "value"}
   serialized = json.dumps(test_data)  # 测试是否可序列化
   ```

## 实际应用示例

### 完整的远程兼容关键字

```python
# keywords/production_ready.py
from pytest_dsl.core.keyword_manager import keyword_manager

@keyword_manager.register('生产级HTTP请求', [
    {'name': '请求地址', 'mapping': 'url', 'description': 'HTTP请求地址'},
    {'name': '请求方法', 'mapping': 'method', 'description': 'HTTP方法', 'default': 'GET'},
    {'name': '请求头', 'mapping': 'headers', 'description': '请求头字典', 'default': {}},
    {'name': '请求体', 'mapping': 'data', 'description': '请求体数据', 'default': None},
    {'name': '超时时间', 'mapping': 'timeout', 'description': '超时时间（秒）', 'default': 30},
    {'name': '重试次数', 'mapping': 'retry_count', 'description': '重试次数', 'default': 3},
    {'name': '调试模式', 'mapping': 'debug_mode', 'description': '调试模式', 'default': False}
], category='网络/HTTP', tags=['生产级', 'HTTP', '健壮性'])
def production_http_request(**kwargs):
    """生产级HTTP请求关键字，支持重试、错误处理和调试"""
    import time
    import json
    from datetime import datetime

    # 获取参数
    url = kwargs.get('url')
    method = kwargs.get('method', 'GET').upper()
    headers = kwargs.get('headers', {})
    data = kwargs.get('data')
    timeout = kwargs.get('timeout', 30)
    retry_count = kwargs.get('retry_count', 3)
    debug_mode = kwargs.get('debug_mode', False)

    # 调试信息
    debug_info = {
        'start_time': datetime.now().isoformat(),
        'url': url,
        'method': method,
        'headers': headers,
        'timeout': timeout,
        'retry_count': retry_count
    }

    # 导入requests库
    try:
        import requests
    except ImportError:
        return {
            'success': False,
            'error': 'requests库未安装',
            'debug_info': debug_info if debug_mode else None
        }

    # 准备请求参数
    request_kwargs = {
        'method': method,
        'url': url,
        'headers': headers,
        'timeout': timeout
    }

    # 处理请求体
    if data is not None:
        if isinstance(data, dict):
            if headers.get('Content-Type', '').startswith('application/json'):
                request_kwargs['json'] = data
            else:
                request_kwargs['data'] = data
        else:
            request_kwargs['data'] = data

    # 执行请求（带重试）
    last_error = None
    for attempt in range(retry_count + 1):
        try:
            if debug_mode:
                print(f"[DEBUG] 第 {attempt + 1} 次尝试请求: {url}")

            response = requests.request(**request_kwargs)

            # 构建成功响应
            result = {
                'success': True,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'text': response.text,
                'attempt': attempt + 1,
                'response_time': response.elapsed.total_seconds()
            }

            # 尝试解析JSON
            try:
                result['json'] = response.json()
            except (ValueError, json.JSONDecodeError):
                result['json'] = None

            debug_info['success'] = True
            debug_info['end_time'] = datetime.now().isoformat()
            debug_info['attempts'] = attempt + 1

            if debug_mode:
                result['debug_info'] = debug_info

            return result

        except requests.exceptions.Timeout as e:
            last_error = f'请求超时: {str(e)}'
        except requests.exceptions.ConnectionError as e:
            last_error = f'连接错误: {str(e)}'
        except requests.exceptions.RequestException as e:
            last_error = f'请求异常: {str(e)}'
        except Exception as e:
            last_error = f'未知错误: {str(e)}'

        # 如果不是最后一次尝试，等待后重试
        if attempt < retry_count:
            wait_time = 2 ** attempt  # 指数退避
            if debug_mode:
                print(f"[DEBUG] 请求失败，{wait_time}秒后重试: {last_error}")
            time.sleep(wait_time)

    # 所有重试都失败
    debug_info['success'] = False
    debug_info['end_time'] = datetime.now().isoformat()
    debug_info['attempts'] = retry_count + 1
    debug_info['last_error'] = last_error

    result = {
        'success': False,
        'error': last_error,
        'attempts': retry_count + 1
    }

    if debug_mode:
        result['debug_info'] = debug_info

    return result
```

通过遵循这些指南和最佳实践，您可以创建既能在本地环境中高效运行，又能在远程环境中稳定执行的高质量自定义关键字。

## 测试和验证

### 本地测试

```python
# test_keyword_compatibility.py
import pytest
from keywords.my_keywords import file_operation, batch_data_processing

class TestKeywordCompatibility:
    """测试关键字的本地和远程兼容性"""

    def test_file_operation_local(self, tmp_path):
        """测试文件操作在本地环境的功能"""
        test_file = tmp_path / "test.txt"
        test_content = "测试内容"

        # 测试写入
        result = file_operation(
            file_path=str(test_file),
            operation="write",
            content=test_content
        )
        assert result['success'] is True

        # 测试读取
        result = file_operation(
            file_path=str(test_file),
            operation="read"
        )
        assert result['success'] is True
        assert result['content'] == test_content

    def test_batch_processing_serialization(self):
        """测试批量处理的序列化兼容性"""
        import json

        # 测试数据
        test_data = ["hello", "world", "test"]

        result = batch_data_processing(
            data_list=test_data,
            process_type="uppercase"
        )

        # 验证结果可以序列化
        serialized = json.dumps(result)
        deserialized = json.loads(serialized)

        assert deserialized['success'] is True
        assert len(deserialized['results']) == 3
        assert deserialized['results'][0]['processed'] == "HELLO"
```

### 远程测试

```python
# test_remote_keywords.dsl
@name: "远程关键字兼容性测试"
@remote: "http://localhost:8270/" as test_server

# 测试本地执行
本地结果 = [文件操作], 文件路径: "local_test.txt", 操作: "write", 内容: "本地测试内容"
[断言], 条件: "${本地结果['success']} == True"

# 测试远程执行
远程结果 = test_server|[文件操作], 文件路径: "remote_test.txt", 操作: "write", 内容: "远程测试内容"
[断言], 条件: "${远程结果['success']} == True"

# 测试批量处理
测试数据 = ["apple", "banana", "cherry"]
批量结果 = test_server|[批量数据处理], 数据列表: ${测试数据}, 处理类型: "uppercase"
[断言], 条件: "${批量结果['processed_count']} == 3"
```

## 部署指南

### 1. 确保依赖一致性

```bash
# requirements.txt
pytest-dsl>=0.16.0
requests>=2.25.0
pyyaml>=5.4.0
# 其他项目依赖...

# 在远程服务器上安装相同的依赖
pip install -r requirements.txt
```

### 2. 关键字模块同步

```bash
# 将关键字模块复制到远程服务器
scp -r keywords/ user@remote-server:/path/to/project/keywords/

# 或者使用Git同步
git clone https://github.com/your-repo/project.git
cd project
pip install -r requirements.txt
```

### 3. 启动远程服务器

```bash
# 基本启动
pytest-dsl-server --host 0.0.0.0 --port 8270

# 带配置文件启动
pytest-dsl-server --config server_config.yaml

# 后台运行
nohup pytest-dsl-server --host 0.0.0.0 --port 8270 > server.log 2>&1 &
```

### 4. 客户端配置

```yaml
# config/test_config.yaml
remote_servers:
  test_server:
    url: "http://remote-server:8270/"
    api_key: "your_secret_key"
    sync_config:
      sync_global_vars: true
      sync_yaml_vars: true
```
