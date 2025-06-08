# pytest-dsl 测试目录

本目录包含pytest-dsl框架的各种测试用例和测试工具。

## 目录结构

### 重试功能测试
- `test_retry_functionality.dsl` - 重试功能的综合测试用例
- `test_retry_runner.py` - 重试功能的测试运行器
- `test_mock_server.py` - Mock HTTP服务器，用于测试重试逻辑
- `mock_config.yaml` - Mock服务器的配置文件

### 变量同步测试
- `test_enhanced_variable_access.py` - 增强变量访问测试
- `test_end_to_end_seamless.py` - 端到端无缝测试
- `test_seamless_variable_sync.py` - 无缝变量同步测试
- `test_variable_sync.py` - 变量同步测试
- `test_variable_sync_demo.py` - 变量同步演示测试

### HTTP功能测试
- `test_http_assertions_extractors.py` - HTTP断言和提取器测试

## 运行测试

### 重试功能测试
```bash
cd tests
python test_retry_runner.py
```

### 其他Python测试
```bash
cd tests
python -m pytest test_*.py
```

### DSL测试文件
```bash
cd tests  
pytest-dsl --yaml-vars mock_config.yaml test_retry_functionality.dsl
```

## Mock服务器

Mock服务器提供以下API端点：
- `GET /api/health` - 健康检查
- `GET /api/retry/fail-then-success` - 失败后成功场景（用于测试重试）
- `GET /api/retry/random-fail` - 随机失败场景
- `GET /api/reset` - 重置服务器状态
- 其他测试用端点...

可以单独启动Mock服务器：
```bash
cd tests
python test_mock_server.py
```

## 注意事项

1. 重试功能测试需要Mock服务器运行在8888端口
2. 测试前会自动启动Mock服务器
3. 测试结束后会自动停止Mock服务器
4. 如果端口被占用，可以使用 `lsof -ti:8888 | xargs kill -9` 清理进程 