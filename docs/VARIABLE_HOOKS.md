# 变量Hook机制详解

pytest-dsl的变量Hook机制允许外部系统动态提供测试变量，实现灵活的环境配置和变量管理。

## 功能概述

变量Hook机制提供以下核心功能：

1. **动态变量获取** - 从外部数据源（数据库、API、配置服务等）获取变量
2. **多环境支持** - 通过环境变量控制不同环境的变量配置
3. **优先级管理** - 与现有变量系统无缝集成，支持优先级覆盖
4. **批量加载** - 支持一次性加载所有环境变量
5. **变量验证** - 对变量配置进行验证确保正确性
6. **源发现** - 列出所有可用的变量源

## Hook接口定义

### 1. dsl_load_variables

批量加载变量配置，通常在初始化时调用。

```python
@hookimpl
def dsl_load_variables(self) -> Dict[str, Any]:
    """批量加载变量配置
    
    Returns:
        Dict[str, Any]: 变量字典，键为变量名，值为变量值
    """
    environment = os.environ.get('PYTEST_DSL_ENVIRONMENT', 'dev')
    
    # 从数据库、配置文件或API获取变量
    variables = load_environment_variables(environment)
    
    return variables
```

### 2. dsl_get_variable

获取单个变量值，按需调用。

```python
@hookimpl
def dsl_get_variable(self, var_name: str) -> Optional[Any]:
    """获取单个变量值
    
    Args:
        var_name: 变量名
        
    Returns:
        Optional[Any]: 变量值，如果不存在返回None
    """
    environment = os.environ.get('PYTEST_DSL_ENVIRONMENT', 'dev')
    
    # 从配置源获取变量
    return get_variable_from_source(var_name, environment)
```

### 3. dsl_list_variable_sources

列出可用的变量源，用于调试和监控。

```python
@hookimpl
def dsl_list_variable_sources(self) -> List[Dict[str, Any]]:
    """列出可用的变量源
    
    Returns:
        List[Dict[str, Any]]: 变量源列表
    """
    return [
        {
            'name': 'database_config',
            'type': 'database',
            'description': '数据库配置变量',
            'environments': ['dev', 'test', 'prod']
        },
        {
            'name': 'api_config',
            'type': 'api',
            'description': 'API配置服务'
        }
    ]
```

### 4. dsl_validate_variables

验证变量配置的有效性。

```python
@hookimpl
def dsl_validate_variables(self, variables: Dict[str, Any]) -> List[str]:
    """验证变量配置
    
    Args:
        variables: 变量字典
        
    Returns:
        List[str]: 验证错误列表，空列表表示验证通过
    """
    errors = []
    
    # 检查必需变量
    required = ['api_url', 'timeout']
    for var in required:
        if var not in variables:
            errors.append(f"缺少必需变量: {var}")
    
    # 检查变量格式
    if 'api_url' in variables:
        if not variables['api_url'].startswith('http'):
            errors.append("api_url必须以http开头")
    
    return errors
```

## 环境变量控制

通过`PYTEST_DSL_ENVIRONMENT`环境变量控制当前环境：

```bash
# 设置环境
export PYTEST_DSL_ENVIRONMENT=dev      # 开发环境
export PYTEST_DSL_ENVIRONMENT=test     # 测试环境  
export PYTEST_DSL_ENVIRONMENT=prod     # 生产环境
```

也可以在代码中动态设置：

```python
import os
os.environ['PYTEST_DSL_ENVIRONMENT'] = 'test'
```

## 完整实现示例

### 数据库变量插件

