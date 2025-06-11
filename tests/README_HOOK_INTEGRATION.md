# 测试平台Hook集成示例

这个示例展示了如何使用pytest-dsl的Hook机制来实现一个完整的测试平台案例管理系统。

## 文件结构

```
tests/
├── test_platform_hook_integration.py  # 完整的Hook集成示例
├── test_platform_hook_pytest.py      # pytest格式的测试
└── README_HOOK_INTEGRATION.md         # 本文档
```

## 功能特性

### 🗄️ 案例管理
- **案例存储**：DSL测试案例存储在SQLite数据库中
- **案例加载**：通过Hook机制从数据库加载DSL内容
- **案例列表**：支持按项目、标签等条件筛选案例
- **CRUD操作**：支持案例的增删改查操作

### 🔧 自定义关键字
- **关键字存储**：自定义关键字定义存储在数据库中
- **动态注册**：通过Hook机制自动注册关键字
- **业务封装**：提供用户登录、库存检查、订单创建等业务关键字

### 🌍 环境管理
- **多环境支持**：支持dev、test、prod等多个环境
- **变量配置**：环境变量存储在数据库中，支持动态获取
- **类型转换**：自动识别和转换布尔值、数字等类型

### 📊 监控统计
- **执行监控**：记录案例执行的开始、结束和耗时
- **统计信息**：提供案例、关键字、变量等的统计数据
- **错误处理**：完善的错误处理和日志记录

## 数据库结构

### test_cases表（测试案例）
- `id`: 案例ID
- `name`: 案例名称
- `description`: 案例描述
- `dsl_content`: DSL内容
- `tags`: 标签（JSON格式）
- `project_id`: 项目ID
- `created_at`: 创建时间
- `updated_at`: 更新时间

### custom_keywords表（自定义关键字）
- `id`: 关键字ID
- `name`: 关键字名称
- `dsl_content`: 关键字定义
- `description`: 描述
- `project_id`: 项目ID
- `created_at`: 创建时间

### environment_variables表（环境变量）
- `id`: 变量ID
- `var_name`: 变量名
- `var_value`: 变量值
- `environment`: 环境名称
- `project_id`: 项目ID
- `description`: 描述
- `created_at`: 创建时间

### projects表（项目）
- `id`: 项目ID
- `name`: 项目名称
- `description`: 项目描述
- `created_at`: 创建时间

## 运行示例

### 1. 独立运行演示

```bash
cd pytest-dsl
python tests/test_platform_hook_integration.py
```

输出示例：
```
🎯 测试平台Hook集成演示
==================================================

1. 平台统计信息
📊 平台统计: {'total_cases': 4, 'total_keywords': 3, 'total_variables': 12, 'total_projects': 1, 'database_path': '/tmp/xxx.db'}

2. 案例列表功能
📋 从测试平台获取到 4 个测试案例
   - 用户登录测试: 验证用户登录功能
   - 商品库存检查测试: 验证商品库存检查功能

3. 环境变量功能
🌍 环境 dev: api_url=https://api-dev.example.com, timeout=30, debug=True
🌍 环境 test: api_url=https://api-test.example.com, timeout=60, debug=False
🌍 环境 prod: api_url=https://api.example.com, timeout=120, debug=False

...
```

### 2. pytest运行

```bash
cd pytest-dsl
python -m pytest tests/test_platform_hook_pytest.py -v -s
```

### 3. 集成到CI/CD

```bash
# 在持续集成中运行
python -m pytest tests/test_platform_hook_pytest.py --tb=short
```

## Hook实现详解

### 1. DSL内容加载Hook

```python
@hookimpl
def dsl_load_content(self, dsl_id: str) -> Optional[str]:
    """从数据库加载DSL内容"""
    # 支持按ID或名称加载
    if dsl_id.isdigit():
        # 按ID查询
        cursor.execute("SELECT dsl_content FROM test_cases WHERE id = ?", (int(dsl_id),))
    else:
        # 按名称查询
        cursor.execute("SELECT dsl_content FROM test_cases WHERE name = ?", (dsl_id,))
    # ...
```

### 2. 变量提供Hook

```python
@hookimpl
def dsl_get_variable(self, var_name: str) -> Optional[Any]:
    """获取单个变量值"""
    environment = os.environ.get('PYTEST_DSL_ENVIRONMENT', 'dev')
    
    # 从数据库查询变量
    cursor.execute(
        "SELECT var_value FROM environment_variables WHERE var_name = ? AND environment = ?",
        (var_name, environment)
    )
    # 自动类型转换
    if var_value.lower() in ('true', 'false'):
        return var_value.lower() == 'true'
    elif var_value.isdigit():
        return int(var_value)
    else:
        return var_value
```

