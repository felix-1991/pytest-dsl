# 远程关键字

pytest-dsl支持分布式测试，可以在不同机器上执行关键字。这个功能让您能够轻松实现跨网络的测试协调和分布式测试执行。

## 基本概念

远程关键字功能允许您：

- 在远程服务器上执行关键字
- 跨网络进行测试协调
- 实现分布式测试架构
- 无缝传递变量和状态

## 快速开始

### 第一步：启动远程服务器

在远程机器上启动关键字服务：

```bash
# 基本启动
pytest-dsl-server

# 指定地址和端口
pytest-dsl-server --host 0.0.0.0 --port 8270

# 带API密钥的安全启动
pytest-dsl-server --host 0.0.0.0 --port 8270 --api-key your_secret_key
```

### 第二步：在DSL中连接远程服务器

```python
@name: "远程关键字示例"
@remote: "http://remote-server:8270/" as remote_machine

# 在远程机器上执行关键字
remote_machine|[打印], 内容: "这在远程机器上执行"

# 远程执行并获取返回值
result = remote_machine|[生成随机数], 最小值: 1, 最大值: 100
[打印], 内容: "远程生成的随机数: ${result}"
```

### 第三步：运行测试

```bash
pytest-dsl your_test.dsl
```

## 服务器配置

### 命令行参数

```bash
pytest-dsl-server [OPTIONS]

选项:
  --host TEXT        服务器监听地址 (默认: localhost)
  --port INTEGER     服务器监听端口 (默认: 8270)
  --api-key TEXT     API密钥，用于客户端认证
  --extensions TEXT  扩展模块路径，多个路径用逗号分隔
  --help            显示帮助信息
```

### 环境变量配置

```bash
# 设置默认配置
export PYTEST_DSL_REMOTE_HOST=0.0.0.0
export PYTEST_DSL_REMOTE_PORT=8270
export PYTEST_DSL_REMOTE_API_KEY=your_secret_key
```

## DSL语法

### 远程服务器声明

```python
# 基本连接
@remote: "http://localhost:8270/" as server1

# 注意：当前不支持在 @remote 中直接指定 API 密钥
# 需要在 YAML 配置文件中配置认证信息

# 多个远程服务器
@remote: "http://server1:8270/" as server1
@remote: "http://server2:8270/" as server2
```

### 远程关键字调用

```python
# 基本语法
remote_server|[关键字名称], 参数1: 值1, 参数2: 值2

# 带返回值
result = remote_server|[关键字名称], 参数: 值

# 复杂参数
remote_server|[HTTP请求], 客户端: "default", 配置: '''
    method: POST
    url: https://api.example.com
    request:
        json:
            name: "test"
            value: 123
'''
```

## YAML配置自动加载（推荐）

在YAML配置文件中定义远程服务器，无需在DSL中声明：

### 配置文件示例

```yaml
# config/vars.yaml
remote_servers:
  main_server:
    url: "http://server1:8270/"
    alias: "server1"
    api_key: "your_api_key"
    sync_config:
      sync_global_vars: true
      sync_yaml_vars: true

  backup_server:
    url: "http://server2:8270/"
    alias: "server2"
```

### 直接使用

```python
@name: "使用YAML配置的远程服务器"

# 无需@remote导入，直接使用
server1|[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://api.example.com/users/1
'''

server2|[打印], 内容: "备用服务器执行"
```

### 运行时指定配置

```bash
pytest-dsl tests/ --yaml-vars config/vars.yaml
```

## 支持的关键字

所有内置关键字都支持远程执行：

### 基础关键字

```python
# 远程打印
remote_server|[打印], 内容: "Hello from remote!"

# 远程等待
remote_server|[等待], 秒数: 2

# 远程生成随机数
random_num = remote_server|[生成随机数], 最小值: 1, 最大值: 100
```

### HTTP关键字

```python
# 远程HTTP请求
result = remote_server|[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/1
    captures:
        post_id: ["jsonpath", "$.id"]
        post_title: ["jsonpath", "$.title"]
    asserts:
        - ["status", "eq", 200]
'''

[打印], 内容: "远程请求结果: ${result}"
```

### 断言关键字

```python
# 远程断言
remote_server|[断言], 条件: "1 + 1 == 2", 消息: "数学计算错误"
```

### 全局变量关键字

```python
# 远程设置全局变量
remote_server|[设置全局变量], 变量名: "remote_token", 值: "abc123"

# 远程获取全局变量
token = remote_server|[获取全局变量], 变量名: "remote_token"
```

## 变量传递

### 无缝变量传递

客户端的变量会自动传递到远程服务器：

```python
# 客户端定义的变量
api_url = "https://jsonplaceholder.typicode.com"
user_token = "abc123"

# 远程服务器可以直接使用这些变量
remote_machine|[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: ${api_url}/users/1
    request:
        headers:
            Authorization: "Bearer ${user_token}"
'''
```

### 变量捕获

远程执行的结果可以捕获到本地：

```python
# 远程HTTP请求并捕获变量
result = remote_server|[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/users/1
    captures:
        user_name: ["jsonpath", "$.name"]
        user_email: ["jsonpath", "$.email"]
'''

# 注意：远程捕获的变量需要通过返回值访问
[打印], 内容: "远程捕获结果: ${result}"
```

