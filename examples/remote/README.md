# 远程关键字示例

本目录包含了远程关键字功能的各种示例，用于验证和演示远程关键字的功能。

## 目录结构

- `basic_remote_test.dsl` - 基础远程关键字测试
- `http_remote_test.dsl` - 远程HTTP请求功能测试
- `capture_variables_test.dsl` - 远程变量捕获功能测试
- `session_management_test.dsl` - 远程会话管理测试
- `global_variables_test.dsl` - 远程全局变量测试
- `comprehensive_test.dsl` - 综合功能测试
- `multi_server_test.dsl` - 多服务器协作测试

## 使用方法

### 1. 启动远程关键字服务器

```bash
# 在一个终端中启动服务器
python -m pytest_dsl.remote.keyword_server --host localhost --port 8270
```

### 2. 运行示例测试

```bash
# 运行单个示例
pytest-dsl examples/remote/basic_remote_test.dsl

# 运行所有示例
pytest-dsl examples/remote/

# 运行特定示例
pytest-dsl examples/remote/http_remote_test.dsl
```

### 3. 多服务器测试

对于多服务器测试，需要在不同端口启动多个服务器：

```bash
# 终端1
python -m pytest_dsl.remote.keyword_server --host localhost --port 8270

# 终端2
python -m pytest_dsl.remote.keyword_server --host localhost --port 8271

# 然后运行多服务器测试
pytest-dsl examples/remote/multi_server_test.dsl
```

## 示例说明

### 基础功能验证
- 远程关键字调用
- 返回值处理
- 错误处理

### HTTP功能验证
- 远程HTTP请求
- 变量捕获
- 会话管理
- 响应保存

### 高级功能验证
- 全局变量同步
- 多服务器协作
- 性能测试

## 注意事项

1. 确保远程服务器已启动并可访问
2. 检查网络连接和防火墙设置
3. 验证端口是否被占用
4. 查看服务器日志排查问题

## 故障排除

如果测试失败，请检查：

1. **服务器状态**：确认远程服务器正在运行
2. **网络连接**：测试网络连通性
3. **端口占用**：确认端口未被其他程序占用
4. **日志信息**：查看详细的错误日志

## 相关文档

- [远程关键字使用指南](../../docs/remote-keywords-usage.md)
- [远程关键字开发指南](../../docs/remote-keywords-development.md)