```python
import os
import sqlite3
from typing import Dict, List, Optional, Any
from pytest_dsl.core.hookspecs import hookimpl

class DatabaseVariablePlugin:
    """从数据库获取变量的插件"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def _get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    @hookimpl
    def dsl_load_variables(self) -> Dict[str, Any]:
        """批量加载变量配置"""
        environment = os.environ.get('PYTEST_DSL_ENVIRONMENT', 'dev')
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT var_name, var_value FROM variables WHERE environment = ?",
                (environment,)
            )
            
            variables = {}
            for row in cursor.fetchall():
                var_name, var_value = row
                # 尝试解析JSON值
                try:
                    import json
                    variables[var_name] = json.loads(var_value)
                except (json.JSONDecodeError, TypeError):
                    variables[var_name] = var_value
            
            print(f"从数据库加载了 {len(variables)} 个变量 (环境: {environment})")
            return variables
            
        finally:
            conn.close()
    
    @hookimpl
    def dsl_get_variable(self, var_name: str) -> Optional[Any]:
        """获取单个变量值"""
        environment = os.environ.get('PYTEST_DSL_ENVIRONMENT', 'dev')
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT var_value FROM variables WHERE var_name = ? AND environment = ?",
                (var_name, environment)
            )
            
            row = cursor.fetchone()
            if row:
                var_value = row[0]
                # 尝试解析JSON值
                try:
                    import json
                    return json.loads(var_value)
                except (json.JSONDecodeError, TypeError):
                    return var_value
            
            return None
            
        finally:
            conn.close()
    
    @hookimpl
    def dsl_list_variable_sources(self) -> List[Dict[str, Any]]:
        """列出可用的变量源"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT DISTINCT environment FROM variables")
            environments = [row[0] for row in cursor.fetchall()]
            
            return [{
                'name': 'database_variables',
                'type': 'database',
                'description': f'SQLite数据库变量 ({self.db_path})',
                'environments': environments,
                'source_path': self.db_path
            }]
            
        finally:
            conn.close()
    
    @hookimpl
    def dsl_validate_variables(self, variables: Dict[str, Any]) -> List[str]:
        """验证变量配置"""
        errors = []
        
        # 检查数据库连接
        try:
            conn = self._get_connection()
            conn.close()
        except Exception as e:
            errors.append(f"数据库连接失败: {e}")
        
        # 检查必需变量
        required_vars = ['api_url', 'timeout']
        for var in required_vars:
            if var not in variables:
                errors.append(f"缺少必需变量: {var}")
        
        return errors
```

### API配置服务插件

```python
import requests
import os
from typing import Dict, List, Optional, Any
from pytest_dsl.core.hookspecs import hookimpl

class APIConfigPlugin:
    """从API配置服务获取变量的插件"""
    
    def __init__(self, api_base_url: str, api_key: str = None):
        self.api_base_url = api_base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})
    
    @hookimpl
    def dsl_load_variables(self) -> Dict[str, Any]:
        """从API批量加载变量配置"""
        environment = os.environ.get('PYTEST_DSL_ENVIRONMENT', 'dev')
        
        try:
            response = self.session.get(
                f"{self.api_base_url}/variables",
                params={'environment': environment},
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            variables = data.get('variables', {})
            
            print(f"从API加载了 {len(variables)} 个变量 (环境: {environment})")
            return variables
            
        except Exception as e:
            print(f"从API加载变量失败: {e}")
            return {}
    
    @hookimpl
    def dsl_get_variable(self, var_name: str) -> Optional[Any]:
        """从API获取单个变量值"""
        environment = os.environ.get('PYTEST_DSL_ENVIRONMENT', 'dev')
        
        try:
            response = self.session.get(
                f"{self.api_base_url}/variables/{var_name}",
                params={'environment': environment},
                timeout=5
            )
            
            if response.status_code == 404:
                return None
                
            response.raise_for_status()
            data = response.json()
            return data.get('value')
            
        except Exception as e:
            print(f"从API获取变量 {var_name} 失败: {e}")
            return None
    
    @hookimpl
    def dsl_list_variable_sources(self) -> List[Dict[str, Any]]:
        """列出可用的变量源"""
        try:
            response = self.session.get(
                f"{self.api_base_url}/sources",
                timeout=5
            )
            response.raise_for_status()
            
            return response.json().get('sources', [])
            
        except Exception as e:
            print(f"获取变量源列表失败: {e}")
            return [{
                'name': 'api_config',
                'type': 'api',
                'description': 'API配置服务',
                'url': self.api_base_url,
                'status': 'error',
                'error': str(e)
            }]
```

