# Electron GUI 运行时解析修复设计

## 目标

修复 Pytest DSL Studio 打包后从桌面启动时因 PATH 不完整而触发的 `spawn python ENOENT`，并让 Python、pytest-dsl、pytest 与 Allure 3 的运行时选择在运行、调试、构建、关键字加载和报告导出链路中保持一致。

## 已确认根因

- `executionService.js` 和 `buildService.js` 在公开 CLI 不可用时，各自固定回退到裸 `python`，没有复用已经存在的 `pythonEnvService.js`。
- macOS Finder、Windows 开始菜单和 Linux 桌面启动的应用不会可靠继承交互式 shell PATH，因此终端中可用的 `python`、pyenv 和 Allure 不一定能被打包应用发现。
- Allure 链路不会直接抛出 `spawn python ENOENT`，但当前打包产物没有内置 Allure CLI；找不到外部 Allure 3 时，实时报告和 HTML 导出都会不可用。

## 方案边界

采用“自动发现 + 项目级显式配置”，不把 Python、pytest-dsl 或 Allure CLI 打进 Electron 安装包。

- 默认自动发现项目根目录下的 `.venv` 或 `venv`。
- 自动发现失败时，再检查进程环境和当前 PATH 中的 Python/Allure 候选。
- 用户可以在 Studio 的配置下拉区选择项目使用的 Python 和 Allure 可执行文件。
- 显式配置保存在项目现有的 `.pytest-dsl-gui/metadata.json` 中；该目录本来就是本地运行元数据，不进入源码提交。
- Python 配置要求解释器环境已经安装 `pytest-dsl` 及项目测试依赖。
- Allure 仍为可选能力：缺失时测试构建可以继续生成 `allure-results`，但实时报告和报告导出会给出可执行的安装或配置提示。

## 组件设计

### 1. 统一运行时服务

扩展 `pythonEnvService.js`，并新增独立的 Allure 解析能力。候选项使用统一结构描述命令、前置参数和来源，避免各服务继续复制可执行文件检查逻辑。

Python 优先级：

1. 调用方测试覆盖项；
2. 项目元数据中的 `runtime.pythonExecutable`；
3. `PYTEST_DSL_PYTHON` 或 `PYTHON`；
4. 项目 `.venv` / `venv`；
5. PATH 中的平台候选，POSIX 优先 `python3`，Windows检查 `python.exe` 和 `py.exe -3`。

Allure 优先级：

1. 调用方测试覆盖项；
2. 项目元数据中的 `runtime.allureExecutable`；
3. `PYTEST_DSL_ALLURE`；
4. 项目 `node_modules/.bin/allure`；
5. Studio 开发环境 `node_modules/.bin/allure`；
6. PATH 中的 `allure`。

Allure 候选必须通过 `--version` 且主版本不低于 3。找不到 Python 时不再调用 `spawn("python")`，而是在创建子进程前返回包含已检查位置和配置入口的错误。

### 2. 项目级配置存储

`metadataStore.js` 的默认结构增加：

```json
{
  "runtime": {
    "pythonExecutable": null,
    "allureExecutable": null
  }
}
```

读取旧 metadata 时补齐默认值，保持现有 version、最近文件和布局数据不变。保存路径前做绝对路径、文件存在性和可执行性检查；“自动发现”操作通过写入 `null` 恢复默认行为。

### 3. 主进程与界面

在现有顶部配置下拉区增加紧凑的“运行环境”区域，分别展示 Python 和 Allure 的当前解析结果、来源和状态，并提供“选择”与“自动”操作。

- 文件选择由主进程的原生文件对话框完成，renderer 不直接访问文件系统。
- preload 仅暴露读取运行时状态、选择可执行文件、保存配置和恢复自动发现所需的窄 IPC。
- 打开项目或修改配置后立即刷新状态。
- Python 状态区分“可执行文件不存在”和“解释器缺少 pytest-dsl”。
- Allure 状态区分“未安装”“版本低于 3”和“可用”。

### 4. 执行与报告数据流

运行、语法检查、调试和测试套执行先解析同一个 Python 候选；当公开 CLI 不可用时，通过该解释器执行对应 `-m` 模块。构建使用同一解释器运行 `python -m pytest`。

关键字列表与定义查询也读取同一项目配置，避免编辑器补全使用一个环境、实际执行使用另一个环境。

构建启动和报告导出从项目配置解析同一个 Allure 3：

```text
项目配置/自动发现
  -> Python -> pytest -> allure-results
  -> Allure 3 watch -> 内嵌实时报告
  -> Allure 3 awesome --single-file -> 下载 HTML
```

Allure 缺失不会阻断 pytest；Python 缺失或配置无效会在启动测试前终止，并输出明确错误。

## 错误处理

- 配置路径失效时不静默回退，以免用户误以为指定环境生效；状态区标红并提示重新选择或恢复自动发现。
- 自动发现候选无效时继续尝试下一候选，全部失败后汇总已检查候选。
- Python 子进程仍可能返回依赖缺失错误，原始 stderr 保留在控制台和构建日志中。
- Allure 版本探测失败只影响报告能力，不改变 pytest 的最终状态。
- 报告导出继续从 `.pytest-dsl-gui/builds/<buildId>/allure-results` 生成单文件 HTML，不改动现有制品结构。

## 测试与验收

按 TDD 增加以下回归：

- metadata 兼容旧结构并持久化/清除两个运行时路径；
- 受限 PATH 下优先使用项目 `.venv`，运行与构建不再产生 `spawn python ENOENT`；
- 无 `python` 但有 `python3` 时能够回退；
- 显式无效 Python 不静默切换到其他解释器；
- 关键字列表和定义查询使用项目配置的 Python；
- Allure 配置路径优先于 PATH，且拒绝低于 v3 的版本；
- Allure 缺失时 pytest 构建继续完成，并返回明确的报告不可用原因；
- UI 和 IPC 覆盖选择、自动发现、状态展示及项目切换刷新。

最终执行针对性 Node 测试、完整 `npm test --prefix electron-gui`、`npm run check --prefix electron-gui`、`git diff --check`，并重新打包当前平台。在清理后的桌面应用 PATH 中，用带项目 `.venv` 的临时项目验证真实运行路径；Allure 使用可控的 v3 测试可执行文件验证实时报告和单文件导出解析路径。

## 非目标

- 不内置或自动下载 Python、pytest-dsl、项目依赖、Java 或 Allure CLI。
- 不修改 DSL、pytest 或 Allure 结果格式。
- 不引入全局运行时配置；本次只提供项目级配置，避免不同项目依赖相互污染。
- 不自动执行 shell 初始化脚本来获取 PATH，避免启动延迟、跨平台差异和用户 shell 副作用。
