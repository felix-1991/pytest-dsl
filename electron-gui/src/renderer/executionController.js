import { errorMessage } from "./utils.js";
import {
  allureRuntimeUnavailableMessage,
  isAllureRuntimeAvailable,
  isPythonRuntimeAvailable,
  pythonRuntimeUnavailableMessage,
} from "./state.js";

export function createExecutionController({
  state,
  el,
  api,
  appendLog,
  showActionFeedback,
  currentCommand,
  consoleScopeForMode,
  appendProcessOutput,
  resetConsoleForExecution,
  finishConsoleForExecution,
  setConsoleScope,
  openConsolePanel,
  setExecutionCommand,
  releaseExecutionCommand,
  updateCommandPreview,
  previewCommand,
  commandContextForMode,
  currentSelectedSuiteIds,
  computeSelectedFiles,
  suiteCommandLabel,
  buildCommandLabel,
  showRuntimeRequirementDialog,
  setBuildReportUrl,
  resetBuildReport,
  buildStatusLabel,
  recordBuildHistory,
  updateBuildSummary,
  updateBuildActionState,
  updateFileActionState,
  isExecutableFile,
  isRunnableWholeFile,
  selectedConfigSources,
}) {
  async function runExecutionTask(mode, options = {}) {
    if (!state.currentFile) {
      appendLog("warn", "No file selected");
      return;
    }
    if (!isExecutableFile(state.currentFile)) {
      appendLog("warn", "当前文件不支持执行");
      return;
    }
    if (state.currentTaskId) {
      appendLog("warn", "已有任务正在运行，请先停止或等待完成");
      return;
    }
    if (!ensurePythonRuntimeReady("debug")) {
      return;
    }

    const taskId = createTaskId(mode);
    const debugScope = mode === "debug" ? normalizeDebugScope(options.debugScope) : null;
    const selection = !debugScope
      ? CM6.getSelection()
      : null;
    if (
      mode === "run" &&
      !selection &&
      !isRunnableWholeFile(state.currentFile)
    ) {
      appendLog("warn", "Resource 文件请先选中要运行的片段");
      return;
    }
    if (
      mode === "debug" &&
      !selection &&
      !debugScope &&
      !isRunnableWholeFile(state.currentFile)
    ) {
      appendLog("warn", "Resource 文件请先选中片段或设置调试起点");
      return;
    }
    const yamlVars = selectedConfigSources().map((source) => source.relativePath);
    const sourceLabel = executionSourceLabel(state.currentFile, selection, debugScope);
    const command = executionCommandLabel(mode, sourceLabel, yamlVars);

    state.debugSelection = selection;
    state.currentDebugLine = null;
    CM6.setDebugState({ debugStartLine: state.debugStartLine, currentDebugLine: null, debugSelection: selection });
    await resetConsoleForExecution("debug", {
      projectRoot: state.snapshot.project.rootPath,
      taskId,
    });
    setConsoleScope("debug");
    openConsolePanel("debug");
    setRunningState(true, taskId, mode);
    setExecutionCommand(command, { mode, taskId });
    appendLog("info", `${executionModeLabel(mode)} started: ${sourceLabel}`, { scope: "debug" });
    if (mode === "syntax") {
      showActionFeedback("语法检查已提交", "info");
    }

    try {
      await api.startExecution({
        taskId,
        mode,
        projectRoot: state.snapshot.project.rootPath,
        relativePath: state.currentFile,
        content: CM6.getContent(),
        selection,
        debugScope,
        yamlVars,
      });
    } catch (error) {
      appendLog("error", errorMessage(error), { scope: "debug" });
      if (showRuntimeRequirementDialog(error)) {
        showActionFeedback("运行环境不可用，请按弹窗安装后重试", "error");
      } else if (mode === "syntax") {
        showActionFeedback("语法检查失败", "error");
      }
      if (state.currentTaskId === taskId) {
        releaseExecutionCommand(taskId);
        setRunningState(false);
      }
      finishConsoleForExecution("debug");
    }
  }

  function currentDebugRunOptions() {
    if (!state.debugStartLine) {
      return {};
    }
    return {
      debugScope: {
        kind: "fromLine",
        startLine: state.debugStartLine,
      },
    };
  }

  function debugFromLine(lineNumber) {
    const startLine = Math.trunc(Number(lineNumber));
    if (!Number.isFinite(startLine) || startLine < 1) {
      return;
    }
    if (!isExecutableFile(state.currentFile)) {
      return;
    }
    state.debugStartLine = state.debugStartLine === startLine ? null : startLine;
    state.debugSelection = null;
    state.currentDebugLine = null;
    CM6.setDebugState({ debugStartLine: state.debugStartLine, currentDebugLine: null, debugSelection: null });
    updateFileActionState();
    previewCommand(currentCommand(), { force: true });
  }

  function normalizeDebugScope(debugScope) {
    if (!debugScope || debugScope.kind !== "fromLine") {
      return null;
    }
    const startLine = Math.trunc(Number(debugScope.startLine));
    if (!Number.isFinite(startLine) || startLine < 1) {
      return null;
    }
    return {
      kind: "fromLine",
      startLine,
    };
  }

  function executionSourceLabel(relativePath, selection, debugScope) {
    if (debugScope && debugScope.kind === "fromLine") {
      return `${relativePath}:${debugScope.startLine}-end`;
    }
    if (selection) {
      return `${relativePath}:${selection.startLine}-${selection.endLine}`;
    }
    return relativePath;
  }

  async function runSuiteExecution() {
    if (!state.snapshot) {
      appendLog("warn", "No project loaded");
      return;
    }
    if (state.currentTaskId) {
      appendLog("warn", "已有任务正在运行，请先停止或等待完成");
      return;
    }
    if (!ensurePythonRuntimeReady("debug")) {
      return;
    }

    const selectedSuiteIds = currentSelectedSuiteIds("debug");
    if (selectedSuiteIds.length === 0) {
      appendLog("warn", "没有可运行的测试套");
      return;
    }
    const yamlVars = selectedConfigSources().map((source) => source.relativePath);
    const taskId = createTaskId("suite");
    const command = suiteCommandLabel(selectedSuiteIds, yamlVars);
    await resetConsoleForExecution("debug", {
      projectRoot: state.snapshot.project.rootPath,
      taskId,
    });
    setConsoleScope("debug");
    openConsolePanel("debug");
    setRunningState(true, taskId, "suite");
    setExecutionCommand(command, { mode: "suite", taskId });
    appendLog("info", `测试套运行 started: ${selectedSuiteIds.join(", ")}`, { scope: "debug" });

    try {
      const selectedFiles = computeSelectedFiles("debug");
      await api.startExecution({
        taskId,
        mode: "suite",
        projectRoot: state.snapshot.project.rootPath,
        selectedSuiteIds,
        selectedFiles,
        yamlVars,
      });
    } catch (error) {
      appendLog("error", errorMessage(error), { scope: "debug" });
      if (showRuntimeRequirementDialog(error)) {
        showActionFeedback("运行环境不可用，请按弹窗安装后重试", "error");
      }
      if (state.currentTaskId === taskId) {
        releaseExecutionCommand(taskId);
        setRunningState(false);
      }
      finishConsoleForExecution("debug");
    }
  }

  async function runBuildExecution() {
    if (!state.snapshot) {
      appendLog("warn", "No project loaded");
      return;
    }
    if (state.currentTaskId) {
      appendLog("warn", "已有任务正在运行，请先停止或等待完成");
      return;
    }

    const selectedSuiteIds = currentSelectedSuiteIds("build");
    if (selectedSuiteIds.length === 0) {
      appendLog("warn", "没有可运行的测试套");
      return;
    }
    if (!ensurePythonRuntimeReady("build")) {
      return;
    }
    if (!isAllureRuntimeAvailable(state)) {
      const message = allureRuntimeUnavailableMessage(state);
      appendLog("warn", message, { scope: "build" });
      showActionFeedback(message, "warn");
    }

    const selectedFiles = computeSelectedFiles("build");
    const yamlVars = selectedConfigSources().map((source) => source.relativePath);
    const buildId = createTaskId("build");
    const command = buildCommandLabel(buildId);

    state.currentBuildId = buildId;
    state.currentBuildStatus = "running";
    state.currentBuildReportUrl = "";
    state.currentBuildReportText = "";
    state.currentBuildResultsDir = "";
    resetBuildReport();
    await resetConsoleForExecution("build", {
      projectRoot: state.snapshot.project.rootPath,
      taskId: buildId,
    });
    setConsoleScope("build");
    openConsolePanel("build");
    setRunningState(true, buildId, "build");
    setExecutionCommand(command, { mode: "build", taskId: buildId });
    updateBuildSummary({
      status: "构建启动中",
      command,
    });
    appendLog("info", `构建运行 started: ${selectedSuiteIds.join(", ")}`, { scope: "build" });

    try {
      await api.startBuild({
        buildId,
        projectRoot: state.snapshot.project.rootPath,
        selectedSuiteIds,
        selectedFiles,
        yamlVars,
      });
    } catch (error) {
      appendLog("error", errorMessage(error), { scope: "build" });
      if (showRuntimeRequirementDialog(error)) {
        showActionFeedback("构建环境不可用，请按弹窗安装后重试", "error");
      }
      if (state.currentTaskId === buildId) {
        releaseExecutionCommand(buildId);
        setRunningState(false);
        state.currentBuildStatus = "";
        updateBuildSummary({ status: "构建启动失败" });
      }
      finishConsoleForExecution("build");
    }
  }

  async function stopCurrentTask() {
    if (!state.currentTaskId) {
      appendLog("warn", "没有正在运行的任务");
      return;
    }

    const taskId = state.currentTaskId;
    const scope = consoleScopeForMode(state.currentTaskMode);
    appendLog("warn", `Stop requested: ${taskId}`, { scope });
    try {
      const result = state.currentTaskMode === "build"
        ? await api.stopBuild(taskId)
        : await api.stopExecution(taskId);
      if (!result || !result.stopped) {
        appendLog("warn", "任务已经结束或不存在", { scope });
      }
    } catch (error) {
      appendLog("error", errorMessage(error), { scope });
    }
  }

  async function sendDebugCommand(command) {
    if (!state.currentTaskId || state.currentTaskMode !== "debug") {
      appendLog("warn", "当前没有正在暂停的调试任务");
      return;
    }

    try {
      state.debugPaused = false;
      updateFileActionState();
      const result = await api.sendExecutionCommand(state.currentTaskId, command);
      if (!result || !result.sent) {
        appendLog("warn", `调试指令未发送: ${command}`, { scope: "debug" });
        state.debugPaused = Boolean(state.currentTaskId);
        updateFileActionState();
        return;
      }
      appendLog("info", `Debug command: ${command}`, { scope: "debug" });
    } catch (error) {
      appendLog("error", errorMessage(error), { scope: "debug" });
      state.debugPaused = Boolean(state.currentTaskId);
      updateFileActionState();
    }
  }

  function handleExecutionEvent(event) {
    if (!event || event.taskId !== state.currentTaskId) {
      return;
    }

    if (event.type === "started") {
      updateCommandPreview(event.command || currentCommand(), {
        context: commandContextForMode(event.mode),
        persistent: true,
        taskId: event.taskId,
        scope: "debug",
      });
      return;
    }

    if (event.type === "stdout" || event.type === "stderr") {
      appendProcessOutput(event.type === "stderr" ? "error" : "info", event.text, { scope: "debug" });
      return;
    }

    if (event.type === "debug-step") {
      handleDebugStepEvent(event);
      return;
    }

    if (event.type === "completed") {
      const level = event.status === "passed"
        ? "pass"
        : event.status === "stopped"
          ? "warn"
          : "error";
      appendLog(
        level,
        `${executionModeLabel(event.mode)} ${event.status} (${event.durationMs}ms)`,
        { scope: "debug" },
      );
      if (event.mode === "syntax") {
        if (event.status === "passed") {
          showActionFeedback("语法检查通过", "pass");
        } else {
          showActionFeedback("语法检查失败", "error");
        }
      }
      releaseExecutionCommand(event.taskId);
      setRunningState(false);
      finishConsoleForExecution("debug");
    }
  }

  function handleBuildEvent(event) {
    if (!event || event.buildId !== state.currentBuildId) {
      return;
    }

    if (event.type === "build-started") {
      state.currentBuildStatus = "running";
      state.currentBuildResultsDir = event.allureResultsDir || "";
      updateCommandPreview(event.command || buildCommandLabel(event.buildId), {
        context: "build",
        persistent: true,
        taskId: event.buildId,
        scope: "build",
      });
      updateBuildSummary({
        status: "构建运行中",
        command: event.command,
        resultsDir: event.allureResultsDir,
      });
      return;
    }

    if (event.type === "report-started") {
      updateBuildSummary({ status: "Allure watch 启动中" });
      return;
    }

    if (event.type === "report-ready") {
      state.currentBuildReportUrl = event.url || "";
      setBuildReportUrl(state.currentBuildReportUrl);
      appendLog("pass", `Allure report ready: ${state.currentBuildReportUrl}`, { scope: "build" });
      return;
    }

    if (event.type === "report-unavailable") {
      state.currentBuildReportText = event.reason === "allure3-unavailable"
        ? allureRuntimeUnavailableMessage(state)
        : `Allure 实时报告不可用: ${event.reason || "unknown"}`;
      updateBuildSummary({ reportText: state.currentBuildReportText });
      appendLog("warn", state.currentBuildReportText, { scope: "build" });
      return;
    }

    if (event.type === "stdout" || event.type === "stderr") {
      appendProcessOutput(event.type === "stderr" ? "error" : "info", event.text, { scope: "build" });
      return;
    }

    if (event.type === "build-completed") {
      const level = event.status === "passed"
        ? "pass"
        : event.status === "stopped"
          ? "warn"
          : "error";
      state.currentBuildStatus = event.status || "completed";
      appendLog(level, `${buildStatusLabel(event.status)} (${event.durationMs}ms)`, { scope: "build" });
      if (event.reportUrl && !state.currentBuildReportUrl) {
        setBuildReportUrl(event.reportUrl);
      }
      releaseExecutionCommand(event.buildId);
      setRunningState(false);
      updateBuildSummary({
        status: buildStatusLabel(event.status),
        command: buildCommandLabel(event.buildId),
        resultsDir: event.allureResultsDir,
      });
      recordBuildHistory(event);
      finishConsoleForExecution("build");
    }
  }

  function handleDebugStepEvent(event) {
    if (event.phase === "start") {
      state.currentDebugLine = event.line;
      state.debugPaused = true;
      CM6.setDebugState({ debugStartLine: state.debugStartLine, currentDebugLine: state.currentDebugLine, debugSelection: state.debugSelection });
      CM6.scrollToLine(event.line);
      updateFileActionState();
      appendLog(
        "info",
        `Step line ${event.line || "?"}: ${event.description || event.nodeType || "DSL step"}`,
        { scope: "debug" },
      );
      return;
    }

    if (event.phase === "finish") {
      const level = event.status === "failed" ? "error" : "pass";
      appendLog(
        level,
        `Step ${event.status || "done"} line ${event.line || "?"}${event.error ? `: ${event.error}` : ""}`,
        { scope: "debug" },
      );

      // Clear the current-line highlight immediately so the yellow
      // decoration does not linger on the finished line until the
      // next step's "start" event arrives.
      state.currentDebugLine = null;
      state.debugPaused = false;
      CM6.setDebugState({
        debugStartLine: state.debugStartLine,
        currentDebugLine: null,
        debugSelection: state.debugSelection,
      });
      updateFileActionState();
    }
  }

  function setRunningState(isRunning, taskId = null, mode = null) {
    state.currentTaskId = isRunning ? taskId : null;
    state.currentTaskMode = isRunning ? mode : null;
    if (!isRunning) {
      state.currentDebugLine = null;
      state.debugPaused = false;
      state.debugSelection = null;
      CM6.setDebugState({ debugStartLine: state.debugStartLine, currentDebugLine: null, debugSelection: null });
    }
    updateFileActionState();
    updateBuildActionState();
  }

  function createTaskId(mode) {
    return `gui-${mode}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }

  function ensurePythonRuntimeReady(scope) {
    if (isPythonRuntimeAvailable(state)) {
      return true;
    }
    const message = pythonRuntimeUnavailableMessage(state);
    appendLog("warn", message, { scope });
    showActionFeedback(message, "error");
    return false;
  }

  function executionCommandLabel(mode, sourceLabel, yamlVars) {
    if (mode === "syntax") {
      return `syntax ${sourceLabel}`;
    }
    const yaml = yamlVars.length > 0
      ? ` ${yamlVars.map((item) => `--yaml-vars ${item}`).join(" ")}`
      : "";
    return `${mode === "debug" ? "debug" : "pytest-dsl"} ${sourceLabel}${yaml}`;
  }

  function executionModeLabel(mode) {
    const labels = {
      syntax: "语法检查",
      run: "运行",
      debug: "调试",
      suite: "测试套运行",
      build: "构建运行",
    };
    return labels[mode] || "执行";
  }

  return {
    runExecutionTask,
    currentDebugRunOptions,
    debugFromLine,
    normalizeDebugScope,
    executionSourceLabel,
    runSuiteExecution,
    runBuildExecution,
    stopCurrentTask,
    sendDebugCommand,
    handleExecutionEvent,
    handleBuildEvent,
    handleDebugStepEvent,
    setRunningState,
    createTaskId,
    executionCommandLabel,
    executionModeLabel,
  };
}