## 插件注册和使用

### 注册插件

```python
from pytest_dsl.core.hook_manager import hook_manager

# 注册数据库插件
db_plugin = DatabaseVariablePlugin('/path/to/config.db')
hook_manager.register_plugin(db_plugin, "database_variables")

# 注册API插件
api_plugin = APIConfigPlugin('https://config.example.com', 'your-api-key')
hook_manager.register_plugin(api_plugin, "api_config")

# 初始化hook管理器
hook_manager.initialize()
```

### 启用变量Hook

```python
from pytest_dsl.core.yaml_vars import yaml_vars

# 启用hook支持
yaml_vars.set_enable_hooks(True)

# 设置环境
import os
os.environ['PYTEST_DSL_ENVIRONMENT'] = 'test'

# 获取变量（会自动调用hook）
api_url = yaml_vars.get_variable('api_url')
timeout = yaml_vars.get_variable('timeout')
```

### 在DSL中使用

```python
@name: "使用Hook变量的测试"

# Hook变量可以直接使用，无需预先赋值
# DSL执行器会自动通过Hook获取这些变量

[打印], 内容: "API地址: ${api_url}"
[打印], 内容: "超时时间: ${timeout}"
[打印], 内容: "调试模式: ${debug}"

# 在HTTP请求中使用Hook变量
[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: ${api_url}/health
    timeout: ${timeout}
'''

# 也可以先赋值再使用（会覆盖Hook提供的值）
local_timeout = 30
[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: ${api_url}/data
    timeout: ${local_timeout}
    json: {"debug": ${debug}}
'''
```

## 变量优先级

变量获取的优先级顺序（从高到低）：

1. **本地DSL变量** - 直接在DSL中赋值的变量
2. **测试上下文变量** - 通过context传递的变量
3. **YAML文件变量** - 从YAML配置文件加载的变量
4. **Hook提供的变量** - 通过Hook机制获取的变量
5. **全局上下文变量** - 全局共享的变量

## 性能优化

### 缓存策略

```python
import time
import os
from typing import Optional, Any
from pytest_dsl.core.hookspecs import hookimpl

class CachedVariablePlugin:
    """带缓存的变量插件"""
    
    def __init__(self):
        self._cache = {}
        self._cache_timeout = 300  # 5分钟缓存
        self._last_load = {}
    
    @hookimpl
    def dsl_get_variable(self, var_name: str) -> Optional[Any]:
        """带缓存的变量获取"""
        environment = os.environ.get('PYTEST_DSL_ENVIRONMENT', 'dev')
        cache_key = f"{environment}:{var_name}"
        
        # 检查缓存
        if cache_key in self._cache:
            cache_time = self._last_load.get(cache_key, 0)
            if time.time() - cache_time < self._cache_timeout:
                return self._cache[cache_key]
        
        # 从源获取
        value = self._fetch_variable(var_name, environment)
        
        # 更新缓存
        if value is not None:
            self._cache[cache_key] = value
            self._last_load[cache_key] = time.time()
        
        return value
    
    def _fetch_variable(self, var_name: str, environment: str) -> Optional[Any]:
        """从实际数据源获取变量（需要子类实现）"""
        # 这里应该实现实际的变量获取逻辑
        # 例如从数据库、API或配置文件获取
        return None
```

### 异步支持

