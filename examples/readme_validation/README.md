# README.md 示例验证

这个目录包含了主README.md文档中所有示例的可运行版本，用于确保文档中的示例都能正常工作。

## 目录结构

```
examples/readme_validation/
├── README.md                 # 本文档
├── run_all_tests.py         # 批量运行所有示例的脚本
├── config/
│   └── dev.yaml            # 测试配置文件
├── utils.resource          # 资源文件示例
├── hello.dsl               # 第一个测试示例
├── basic_syntax.dsl        # 基本语法示例
├── builtin_keywords.dsl    # 内置关键字示例
├── custom_keywords.dsl     # 自定义关键字示例
├── resource_usage.dsl      # 资源文件使用示例
├── api_basic.dsl           # 基础API测试示例
├── api_params.dsl          # 带参数的API请求示例
├── api_capture.dsl         # 数据捕获示例
├── yaml_vars.dsl           # YAML变量使用示例
├── variable_access.dsl     # 变量访问语法示例
├── assertion_retry.dsl     # 断言重试机制示例
├── auth_test.dsl           # 认证功能测试示例
├── auth.resource           # 认证相关关键字资源文件
├── data_driven.dsl         # 数据驱动测试示例（需要pytest运行）
├── data_driven.csv         # 数据驱动测试数据文件
└── test_runner.py          # pytest集成示例
```

## 运行方式

### 运行单个示例

```bash
# 进入验证目录
cd examples/readme_validation

# 运行单个示例
pytest-dsl hello.dsl
pytest-dsl api_basic.dsl
```

### 批量运行所有示例

```bash
# 使用验证脚本
python run_all_tests.py
```

### 使用pytest运行（包括数据驱动测试）

```bash
# 运行pytest集成示例
python test_runner.py

# 或者直接使用pytest
pytest test_runner.py -v
```

## 示例说明

### 基础功能示例

- **hello.dsl**: 演示基本的DSL语法，包括变量定义、循环、断言和teardown
- **basic_syntax.dsl**: 展示变量类型、条件判断和循环结构
- **builtin_keywords.dsl**: 内置关键字的使用，如打印、断言、等待、随机数生成等

### 自定义关键字示例

- **custom_keywords.dsl**: 演示如何定义和使用自定义关键字（函数）
- **utils.resource**: 资源文件示例，包含可复用的关键字
- **resource_usage.dsl**: 演示如何导入和使用资源文件中的关键字

### API测试示例

- **api_basic.dsl**: 基础的HTTP GET请求测试
- **api_params.dsl**: 带查询参数的API请求
- **api_capture.dsl**: 演示如何捕获API响应数据并在后续测试中使用

### 配置管理示例

- **config/dev.yaml**: 环境配置文件，包含API地址、HTTP客户端配置、测试数据等
- **yaml_vars.dsl**: 演示如何使用YAML配置文件中的变量
- **variable_access.dsl**: 展示增强的变量访问语法

### 进阶功能示例

- **assertion_retry.dsl**: 演示HTTP请求的断言重试机制
- **auth_test.dsl**: 完整的认证功能测试示例
- **auth.resource**: 认证相关关键字资源文件
- **data_driven.dsl**: 数据驱动测试示例（需要pytest运行）
- **data_driven.csv**: 数据驱动测试数据文件

### pytest集成示例

- **test_runner.py**: 演示如何使用pytest运行DSL文件，包括数据驱动测试

## 验证结果

最近一次验证结果：
- ✅ 通过: 13
- ❌ 失败: 0
- 📊 总计: 13

🎉 所有README.md示例都验证通过！

## 注意事项

1. 这些示例使用了真实的API端点（jsonplaceholder.typicode.com）进行测试
2. 配置文件中的变量引用已经简化，避免了复杂的嵌套引用问题
3. 变量访问示例使用了实际可用的YAML配置变量
4. 所有示例都经过实际运行验证，确保功能正常

## 维护说明

当主README.md中的示例发生变化时，应该：

1. 更新对应的DSL文件
2. 运行 `python run_all_tests.py` 验证所有示例
3. 确保所有测试都通过后再提交更改

这样可以确保文档中的示例始终是可运行和正确的。
