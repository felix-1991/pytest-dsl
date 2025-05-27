# YAML远程服务器配置指南

## 概述

pytest-dsl支持通过YAML配置文件自动加载远程关键字服务器，无需在每个DSL文件中手动写`@remote`导入语句。这种方式特别适合需要全局配置多个远程服务器的场景。

## 功能特性

- **全局配置**：在YAML文件中一次性配置所有远程服务器
- **自动连接**：系统启动时自动连接配置的服务器
- **向后兼容**：与现有的`@remote`语法完全兼容
- **灵活配置**：支持API密钥、变量同步等高级配置
- **优先级控制**：DSL中的`@remote`可以覆盖YAML配置

## 配置格式

在YAML配置文件中添加`remote_servers`配置段：

```yaml
# 远程服务器配置
remote_servers:
  server_name:                     # 服务器配置名称
    url: "http://host:port/"       # 必需：服务器URL
    alias: "server_alias"          # 可选：服务器别名，默认使用配置名称
    api_key: "your_api_key"        # 可选：API密钥
    sync_config:                   # 可选：变量同步配置
      sync_global_vars: true       # 是否同步全局变量（g_开头）
      sync_yaml_vars: true         # 是否同步YAML配置变量
```

## 配置示例

### 基本配置

```yaml
remote_servers:
  main_server:
    url: "http://localhost:8270/"
    alias: "main"

  backup_server:
    url: "http://backup-host:8270/"
    alias: "backup"
```

### 完整配置

```yaml
remote_servers:
  production_server:
    url: "http://prod-server:8270/"
    alias: "prod"
    api_key: "prod_api_key_123"
    sync_config:
      sync_global_vars: true
      sync_yaml_vars: true

  test_server:
    url: "http://test-server:8270/"
    alias: "test"
    api_key: "test_api_key_456"
    sync_config:
      sync_global_vars: true
      sync_yaml_vars: false

  dev_server:
    url: "http://dev-server:8270/"
    # 使用默认配置
```

### 最小配置

```yaml
remote_servers:
  simple_server:
    url: "http://simple-host:8270/"
    # 其他配置项都是可选的
```

## 使用方式

### 1. 创建配置文件

在项目的`config`目录下创建YAML文件（如`remote_servers.yaml`）：

```yaml
remote_servers:
  main:
    url: "http://localhost:8270/"
    alias: "main"

  backup:
    url: "http://backup:8270/"
    alias: "backup"
```

### 2. 运行测试

#### 使用pytest插件（推荐）

使用pytest-dsl运行测试时，系统会自动加载配置：

```bash
# 使用默认config目录
pytest test_example.dsl

# 指定配置文件
pytest --yaml-vars config/remote_servers.yaml test_example.dsl

# 指定配置目录
pytest --yaml-vars-dir config test_example.dsl
```

#### 使用CLI工具

也可以使用独立的CLI工具：

```bash
# 使用默认config目录
python -m pytest_dsl.cli test_example.dsl

# 指定配置文件
python -m pytest_dsl.cli --yaml-vars config/remote_servers.yaml test_example.dsl

# 指定配置目录
python -m pytest_dsl.cli --yaml-vars-dir config test_example.dsl
```

**注意**：CLI和pytest插件使用相同的YAML加载逻辑，都支持远程服务器自动连接功能。

### 3. 在DSL中使用

配置的远程服务器会自动连接，可以直接在DSL中使用：

```dsl
@name: "远程关键字测试"

# 直接使用YAML中配置的远程服务器
main|[打印],内容: "使用主服务器"
backup|[打印],内容: "使用备用服务器"

# 仍然可以使用@remote语法添加新的服务器
@remote: "http://temp-server:8270/" as temp

temp|[打印],内容: "临时服务器"
```

## 配置优先级

1. **DSL中的@remote**：优先级最高，会覆盖YAML配置
2. **YAML配置**：全局默认配置
3. **默认值**：系统内置默认值

## 变量同步

YAML配置的远程服务器支持自动变量同步：

```yaml
remote_servers:
  server1:
    url: "http://server1:8270/"
    sync_config:
      sync_global_vars: true    # 同步g_开头的全局变量
      sync_yaml_vars: true      # 同步YAML配置变量

# 这些变量会自动同步到远程服务器
g_environment: "production"
g_base_url: "https://api.example.com"

http_clients:
  default:
    base_url: "https://api.example.com"
```

## 错误处理

- **连接失败**：系统会记录错误但不会中断启动
- **配置错误**：会跳过错误的配置项并继续处理其他配置
- **缺少URL**：必需的URL配置缺失时会跳过该服务器

## 调试信息

系统会输出详细的连接信息：

```
发现 2 个远程服务器配置
正在连接远程服务器: main_server (http://localhost:8270/) 别名: main
成功连接到远程服务器: main_server (http://localhost:8270/)
正在连接远程服务器: backup_server (http://backup:8270/) 别名: backup
连接远程服务器失败: backup_server (http://backup:8270/)
```

## 最佳实践

1. **环境分离**：为不同环境创建不同的配置文件
2. **安全考虑**：API密钥应该通过环境变量或安全存储管理
3. **别名规范**：使用有意义的别名，便于在DSL中识别
4. **配置验证**：定期检查远程服务器的可用性
5. **文档维护**：及时更新配置文档，便于团队协作

## 与现有功能的兼容性

- **完全向后兼容**：现有的`@remote`语法继续有效
- **混合使用**：可以同时使用YAML配置和DSL导入
- **覆盖机制**：DSL中的配置会覆盖YAML中的同名配置
- **变量共享**：所有远程服务器共享相同的变量同步机制