## 实际应用示例

### 分布式API测试

```python
@name: "分布式API测试"
@remote: "http://server1:8270/" as server1
@remote: "http://server2:8270/" as server2

# 在server1上测试用户API
server1|[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/users/1
    captures:
        user_id: ["jsonpath", "$.id"]
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "Server1: 获取用户信息"

# 在server2上测试文章API
server2|[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://jsonplaceholder.typicode.com/posts/1
    captures:
        post_id: ["jsonpath", "$.id"]
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "Server2: 获取文章信息"

[打印], 内容: "分布式测试完成"
```

### 跨网络测试协调

```python
@name: "跨网络测试协调"
@remote: "http://internal-server:8270/" as internal_server
@remote: "http://external-server:8270/" as external_server

# 内网服务器测试内部API
internal_server|[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://internal-api.company.com/health
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "内网健康检查"

# 外网服务器测试公开API
external_server|[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: https://api.company.com/public/status
    asserts:
        - ["status", "eq", 200]
''', 步骤名称: "外网状态检查"

[打印], 内容: "跨网络测试协调完成"
```

### 负载均衡测试

```python
@name: "负载均衡测试"
@remote: "http://node1:8270/" as node1
@remote: "http://node2:8270/" as node2
@remote: "http://node3:8270/" as node3

# 在多个节点上并行执行相同的测试
api_endpoint = "https://api.example.com/load-test"

node1|[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: ${api_endpoint}
    asserts:
        - ["status", "eq", 200]
        - ["response_time", "lt", 1000]
''', 步骤名称: "Node1: 负载测试"

node2|[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: ${api_endpoint}
    asserts:
        - ["status", "eq", 200]
        - ["response_time", "lt", 1000]
''', 步骤名称: "Node2: 负载测试"

node3|[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: ${api_endpoint}
    asserts:
        - ["status", "eq", 200]
        - ["response_time", "lt", 1000]
''', 步骤名称: "Node3: 负载测试"

[打印], 内容: "负载均衡测试完成"
```

## 最佳实践

### 1. 服务器命名规范

```python
# ✅ 好的命名
@remote: "http://api-server:8270/" as api_server
@remote: "http://db-server:8270/" as db_server
@remote: "http://cache-server:8270/" as cache_server

# ❌ 避免的命名
@remote: "http://server1:8270/" as s1
@remote: "http://server2:8270/" as s2
```

### 3. 合理使用远程执行

```python
# ✅ 适合远程执行的场景
# - 需要在特定网络环境中执行的测试
# - 需要访问内部资源的测试
# - 分布式负载测试

# ❌ 不适合远程执行的场景
# - 简单的本地计算
# - 频繁的小操作（网络开销大）
```

### 4. 安全考虑

```python
# 使用API密钥保护远程服务器
@remote: "http://production-server:8270/" as prod_server with api_key="${PROD_API_KEY}"

# 避免在代码中硬编码密钥
# ❌ 不要这样做
@remote: "http://server:8270/" as server with api_key="hardcoded_key"

# ✅ 使用环境变量或配置文件
@remote: "http://server:8270/" as server with api_key="${API_KEY}"
```

## 调试和故障排除

### 常见问题

#### Q: 远程服务器连接失败

A: 检查以下几点：

1. 确认远程服务器已启动
2. 检查网络连接和防火墙设置
3. 验证地址和端口是否正确
4. 确认API密钥是否匹配

```bash
# 测试连接
curl http://remote-server:8270/health
```

#### Q: 变量传递不正确

A: 确保变量在远程调用前已定义：

```python
# ✅ 正确的顺序
api_url = "https://api.example.com"
remote_server|[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: ${api_url}
'''

# ❌ 错误的顺序
remote_server|[HTTP请求], 客户端: "default", 配置: '''
    method: GET
    url: ${api_url}  # api_url还未定义
'''
api_url = "https://api.example.com"
```

#### Q: 远程执行超时

A: 调整超时设置或检查网络状况：

```python
# 在YAML配置中设置超时
remote_servers:
  slow_server:
    url: "http://slow-server:8270/"
    timeout: 60  # 增加超时时间
```

### 调试技巧

```bash
# 使用pytest运行获得详细输出
pytest test_runner.py -v -s

# 启动远程服务器
pytest-dsl-server --host 0.0.0.0 --port 8270
```

## 限制和注意事项

### 当前限制

1. **网络依赖** - 远程执行依赖网络连接，网络问题会影响测试稳定性
2. **性能开销** - 远程调用有网络延迟，不适合频繁的小操作
3. **状态同步** - 远程服务器的状态变化不会自动同步到客户端

### 注意事项

1. **安全性** - 在生产环境中务必使用API密钥
2. **资源管理** - 及时清理远程服务器上的临时资源
3. **错误处理** - 做好网络异常的处理准备

## 下一步

现在您已经掌握了远程关键字的基本使用，可以继续学习：

- **[环境配置管理](./configuration)** - 管理多环境的远程服务器配置
- **[最佳实践](./best-practices)** - 学习分布式测试的最佳实践
- **[CI/CD集成](./cicd)** - 在持续集成中使用远程关键字 