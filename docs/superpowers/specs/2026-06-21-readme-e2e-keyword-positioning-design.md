# README 端到端与自定义关键字定位设计

## 目标

在保持“接口测试是 pytest-dsl 最直接切入点”的前提下，补充框架也适合组织端到端测试，并准确说明其扩展方式与 Robot Framework 的相似点和边界。

## 文案位置

在根 README 的“从 DSL 到可读报告”之后、“Pytest DSL Studio”之前增加一个短章节“从接口测试扩展到端到端”。同时在“核心能力”的扩展与集成列表中增加一条端到端组合能力说明。

## 事实依据

README 只描述仓库当前已经具备的机制：

- DSL 可以通过 `function ... do ... end` 定义自定义关键字；
- `.resource` 文件可以沉淀和复用 DSL 关键字；
- Python 关键字可以通过项目 `keywords/`、关键字注册机制或插件提供；
- Python 关键字可以调用 Python 库和外部驱动；
- 关键字可以通过 XML-RPC 远程执行；
- DSL 用例可以把内置 HTTP 关键字与团队自定义的领域关键字组合成业务流程。

## Robot Framework 对比边界

使用“类似 Robot Framework 的关键字驱动扩展方式”描述共同点：用业务关键字表达流程，把具体驱动细节封装在关键字实现中。

必须同时明确：

- pytest-dsl 基于 pytest，并继续使用 pytest 的收集、fixture、插件和命令行生态；
- pytest-dsl 不兼容 Robot Framework 的语法、库接口或现有用例；
- 浏览器、移动端、数据库、消息队列等端到端能力需要团队提供对应的 Python、插件或远程关键字，不宣称全部由 pytest-dsl 内置。

## 示例边界

本次不新增端到端执行示例或截图。README 使用一段简短的组合示意，说明 HTTP 内置关键字与自定义业务关键字可以处在同一 DSL 流程中；示意不得引用仓库中不存在的内置 UI、数据库或移动端关键字。

## 验证

- README 回归测试固定新章节标题、Robot Framework 边界表述及自定义关键字机制；
- README 本地链接检查继续通过；
- 完整 pytest 回归通过；
- `git diff --check` 通过。
