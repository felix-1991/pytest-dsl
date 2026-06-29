import {
  MAX_CONSOLE_BUFFER_LINES,
  MAX_CONSOLE_RENDER_LINES,
  createCommandBar,
  createCommandPreview,
  createConsoleBuffer,
  createConsoleView,
} from "./state.js";

export function createConsoleController({
  state,
  el,
  api,
  errorMessage,
  renderCommandBar,
  renderCommandPreview,
}) {
  function consoleScopeForMode(mode) {
    return mode === "build" ? "build" : "debug";
  }

  function normalizeConsoleScope(scope) {
    return scope === "build" ? "build" : "debug";
  }

  function setConsoleScope(scope) {
    state.console.activeScope = normalizeConsoleScope(scope);
    applyConsoleViewState();
    renderCommandPreview();
    requestConsoleBufferRender();
  }

  function currentConsoleView() {
    return state.console[state.console.activeScope];
  }

  function currentConsoleBuffer() {
    return consoleBufferForScope(state.console.activeScope);
  }

  function consoleBufferForScope(scope) {
    return state.consoleBuffers[normalizeConsoleScope(scope)];
  }

  function appendProcessOutput(level, text, options = {}) {
    const scope = normalizeConsoleScope(options.scope || consoleScopeForMode(state.currentTaskMode));
    const buffer = consoleBufferForScope(scope);
    buffer.commandOutputChunks.push(String(text || ""));
    const timestamp = new Date().toTimeString().slice(0, 8);
    const entries = String(text || "")
      .replace(/\r\n/g, "\n")
      .split("\n")
      .filter((line) => line.length > 0)
      .map((line) => ({
        timestamp,
        level,
        message: line,
      }));
    appendConsoleEntries(scope, entries);
  }

  async function resetConsoleForExecution(scope, options = {}) {
    const normalizedScope = normalizeConsoleScope(scope);
    clearConsole(normalizedScope);
    const buffer = consoleBufferForScope(normalizedScope);
    buffer.exportLogTarget = null;

    const projectRoot = options.projectRoot || state.snapshot?.project?.rootPath;
    if (!projectRoot || typeof api.resetConsoleLog !== "function") {
      return null;
    }
    try {
      const result = await api.resetConsoleLog({
        projectRoot,
        scope: normalizedScope,
        taskId: options.taskId,
      });
      buffer.exportLogTarget = {
        projectRoot,
        scope: normalizedScope,
        path: result?.path || null,
        active: true,
      };
      return result;
    } catch (error) {
      appendLog("warn", `控制台日志文件初始化失败: ${errorMessage(error)}`, { scope: normalizedScope });
      return null;
    }
  }

  function appendLog(level, message, options = {}) {
    const scope = normalizeConsoleScope(
      options.scope || (state.currentTaskMode ? consoleScopeForMode(state.currentTaskMode) : state.console.activeScope),
    );
    appendConsoleEntries(scope, [{
      timestamp: new Date().toTimeString().slice(0, 8),
      level,
      message: String(message ?? ""),
    }]);
  }

  function finishConsoleForExecution(scope) {
    const buffer = consoleBufferForScope(scope);
    if (buffer.exportLogTarget) {
      buffer.exportLogTarget.active = false;
    }
  }

  function appendConsoleEntries(scope, entries) {
    if (!Array.isArray(entries) || entries.length === 0) {
      return;
    }
    const buffer = consoleBufferForScope(scope);
    appendConsoleExportEntries(scope, entries);
    buffer.lines.push(...entries);
    trimConsoleBuffer(buffer);
    if (scope === state.console.activeScope && shouldRenderConsoleBuffer()) {
      scheduleConsoleBufferRender();
    }
  }

  function appendConsoleExportEntries(scope, entries) {
    const buffer = consoleBufferForScope(scope);
    if (!buffer.exportLogTarget?.active || typeof api.appendConsoleLog !== "function") {
      return;
    }
    const text = formatConsoleLogEntries(entries);
    if (!text) {
      return;
    }
    api.appendConsoleLog({
      projectRoot: buffer.exportLogTarget.projectRoot,
      scope: buffer.exportLogTarget.scope,
      text,
    });
  }

  function trimConsoleBuffer(buffer) {
    const overflow = buffer.lines.length - MAX_CONSOLE_BUFFER_LINES;
    if (overflow <= 0) {
      return;
    }
    buffer.lines.splice(0, overflow);
    buffer.droppedLineCount += overflow;
  }

  function visibleConsoleEntries(buffer) {
    const lines = buffer.lines.slice(-MAX_CONSOLE_RENDER_LINES);
    return {
      lines,
      omittedCount: buffer.droppedLineCount + Math.max(0, buffer.lines.length - lines.length),
    };
  }

  function createConsoleRow(entry) {
    const row = document.createElement("div");
    row.className = "log-line";
    const time = document.createElement("span");
    time.className = "log-time";
    time.textContent = entry.timestamp;
    const level = document.createElement("span");
    level.className = `log-level ${entry.level}`;
    level.textContent = entry.level.toUpperCase();
    const message = document.createElement("span");
    message.className = "log-message";
    message.textContent = entry.message;
    row.append(time, level, message);
    return row;
  }

  function createConsoleOmittedRow(omittedCount) {
    const row = document.createElement("div");
    row.className = "log-line log-line-omitted";
    const message = document.createElement("span");
    message.className = "log-message";
    message.textContent = `已省略 ${omittedCount} 条较早日志`;
    row.append(document.createElement("span"), document.createElement("span"), message);
    return row;
  }

  function requestConsoleBufferRender() {
    if (!el.consoleBody) {
      return;
    }
    if (!shouldRenderConsoleBuffer()) {
      cancelConsoleBufferRender();
      renderConsoleBuffer();
      return;
    }
    scheduleConsoleBufferRender();
  }

  function scheduleConsoleBufferRender() {
    if (!el.consoleBody || state.consoleRenderScheduled) {
      return;
    }
    state.consoleRenderScheduled = true;
    const flush = () => {
      state.consoleRenderRaf = null;
      state.consoleRenderTimer = null;
      state.consoleRenderScheduled = false;
      renderConsoleBuffer();
    };
    if (typeof window.requestAnimationFrame === "function") {
      state.consoleRenderRaf = window.requestAnimationFrame(flush);
    } else {
      state.consoleRenderTimer = window.setTimeout(flush, 0);
    }
  }

  function cancelConsoleBufferRender() {
    if (state.consoleRenderRaf !== null && typeof window.cancelAnimationFrame === "function") {
      window.cancelAnimationFrame(state.consoleRenderRaf);
    }
    if (state.consoleRenderTimer !== null) {
      window.clearTimeout(state.consoleRenderTimer);
    }
    state.consoleRenderRaf = null;
    state.consoleRenderTimer = null;
    state.consoleRenderScheduled = false;
  }

  function renderConsoleBuffer() {
    if (!el.consoleBody) {
      return;
    }
    if (!shouldRenderConsoleBuffer()) {
      el.consoleBody.textContent = "";
      return;
    }
    const visible = visibleConsoleEntries(currentConsoleBuffer());
    const fragment = document.createDocumentFragment();
    if (visible.omittedCount > 0) {
      fragment.appendChild(createConsoleOmittedRow(visible.omittedCount));
    }
    visible.lines.forEach((entry) => {
      fragment.appendChild(createConsoleRow(entry));
    });
    el.consoleBody.replaceChildren(fragment);
    el.consoleBody.scrollTop = el.consoleBody.scrollHeight;
  }

  function shouldRenderConsoleBuffer() {
    const consoleView = currentConsoleView();
    return Boolean(consoleView.open || consoleView.expanded);
  }

  function clearConsole(scope = state.console.activeScope) {
    const buffer = consoleBufferForScope(scope);
    buffer.lines = [];
    buffer.commandOutputChunks = [];
    buffer.droppedLineCount = 0;
    if (normalizeConsoleScope(scope) === state.console.activeScope) {
      requestConsoleBufferRender();
    }
  }

  function formatConsoleLogEntries(entries) {
    return entries.map((entry) => {
      const level = String(entry.level || "info").toUpperCase();
      return `[${entry.timestamp || "--:--:--"}] ${level} ${entry.message || ""}`;
    }).join("\n") + "\n";
  }

  async function exportConsoleLog() {
    const scope = state.console.activeScope;
    const buffer = currentConsoleBuffer();
    if (!buffer.exportLogTarget) {
      appendLog("warn", "没有控制台日志可导出");
      return null;
    }
    if (typeof api.exportConsoleLog !== "function") {
      appendLog("warn", "当前环境不支持导出控制台日志");
      return null;
    }
    try {
      const result = await api.exportConsoleLog({
        projectRoot: buffer.exportLogTarget.projectRoot,
        scope: buffer.exportLogTarget.scope,
      });
      if (result?.canceled) {
        appendLog("info", "已取消导出控制台日志");
        return null;
      }
      appendLog("pass", `控制台日志已导出: ${result.path}`);
      return result;
    } catch (error) {
      appendLog("error", `导出控制台日志失败: ${errorMessage(error)}`);
      return null;
    }
  }

  async function copyConsoleOutput() {
    const text = currentConsoleBuffer().commandOutputChunks.join("");
    if (!text) {
      appendLog("warn", "没有命令行输出可复制");
      return "";
    }
    if (typeof api.copyText !== "function") {
      appendLog("warn", "当前环境不支持复制命令行输出");
      return text;
    }
    try {
      await api.copyText(text);
      appendLog("pass", "命令行输出已复制");
    } catch (error) {
      appendLog("warn", `复制命令行输出失败: ${errorMessage(error)}`);
    }
    return text;
  }

  function toggleConsoleWrap() {
    const consoleView = currentConsoleView();
    consoleView.wrap = !consoleView.wrap;
    applyConsoleViewState();
  }

  function toggleConsoleOpen() {
    const consoleView = currentConsoleView();
    const wasRenderable = shouldRenderConsoleBuffer();
    consoleView.open = !consoleView.open;
    if (!consoleView.open) {
      consoleView.expanded = false;
    }
    applyConsoleViewState();
    if (wasRenderable || shouldRenderConsoleBuffer()) {
      requestConsoleBufferRender();
    }
  }

  function openConsolePanel(scope = state.console.activeScope) {
    const consoleView = state.console[normalizeConsoleScope(scope)];
    consoleView.open = true;
    applyConsoleViewState();
    if (normalizeConsoleScope(scope) === state.console.activeScope) {
      requestConsoleBufferRender();
    }
  }

  function toggleConsoleExpanded() {
    const consoleView = currentConsoleView();
    const wasRenderable = shouldRenderConsoleBuffer();
    if (!consoleView.open) {
      consoleView.open = true;
      consoleView.expanded = false;
    } else {
      consoleView.expanded = !consoleView.expanded;
    }
    applyConsoleViewState();
    if (!wasRenderable && shouldRenderConsoleBuffer()) {
      requestConsoleBufferRender();
    }
  }

  function applyConsoleViewState() {
    const consoleView = currentConsoleView();
    if (consoleView.expanded) {
      consoleView.open = true;
    }
    if (el.bottomConsole) {
      el.bottomConsole.classList.toggle("is-unwrapped", !consoleView.wrap);
      el.bottomConsole.classList.toggle("is-collapsed", !consoleView.open);
    }
    if (el.mainStage) {
      el.mainStage.classList.toggle("is-console-open", consoleView.open);
      el.mainStage.classList.toggle("is-console-expanded", consoleView.expanded);
    }
    if (el.consoleToggleBtn) {
      el.consoleToggleBtn.textContent = consoleView.open ? "收起控制台" : "打开控制台";
      el.consoleToggleBtn.title = consoleView.open ? "收起当前控制台" : "打开当前控制台";
      el.consoleToggleBtn.setAttribute("aria-expanded", String(consoleView.open));
    }
    if (el.consoleStatusToggleBtn) {
      el.consoleStatusToggleBtn.textContent = consoleView.open ? "收起控制台" : "打开控制台";
      el.consoleStatusToggleBtn.title = consoleView.open ? "收起当前控制台" : "打开当前控制台";
      el.consoleStatusToggleBtn.setAttribute("aria-expanded", String(consoleView.open));
    }
    if (el.buildToggleConsoleBtn) {
      el.buildToggleConsoleBtn.textContent = consoleView.open ? "收起控制台" : "打开控制台";
      el.buildToggleConsoleBtn.title = consoleView.open ? "收起构建控制台" : "打开构建控制台";
      el.buildToggleConsoleBtn.setAttribute("aria-pressed", String(consoleView.open));
    }
    if (el.wrapConsoleBtn) {
      el.wrapConsoleBtn.textContent = consoleView.wrap ? "横滚" : "换行";
      el.wrapConsoleBtn.title = consoleView.wrap
        ? "长输出改为横向滚动"
        : "长输出改为自动换行";
      el.wrapConsoleBtn.setAttribute("aria-pressed", String(!consoleView.wrap));
    }
    if (el.expandConsoleBtn) {
      el.expandConsoleBtn.textContent = consoleView.expanded ? "还原" : "最大化";
      el.expandConsoleBtn.title = consoleView.expanded
        ? "还原控制台高度"
        : "最大化控制台";
      el.expandConsoleBtn.setAttribute("aria-pressed", String(consoleView.expanded));
    }
  }

  function resetAllConsoleState() {
    state.consoleBuffers = {
      debug: createConsoleBuffer(),
      build: createConsoleBuffer(),
    };
    state.console = {
      activeScope: "debug",
      debug: createConsoleView(),
      build: createConsoleView(),
    };
    state.commandPreviews = {
      debug: createCommandPreview(),
      build: createCommandPreview(),
    };
    state.commandBar = createCommandBar();
    cancelConsoleBufferRender();
    requestConsoleBufferRender();
    renderCommandBar();
    renderCommandPreview();
    applyConsoleViewState();
  }

  return {
    appendLog,
    appendProcessOutput,
    clearConsole,
    consoleScopeForMode,
    copyConsoleOutput,
    currentConsoleBuffer,
    exportConsoleLog,
    finishConsoleForExecution,
    formatConsoleLogEntries,
    normalizeConsoleScope,
    openConsolePanel,
    requestConsoleBufferRender,
    resetAllConsoleState,
    resetConsoleForExecution,
    setConsoleScope,
    shouldRenderConsoleBuffer,
    toggleConsoleExpanded,
    toggleConsoleOpen,
    toggleConsoleWrap,
    applyConsoleViewState,
  };
}