### 3. 关键字注册Hook

```python
@hookimpl
def dsl_register_custom_keywords(self, project_id: Optional[int] = None) -> None:
    """注册数据库中的自定义关键字"""
    # 查询关键字定义
    cursor.execute("SELECT name, dsl_content FROM custom_keywords WHERE project_id = ?", (project_id,))
    
    # 注册到关键字管理器
    for name, dsl_content in rows:
        custom_keyword_manager.register_keyword_from_dsl_content(
            dsl_content, f"测试平台:{name}"
        )
```

## 预置测试案例

### 1. 用户登录测试
- 测试用户登录功能的正常流程
- 使用自定义的"用户登录"关键字

### 2. 商品库存检查测试
- 测试商品库存检查的各种场景
- 验证库存充足和不足的情况

### 3. 订单创建流程测试
- 完整的业务流程测试
- 包含登录→库存检查→创建订单的完整链路

### 4. 环境配置验证
- 验证不同环境的配置是否正确
- 检查API地址、超时时间等配置参数

## 自定义关键字

### 1. 用户登录
```python
function 用户登录 (用户名, 密码) do
    # 发送登录请求
    [HTTP请求], 客户端: "default", 配置: '''
        method: POST
        url: ${api_url}/auth/login
        timeout: ${timeout}
        json:
            username: ${用户名}
            password: ${密码}
    '''
    # 返回模拟token
    token = "mock_token_${用户名}_123456"
    return ${token}
end
```

### 2. 检查商品库存
```python
function 检查商品库存 (商品ID, 最小库存=10) do
    # 发送库存查询请求
    [HTTP请求], 客户端: "default", 配置: '''
        method: GET
        url: ${api_url}/products/${商品ID}/stock
        timeout: ${timeout}
    '''
    # 返回库存信息
    return {
        "product_id": ${商品ID},
        "current_stock": 50,
        "min_stock": ${最小库存},
        "status": "充足"
    }
end
```

### 3. 创建订单
```python
function 创建订单 (用户ID, 商品列表, 收货地址) do
    # 生成订单号
    订单号 = "ORD_${用户ID}_" + str(time.time())
    
    # 发送创建订单请求
    [HTTP请求], 客户端: "default", 配置: '''
        method: POST
        url: ${api_url}/orders
        timeout: ${timeout}
        json:
            user_id: ${用户ID}
            products: ${商品列表}
            address: ${收货地址}
            order_no: ${订单号}
    '''
    
    return {
        "order_no": ${订单号},
        "status": "created"
    }
end
```

## 环境变量配置

### Dev环境
- `api_url`: https://api-dev.example.com
- `timeout`: 30
- `debug`: true
- `db_host`: localhost

### Test环境
- `api_url`: https://api-test.example.com
- `timeout`: 60
- `debug`: false
- `db_host`: test-db.example.com

### Prod环境
- `api_url`: https://api.example.com
- `timeout`: 120
- `debug`: false
- `db_host`: prod-db.example.com

## 扩展建议

### 1. 集成到实际测试平台

```python
# 在orbitest或其他测试平台中使用
class OrbitestDSLPlugin(TestPlatformPlugin):
    def __init__(self, orbitest_session):
        self.session = orbitest_session
        super().__init__()
    
    def dsl_load_content(self, dsl_id: str) -> Optional[str]:
        # 从orbitest数据库加载
        case = self.session.query(TestCase).filter_by(id=int(dsl_id)).first()
        return case.dsl_content if case else None
```

### 2. 添加更多Hook功能

- **案例验证**：实现`dsl_validate_content`验证DSL语法
- **内容转换**：实现`dsl_transform_content`进行DSL预处理
- **执行控制**：实现`dsl_create_executor`自定义执行器

### 3. 性能优化

- **连接池**：使用数据库连接池提高性能
- **缓存**：添加变量和关键字的缓存机制
- **异步**：支持异步Hook调用

### 4. 监控扩展

- **执行日志**：详细记录每次执行的日志
- **性能监控**：监控Hook调用的性能
- **告警机制**：异常情况的告警通知

## 总结

这个示例演示了pytest-dsl Hook机制的强大功能：

1. **无侵入集成**：外部系统可以无缝集成DSL功能
2. **灵活扩展**：支持自定义的内容加载、变量提供等
3. **完整生态**：覆盖案例管理的完整生命周期
4. **易于维护**：清晰的架构和完善的测试

通过这种方式，测试平台可以：
- 提供可视化的DSL案例编辑器
- 实现多环境的配置管理
- 支持团队协作的关键字库
- 构建完整的测试执行引擎 