# pytest-dsl Hook机制集成指南

pytest-dsl现在支持基于[pluggy](https://pluggy.readthedocs.io/)的hook机制，允许外部框架轻松集成并扩展DSL功能。

## 概述

Hook机制使得pytest-dsl具备了以下扩展能力：

1. **自定义DSL内容加载**：从数据库、API或其他数据源加载DSL内容
2. **动态关键字注册**：从外部源注册自定义关键字
3. **执行上下文扩展**：注入额外的变量和配置
4. **变量动态提供**：通过hook机制动态提供环境变量和配置
5. **执行生命周期钩子**：在DSL执行前后执行自定义逻辑
6. **内容验证和转换**：对DSL内容进行自定义验证和预处理

## 核心组件

### 1. Hook规范 (hookspecs.py)

定义了所有可用的hook接口：

#### DSL内容相关
- `dsl_load_content`: 加载DSL内容
- `dsl_list_cases`: 列出DSL用例
- `dsl_validate_content`: 验证DSL内容
- `dsl_transform_content`: 转换DSL内容

#### 关键字相关
- `dsl_register_custom_keywords`: 注册自定义关键字

#### 执行相关
- `dsl_get_execution_context`: 获取执行上下文
- `dsl_create_executor`: 创建自定义执行器
- `dsl_before_execution`: 执行前hook
- `dsl_after_execution`: 执行后hook

#### 变量相关 🆕
- `dsl_load_variables`: 批量加载变量配置
- `dsl_get_variable`: 获取单个变量值
- `dsl_list_variable_sources`: 列出可用变量源
- `dsl_validate_variables`: 验证变量配置

### 2. Hook管理器 (hook_manager.py)

管理插件的注册、发现和调用：

```python
from pytest_dsl.core.hook_manager import hook_manager

# 注册插件
hook_manager.register_plugin(my_plugin, "my_plugin_name")

# 初始化
hook_manager.initialize()

# 调用hook
results = hook_manager.pm.hook.dsl_load_content(dsl_id="case_001")
```

### 3. 变量Hook集成 🆕

变量系统现在支持通过hook动态提供变量：

```python
from pytest_dsl.core.yaml_vars import yaml_vars

# 启用hook支持
yaml_vars.set_enable_hooks(True)

# 通过环境变量控制环境
import os
os.environ['PYTEST_DSL_ENVIRONMENT'] = 'test'

# 获取变量（会自动调用hook）
api_url = yaml_vars.get_variable('api_url')
```

### 4. DSL执行器Hook集成

DSL执行器现在默认支持hook机制：

```python
from pytest_dsl.core.dsl_executor import DSLExecutor

# 创建支持hook的执行器
executor = DSLExecutor(enable_hooks=True)

# 执行DSL（支持hook扩展）
result = executor.execute_from_content(
    content="",  # 可以为空，通过hook加载
    dsl_id="case_001"
)
```

## 详细实现指南

### 1. 创建完整的Hook插件

```python
import os
from typing import Dict, List, Optional, Any
from pytest_dsl.core.hookspecs import hookimpl

class ComprehensivePlugin:
    """完整的Hook插件示例"""
    
    def __init__(self, database_connection=None):
        self.db = database_connection
        self.variables = {
            'dev': {
                'api_url': 'https://api-dev.example.com',
                'timeout': 30,
                'debug': True
            },
            'test': {
                'api_url': 'https://api-test.example.com',
                'timeout': 60,
                'debug': False
            },
            'prod': {
                'api_url': 'https://api.example.com',
                'timeout': 120,
                'debug': False
            }
        }
    
    # === DSL内容相关Hook ===
    
    @hookimpl
    def dsl_load_content(self, dsl_id: str) -> Optional[str]:
        """从数据库加载DSL内容"""
        if self.db:
            return self.db.get_dsl_content(dsl_id)
        return None
    
    @hookimpl
    def dsl_list_cases(self, project_id: Optional[int] = None, 
                       filters: Optional[Dict[str, Any]] = None
                       ) -> List[Dict[str, Any]]:
        """从数据库获取用例列表"""
        if self.db:
            return self.db.get_test_cases(project_id, filters)
        return []
    
    @hookimpl
    def dsl_validate_content(self, dsl_id: str, content: str) -> List[str]:
        """验证DSL内容"""
        errors = []
        if not content.strip():
            errors.append("DSL内容不能为空")
        if '@name' not in content:
            errors.append("DSL必须包含@name标签")
        return errors
    
    # === 关键字相关Hook ===
    
    @hookimpl
    def dsl_register_custom_keywords(self, project_id: Optional[int] = None) -> None:
        """注册数据库中的自定义关键字"""
        if self.db:
            from pytest_dsl.core.custom_keyword_manager import custom_keyword_manager
            keywords = self.db.get_custom_keywords(project_id)
            for name, dsl_content in keywords.items():
                try:
                    custom_keyword_manager.register_keyword_from_dsl_content(
                        dsl_content, f"数据库关键字:{name}"
                    )
                except Exception as e:
                    print(f"注册关键字失败 {name}: {e}")
    
    # === 变量相关Hook ===
    
    @hookimpl
    def dsl_load_variables(self) -> Dict[str, Any]:
        """批量加载变量配置"""
        environment = os.environ.get('PYTEST_DSL_ENVIRONMENT', 'dev')
        print(f"🔧 插件加载环境变量: {environment}")
        
        if environment in self.variables:
            return self.variables[environment]
        return {}
    
    @hookimpl
    def dsl_get_variable(self, var_name: str) -> Optional[Any]:
        """获取单个变量值"""
        environment = os.environ.get('PYTEST_DSL_ENVIRONMENT', 'dev')
        
        if environment in self.variables:
            value = self.variables[environment].get(var_name)
            if value is not None:
                print(f"🔍 插件提供变量: {var_name} = {value}")
                return value
        
        # 也可以从数据库获取
        if self.db:
            return self.db.get_variable(var_name, environment)
        
        return None
    
    @hookimpl
    def dsl_list_variable_sources(self) -> List[Dict[str, Any]]:
        """列出可用的变量源"""
        sources = [
            {
                'name': 'plugin_variables',
                'type': 'plugin',
                'description': '插件内置变量',
                'environments': list(self.variables.keys())
            }
        ]
        
        if self.db:
            sources.append({
                'name': 'database_variables',
                'type': 'database',
                'description': '数据库动态变量'
            })
        
        return sources
    
    @hookimpl
    def dsl_validate_variables(self, variables: Dict[str, Any]) -> List[str]:
        """验证变量配置"""
        errors = []
        
        # 检查必需变量
        required_vars = ['api_url', 'timeout']
        for var in required_vars:
            if var not in variables:
                errors.append(f"缺少必需变量: {var}")
        
        # 检查变量类型
        if 'timeout' in variables:
            try:
                timeout = int(variables['timeout'])
                if timeout <= 0:
                    errors.append("timeout必须大于0")
            except (ValueError, TypeError):
                errors.append("timeout必须是数字")
        
        return errors
    
    # === 执行相关Hook ===
    
    @hookimpl
    def dsl_get_execution_context(self, dsl_id: str, 
                                  base_context: Dict[str, Any]
                                  ) -> Dict[str, Any]:
        """扩展执行上下文"""
        extended_context = base_context.copy()
        
        # 添加插件特定的上下文
        extended_context.update({
            'plugin_name': 'comprehensive_plugin',
            'database_available': self.db is not None,
            'execution_timestamp': '2024-01-01T12:00:00Z'
        })
        
        return extended_context
    
    @hookimpl
    def dsl_before_execution(self, dsl_id: str, context: Dict[str, Any]) -> None:
        """执行前hook"""
        print(f"🚀 准备执行DSL: {dsl_id}")
        if self.db:
            # 记录执行开始
            self.db.log_execution_start(dsl_id, context)
    
    @hookimpl
    def dsl_after_execution(self, dsl_id: str, context: Dict[str, Any],
                            result: Any, exception: Optional[Exception] = None) -> None:
        """执行后hook"""
        if exception:
            print(f"❌ DSL执行失败: {dsl_id}, 错误: {exception}")
            if self.db:
                self.db.log_execution_failure(dsl_id, str(exception))
        else:
            print(f"✅ DSL执行成功: {dsl_id}")
            if self.db:
                self.db.log_execution_success(dsl_id, result)
```

### 2. 注册和使用插件

```python
from pytest_dsl.core.hook_manager import hook_manager

# 创建插件实例
plugin = ComprehensivePlugin(database_connection=my_db)

# 注册插件
hook_manager.register_plugin(plugin, "comprehensive_plugin")

# 初始化（必需）
hook_manager.initialize()

print(f"已注册插件: {hook_manager.get_plugins()}")
```
## 变量Hook优先级

变量获取的优先级顺序：

1. **本地DSL变量** (最高优先级)
2. **测试上下文变量**
3. **YAML文件变量**
4. **Hook提供的变量** 🆕
5. **全局上下文变量** (最低优先级)

## 环境控制

通过环境变量控制当前环境：

```bash
# 设置环境
export PYTEST_DSL_ENVIRONMENT=dev     # 开发环境
export PYTEST_DSL_ENVIRONMENT=test    # 测试环境
export PYTEST_DSL_ENVIRONMENT=prod    # 生产环境

# 或者在代码中设置
import os
os.environ['PYTEST_DSL_ENVIRONMENT'] = 'test'
```

## 调试和监控

### 启用调试信息

```python
# 查看已注册的插件
print(f"已注册插件: {hook_manager.get_plugins()}")

# 查看变量源
from pytest_dsl.core.yaml_loader import load_yaml_variables_from_args
load_yaml_variables_from_args(
    yaml_files=[],
    yaml_vars_dir=None,
    project_root=os.getcwd(),
    environment='test'
)
```

### 错误处理

Hook调用失败时会记录警告但不影响正常流程：

```python
try:
    # Hook调用
    results = hook_manager.pm.hook.dsl_get_variable(var_name='api_url')
except Exception as e:
    print(f"Hook调用失败: {e}")
    # 继续使用其他变量源
```

## 最佳实践

### 1. 插件设计

- **职责单一**：每个插件专注一个特定功能
- **错误处理**：优雅处理异常，不影响主流程
- **性能考虑**：避免在hook中执行耗时操作
- **向后兼容**：确保插件的添加不破坏现有功能

### 2. 变量管理

- **环境隔离**：不同环境使用不同的变量配置
- **敏感信息**：敏感变量通过hook动态获取，不存储在代码中
- **缓存策略**：对于不变的变量使用适当的缓存
- **验证机制**：对关键变量进行验证确保正确性

### 3. 集成策略

- **渐进集成**：先在小范围试用，再逐步推广
- **监控观察**：监控hook的调用情况和性能影响
- **文档维护**：及时更新集成文档和示例
- **测试覆盖**：为hook插件编写充分的测试

## 优势总结

使用hook机制的优势：

1. **最小侵入性**：orbitest现有代码无需修改
2. **灵活扩展**：可以选择性实现需要的hook
3. **标准化接口**：使用pytest生态的pluggy标准
4. **动态配置**：支持运行时动态变量和配置
5. **易于维护**：清晰的职责分离
6. **向后兼容**：pytest-dsl原有功能完全保留
7. **环境支持**：完整的多环境变量管理
8. **错误恢复**：Hook失败时自动降级到其他数据源

通过这种方式，orbitest可以轻松地将pytest-dsl集成进来，在用例层面提供DSL高级模式选项，同时获得完整的变量管理和动态配置能力。 