```python
import asyncio
import aiohttp
import os
from typing import Optional, Any
from pytest_dsl.core.hookspecs import hookimpl

class AsyncVariablePlugin:
    """异步变量插件"""
    
    def __init__(self, api_url: str):
        self.api_url = api_url
    
    @hookimpl
    def dsl_get_variable(self, var_name: str) -> Optional[Any]:
        """异步获取变量"""
        return asyncio.run(self._async_get_variable(var_name))
    
    async def _async_get_variable(self, var_name: str) -> Optional[Any]:
        """异步获取变量实现"""
        environment = os.environ.get('PYTEST_DSL_ENVIRONMENT', 'dev')
        
        try:
            # 使用aiohttp等异步库
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/variables/{var_name}",
                                       params={'env': environment}) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('value')
        except Exception as e:
            print(f"异步获取变量失败: {e}")
        
        return None
```

## 监控和调试

### 调试工具

```python
def debug_variable_hooks():
    """调试变量Hook功能"""
    from pytest_dsl.core.hook_manager import hook_manager
    from pytest_dsl.core.yaml_vars import yaml_vars
    
    print("=== 变量Hook调试信息 ===")
    
    # 检查插件状态
    plugins = hook_manager.get_plugins()
    print(f"已注册插件: {len(plugins)}")
    for name, plugin in plugins.items():
        print(f"  - {name}: {type(plugin).__name__}")
    
    # 检查变量源
    try:
        sources_results = hook_manager.pm.hook.dsl_list_variable_sources()
        print(f"\n变量源:")
        for sources in sources_results:
            if sources:
                for source in sources:
                    print(f"  - {source['name']} ({source['type']}): {source['description']}")
    except Exception as e:
        print(f"获取变量源失败: {e}")
    
    # 测试变量获取
    test_vars = ['api_url', 'timeout', 'debug']
    print(f"\n测试变量获取:")
    for var_name in test_vars:
        try:
            value = yaml_vars.get_variable(var_name)
            print(f"  - {var_name}: {value}")
        except Exception as e:
            print(f"  - {var_name}: 获取失败 - {e}")

# 使用示例
if __name__ == "__main__":
    debug_variable_hooks()
```

### 性能监控

```python
import time
from functools import wraps
from pytest_dsl.core.hookspecs import hookimpl

class MonitoredVariablePlugin:
    """带性能监控的变量插件"""
    
    def __init__(self):
        self.stats = {
            'calls': 0,
            'total_time': 0,
            'errors': 0
        }
    
    def _monitor_performance(self, func):
        """性能监控装饰器"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            self.stats['calls'] += 1
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                self.stats['errors'] += 1
                raise
            finally:
                elapsed = time.time() - start_time
                self.stats['total_time'] += elapsed
                
                # 记录慢查询
                if elapsed > 1.0:  # 超过1秒
                    print(f"慢查询警告: {func.__name__} 耗时 {elapsed:.2f}s")
        
        return wrapper
    
    @hookimpl
    def dsl_get_variable(self, var_name: str) -> Optional[Any]:
        """带监控的变量获取"""
        return self._monitor_performance(self._get_variable_impl)(var_name)
    
    def _get_variable_impl(self, var_name: str) -> Optional[Any]:
        """实际的变量获取逻辑"""
        # ... 实现逻辑
        pass
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取性能统计"""
        avg_time = (self.stats['total_time'] / self.stats['calls'] 
                   if self.stats['calls'] > 0 else 0)
        
        return {
            'total_calls': self.stats['calls'],
            'total_time': self.stats['total_time'],
            'average_time': avg_time,
            'error_count': self.stats['errors'],
            'error_rate': (self.stats['errors'] / self.stats['calls'] 
                          if self.stats['calls'] > 0 else 0)
        }
```

## 最佳实践

1. **错误处理**: Hook实现应该优雅处理异常，避免影响主流程
2. **性能考虑**: 避免在Hook中执行耗时操作，考虑使用缓存
3. **环境隔离**: 确保不同环境的变量严格隔离
4. **安全性**: 敏感变量应该加密存储和传输
5. **监控**: 监控Hook的调用频率和性能
6. **文档**: 为每个Hook实现提供清晰的文档
7. **测试**: 为Hook插件编写充分的单元测试

通过变量Hook机制，pytest-dsl可以灵活地从各种外部数据源获取配置，实现真正的配置与代码分离。 