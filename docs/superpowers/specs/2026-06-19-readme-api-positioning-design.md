# pytest-dsl README API 定位重构设计

## 目标

将仓库首页从长篇功能教程改为产品价值入口：首先说明 pytest-dsl 如何用 DSL 语法约束自动化测试规划、用例结构和报告层级，再以接口自动化为首要场景，通过可运行示例和 Pytest DSL Studio 截图建立完整认知。

## 核心叙事

README 按以下顺序回答读者的问题：

1. pytest-dsl 解决什么问题：普通 pytest 依赖团队自行约定函数结构和 `allure.step`，pytest-dsl 将步骤、参数、赋值、控制流和关键字调用固化为统一语法。
2. 为什么先用于接口自动化：请求配置、响应捕获、断言和上下文传递天然适合结构化表达，也容易形成业务可读的用例和报告。
3. 代码与报告如何对应：一个 DSL API 示例同时展示源码步骤和 Allure 中的层级化执行记录。
4. GUI 有什么作用：Pytest DSL Studio 提供项目浏览、DSL 编辑、关键字发现、运行/调试和报告查看，但不替代 pytest-dsl 核心执行能力。
5. 如何开始：从安装、加载示例项目、运行 API 用例到查看报告形成最短闭环。

## README 信息架构

新的根 README 控制为产品首页长度，不再承载完整手册：

- 标题、徽章和一句话定位。
- “为什么是 pytest-dsl”：用普通 pytest + `allure.step` 与 DSL 的简短对比说明语法约束价值。
- “一个 API 用例看懂核心价值”：展示请求、捕获、断言和后续变量使用。
- “从 DSL 到可读报告”：解释语法节点如何映射到 Allure 步骤、参数、附件和失败位置。
- “Pytest DSL Studio”：展示 GUI 在编辑、执行、调试和报告链路中的辅助作用。
- “5 分钟运行”：CLI 路径和 GUI 路径各给出最短命令。
- “核心能力”：API、变量/配置、关键字扩展、远程执行、pytest/Allure 生态。
- “进一步阅读”：链接到 `docs/` 中现有专题文档，删除 README 内重复教程。
- 安装要求、贡献和许可证。

## 可运行 API 示例

将 `examples/gui_validation` 从纯本地临时验收目录提升为可提交、可截图的 Studio 示例项目，同时继续忽略运行生成物。

新增一条自包含 API 业务链路：

- 本地 mock API 服务提供用户详情和登录接口，避免依赖公网服务。
- DSL 用例展示 GET/POST 请求、状态码与 JSONPath 断言、响应字段捕获、变量传递和业务断言。
- 用例名称、步骤名称和断言消息使用面向业务的中文文案，以便在 Allure 中直接形成可读层级。
- 示例 README 写清启动 mock 服务、CLI 执行、Studio 加载和报告生成命令。

`.gitignore` 只放开示例源码和文档；继续忽略 `.pytest-dsl-gui/`、`.pytest-dsl-generated/`、`allure-results/`、`allure-report/`、缓存和系统文件。

## 截图方案

截图存放在 `docs/images/readme/`，根 README 使用相对路径引用。计划保留三张真实截图：

1. `studio-api-editor.png`：Studio 加载 `examples/gui_validation`，编辑器显示 API DSL，用于展示可读源码和项目结构。
2. `studio-api-run.png`：同一用例运行完成，底部输出区显示成功结果，用于展示编辑到执行的闭环。
3. `allure-api-report.png`：Allure 展开 API 用例步骤，用于展示 DSL 语法约束如何转化为可读报告。

截图统一使用当前 Pytest DSL Studio 界面，裁掉桌面无关区域和敏感路径；窗口尺寸保持一致，正文在常见 GitHub README 宽度下可辨认。

## 实现边界

- 不修改 DSL 语法、HTTP 关键字行为、Allure 事件结构或 Electron GUI 功能。
- 不在 README 中宣称当前仓库没有验证过的能力。
- 不把 Studio 描述成核心框架或必需运行时；它是可选辅助工具。
- 不保留原 README 中重复、过时或无法从当前代码验证的长篇示例。
- 不提交 Allure 静态站点、运行结果、Electron 构建产物或本地元数据。

## 验证与验收

- API 示例可在 `examples/gui_validation` 目录按 README 命令运行通过。
- 示例执行生成 Allure 数据，报告能看到业务步骤、HTTP 请求步骤、捕获值和断言结果。
- Studio 能加载示例项目并运行 API DSL，用截图证明实际渲染效果。
- 根 README 中的本地链接和图片路径全部存在。
- README 中的安装命令、CLI 参数和 Studio 启动命令与当前项目配置一致。
- 执行相关 Python 测试、`npm run check --prefix electron-gui` 和 Markdown/链接静态检查，确认文档改写没有破坏已有能力。
