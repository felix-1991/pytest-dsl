# 变量同步过滤Hook机制

## 概述

pytest-dsl提供了Hook机制，允许外部程序自定义远程关键字变量同步的过滤规则。通过实现`dsl_filter_sync_variables` Hook，可以在变量同步到远程服务器前进行自定义过滤。

## Hook规范

```python
@hookspec
def dsl_filter_sync_variables(self, variables: Dict[str, Any], 
                             sync_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """过滤要同步的变量（在最终同步前调用）
    
    Args:
        variables: 经过基础过滤后的变量字典
        sync_context: 同步上下文信息
        
    Returns:
        过滤后的变量字典，返回None表示不修改
    """
```

## 同步上下文

`sync_context` 包含以下信息：

```python
sync_context = {
    'server_alias': 'server1',           # 服务器别名
    'server_url': 'http://localhost:8270', # 服务器URL
    'sync_type': 'initial|realtime|change', # 同步类型
    'variable_source': 'context|global|yaml', # 变量来源
}
```

### 同步类型说明

- `initial`: 连接时的初始同步
- `realtime`: 关键字执行前的实时同步

### 变量来源说明

- `context`: 上下文变量（运行时变量）
- `global`: 全局变量
- `yaml`: YAML配置变量

## Hook调用时机

Hook过滤在以下时机被调用，**每种变量来源只过滤一次**：

1. **连接时初始同步**:
   - 全局变量收集时: `sync_type='initial'`, `variable_source='global'`
   - YAML变量收集时: `sync_type='initial'`, `variable_source='yaml'`

2. **关键字执行前实时同步**:
   - 上下文变量同步时: `sync_type='realtime'`, `variable_source='context'`

### 优化说明

- **避免重复过滤**: 每种变量来源在各自的收集方法中过滤，不会重复调用Hook
- **避免重复同步**: 移除了变量变化通知机制，因为实时同步已经足够
- **性能优化**: 减少了不必要的Hook调用和网络同步，提高性能
- **逻辑清晰**: 不同变量来源的过滤逻辑分离，便于维护

## 基本用法

### 1. 创建插件

```python
from pytest_dsl.core.hookspecs import hookimpl

class MySyncPlugin:
    
    @hookimpl
    def dsl_filter_sync_variables(self, variables, sync_context):
        """自定义变量过滤逻辑"""
        
        # 生产环境只同步必要变量
        if sync_context['server_alias'] == 'prod_server':
            essential_vars = ['g_environment', 'g_base_url', 'api_version']
            return {k: v for k, v in variables.items() if k in essential_vars}
        
        # 实时同步时过滤大对象
        if sync_context['sync_type'] == 'realtime':
            filtered = {}
            for k, v in variables.items():
                if isinstance(v, (list, dict)) and len(str(v)) > 1000:
                    continue  # 跳过大对象
                filtered[k] = v
            return filtered
            
        return None  # 不修改
```

### 2. 注册插件

```python
from pytest_dsl.core.hook_manager import hook_manager

plugin = MySyncPlugin()
hook_manager.register_plugin(plugin, name="my_sync_filter")
```

### 3. 在DSL中使用

```python
@name: "使用自定义同步过滤的测试"
@remote_server http://localhost:8270|prod_server

# 设置变量
设置变量: g_environment = "production"
设置变量: debug_info = "some debug data"  # 会被过滤掉
设置变量: large_data = [1, 2, 3, ...]     # 实时同步时会被过滤掉

# 远程关键字执行时会应用过滤规则
prod_server|[HTTP请求], 配置: '''
    method: GET
    url: ${g_base_url}/api/test
'''
```

## 高级用法

### 多插件协作

```python
class EnvironmentPlugin:
    @hookimpl
    def dsl_filter_sync_variables(self, variables, sync_context):
        if 'prod' in sync_context['server_alias']:
            return {k: v for k, v in variables.items() if not k.startswith('debug_')}
        return None

class SecurityPlugin:
    @hookimpl
    def dsl_filter_sync_variables(self, variables, sync_context):
        if 'external' in sync_context['server_alias']:
            whitelist = ['g_environment', 'api_version']
            return {k: v for k, v in variables.items() if k in whitelist}
        return None

# 注册多个插件
hook_manager.register_plugin(EnvironmentPlugin(), "env_filter")
hook_manager.register_plugin(SecurityPlugin(), "security_filter")
```

### 基于配置的插件

```python
class ConfigBasedPlugin:
    def __init__(self, config):
        self.config = config
    
    @hookimpl
    def dsl_filter_sync_variables(self, variables, sync_context):
        server_alias = sync_context['server_alias']
        
        if server_alias in self.config:
            rules = self.config[server_alias]
            
            # 白名单模式
            if 'whitelist' in rules:
                return {k: v for k, v in variables.items() if k in rules['whitelist']}
            
            # 黑名单模式
            if 'blacklist' in rules:
                return {k: v for k, v in variables.items() if k not in rules['blacklist']}
        
        return None

# 使用配置
config = {
    'prod_server': {
        'whitelist': ['g_environment', 'g_base_url', 'api_version']
    },
    'dev_server': {
        'blacklist': ['prod_password', 'prod_secret']
    }
}

plugin = ConfigBasedPlugin(config)
hook_manager.register_plugin(plugin, "config_filter")
```

## 调试和监控

### 添加日志

```python
class LoggingSyncPlugin:
    @hookimpl
    def dsl_filter_sync_variables(self, variables, sync_context):
        print(f"同步到 {sync_context['server_alias']}: {len(variables)} 个变量")
        print(f"同步类型: {sync_context['sync_type']}")
        print(f"变量来源: {sync_context['variable_source']}")
        
        # 进行过滤
        filtered = my_filter_logic(variables, sync_context)
        
        if filtered != variables:
            print(f"过滤后: {len(filtered)} 个变量")
            
        return filtered
```

### 性能监控

```python
import time

class PerformanceMonitorPlugin:
    @hookimpl
    def dsl_filter_sync_variables(self, variables, sync_context):
        start_time = time.time()
        
        # 执行过滤逻辑
        result = my_filter_logic(variables, sync_context)
        
        elapsed = time.time() - start_time
        if elapsed > 0.1:  # 超过100ms
            print(f"警告: 同步过滤耗时 {elapsed:.3f}s")
            
        return result
```

## 最佳实践

1. **保持简单**: Hook函数应该快速执行，避免复杂的计算
2. **异常处理**: Hook内部异常会被捕获，但最好自己处理
3. **返回None**: 如果不需要修改变量，返回None而不是原变量
4. **测试充分**: 为插件编写单元测试
5. **文档清晰**: 为插件编写清晰的文档说明

## 示例插件

完整的示例插件请参考：`examples/plugins/sync_filter_examples.py`

## 测试

运行测试验证功能：

```bash
python -m pytest tests/test_sync_filter_plugin.py -v
```
