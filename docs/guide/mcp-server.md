# MCP 服务

pytest-dsl 可以以 MCP（Model Context Protocol）服务模式启动，把已加载的关键字暴露给支持 MCP 的 AI 客户端使用。MCP 服务会提供关键字查询、关键字契约查看、关键字执行和共享变量读写等工具。

## 启动方式

安装 pytest-dsl 后，可以使用独立命令启动：

```bash
pytest-dsl-mcp
```

也可以通过 `pytest-dsl` 的子命令启动：

```bash
pytest-dsl mcp
```

默认使用 `stdio` 传输，适合由 MCP 客户端直接拉起进程。stdio 模式下标准输出用于 MCP JSON-RPC 消息，运行日志会写到标准错误。

## stdio 模式

stdio 是推荐的客户端集成方式：

```bash
pytest-dsl-mcp --transport stdio
```

等价写法：

```bash
pytest-dsl mcp --transport stdio
```

MCP 客户端配置示例：

```json
{
  "mcpServers": {
    "pytest-dsl": {
      "command": "pytest-dsl-mcp",
      "args": ["--transport", "stdio"]
    }
  }
}
```

如果需要加载项目扩展，可以在参数中传入 `--extensions`：

```json
{
  "mcpServers": {
    "pytest-dsl": {
      "command": "pytest-dsl-mcp",
      "args": [
        "--transport",
        "stdio",
        "--extensions",
        "extensions/"
      ]
    }
  }
}
```

## HTTP 模式

如果客户端需要连接一个常驻 HTTP MCP 服务，可以使用 `http` 传输：

```bash
pytest-dsl-mcp --transport http --host 127.0.0.1 --port 8765 --path /mcp
```

等价写法：

```bash
pytest-dsl mcp --transport http --host 127.0.0.1 --port 8765 --path /mcp
```

启动后 MCP 端点为：

```text
http://127.0.0.1:8765/mcp
```

健康检查地址：

```text
http://127.0.0.1:8765/healthz
```

## 常用参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--transport` | `stdio` | MCP 传输模式，可选 `stdio` 或 `http` |
| `--host` | `127.0.0.1` | HTTP 服务监听地址，仅 `--transport http` 时使用 |
| `--port` | `8765` | HTTP 服务监听端口，仅 `--transport http` 时使用 |
| `--path` | `/mcp` | HTTP MCP 端点路径，仅 `--transport http` 时使用 |
| `--extensions` | 无 | 额外扩展模块、文件或目录，多个值用逗号分隔 |
| `--max-concurrency` | `20` | 最大并发关键字执行数 |
| `--no-keyword-tools` | 关闭 | 只暴露通用 MCP 工具，不为每个关键字生成独立工具 |

## 暴露的工具

MCP 服务默认暴露通用工具和按关键字生成的动态工具。

通用工具包括：

- `pytest_dsl_list_keywords`：列出当前已加载关键字
- `pytest_dsl_get_keyword_contract`：查看关键字参数、返回值和文档
- `pytest_dsl_run_keyword`：按关键字名称执行关键字
- `pytest_dsl_set_shared_variable`：写入共享变量
- `pytest_dsl_get_shared_variable`：读取共享变量
- `pytest_dsl_list_shared_variables`：列出共享变量

默认还会为每个已加载关键字生成一个独立 MCP 工具，工具名以 `pytest_dsl_keyword__` 开头。如果只希望保留通用工具，可以这样启动：

```bash
pytest-dsl-mcp --no-keyword-tools
```

## 加载扩展关键字

MCP 服务启动时会自动加载 pytest-dsl 默认关键字和可发现的扩展。需要额外加载项目内扩展时，使用 `--extensions`：

```bash
# 加载单个目录
pytest-dsl-mcp --extensions extensions/

# 加载多个扩展
pytest-dsl-mcp --extensions "ext1.py,ext2.py,extensions/"
```

HTTP 模式同样支持扩展加载：

```bash
pytest-dsl-mcp \
  --transport http \
  --host 127.0.0.1 \
  --port 8765 \
  --extensions extensions/
```

## 使用建议

- 本地 AI 客户端优先使用 `stdio`，由客户端负责启动和管理进程生命周期。
- 需要多个客户端共享同一个服务时使用 `http`，并优先绑定到 `127.0.0.1`。
- 在 HTTP 模式下监听 `0.0.0.0` 前，请确认网络访问控制和关键字执行风险。
- 若关键字会修改外部系统状态，建议通过客户端侧的工具审批机制控制调用。
