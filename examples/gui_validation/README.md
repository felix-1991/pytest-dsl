# Pytest DSL Studio API 验证项目

这个目录用于 Pytest DSL Studio 演示和 pytest-dsl API 回归验证。接口请求链路只使用框架内置的 `[HTTP请求]`，结尾再用通用 `[断言]` 与 `[打印]` 校验和展示结果；不需要额外编写 Python 请求客户端、pytest fixture 或 `allure.step` 包装。

## 目录结构

```text
examples/gui_validation/
├── config/
│   └── api.yaml
├── tests/
│   └── api_quickstart.dsl
└── tools/
    └── mock_api_server.py
```

## 运行 API 示例

示例链路依次查询用户、登录并捕获访问令牌、携带令牌查询账户状态。mock 服务只使用 Python 标准库，不依赖公网接口。

在当前目录启动服务：

```bash
python tools/mock_api_server.py
```

另开一个终端，在当前目录运行 DSL：

```bash
pytest-dsl tests/api_quickstart.dsl --yaml-vars config/api.yaml
```

这个用例实际验证：

- `GET` 和 `POST` 请求；
- YAML 客户端与请求配置；
- 状态码和 JSONPath 断言；
- JSONPath 响应字段捕获；
- 捕获变量在后续请求 URL、请求体和请求头中的传递；
- DSL 业务步骤到 Allure 步骤和摘要附件的映射。

## 生成 Allure 结果

保持 mock API 运行，在当前目录执行：

```bash
python -m pytest tests/api_quickstart.dsl \
  --yaml-vars config/api.yaml \
  --alluredir allure-results -q
```

当前实现会在 Allure 中生成自定义业务步骤，并附带 `HTTP请求摘要`、`HTTP响应摘要`、`变量捕获摘要` 和 `HTTP断言摘要`。`allure-results/` 是运行产物，不提交到仓库。

## 在 Pytest DSL Studio 中加载

从仓库根目录启动 Studio：

```bash
npm install --prefix electron-gui
npm start --prefix electron-gui
```

在 Studio 中：

1. 将项目目录选择为 `examples/gui_validation`。
2. 在配置选择器中勾选 `config/api.yaml`。
3. 打开 `tests/api_quickstart.dsl`。
4. 使用运行功能查看 CLI 执行结果。
5. 在构建页选择 API 用例并运行，查看内嵌 Allure 报告。

Studio 构建页使用 pytest 原生收集和 `--alluredir`；内嵌实时报告需要本机存在 Allure 3 CLI。Studio 是可选辅助工具，CLI 和 pytest 集成不依赖它。

## 不提交的运行产物

以下目录或文件由 CLI、pytest、Studio 或 Allure 生成，已通过 `.gitignore` 排除：

- `.pytest-dsl-gui/`
- `.pytest-dsl-generated/`
- `allure-results/`
- `allure-report/`
- `__pycache__/`
- `.DS_Store`
