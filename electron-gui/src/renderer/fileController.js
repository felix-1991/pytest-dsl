import { errorMessage, fileNameFromPath } from "./utils.js";
import {
  isPythonRuntimeAvailable,
  pythonRuntimeUnavailableMessage,
} from "./state.js";

export function createFileController({
  state,
  el,
  api,
  appendLog,
  showActionFeedback,
  currentCommand,
  previewCommand,
  resetCommandPreview,
  renderFileTree,
  renderMetadata,
  renderRemoteStatus,
  syncEditorCompletionContext,
  loadEditorCompletionKeywords,
  resetEditorCompletionKeywords,
  selectedConfigErrors,
  selectedMergedConfig,
  updateBuildActionState,
  currentSelectedSuiteIds = () => [],
  closeKeywordPanel,
}) {
  async function selectFile(relativePath) {
    try {
      const result = await api.readFile(
        state.snapshot.project.rootPath,
        relativePath,
      );
      state.currentFile = result.relativePath;
      state.readonlySource = null;
      state.currentDebugLine = null;
      state.debugStartLine = null;
      state.debugSelection = null;
      state.debugPaused = false;
      state.snapshot.metadata = result.metadata || state.snapshot.metadata;
      CM6.setContent(result.content);
      CM6.setLanguage(detectLanguage(result.relativePath));
      CM6.setEnabled(true);
      syncEditorCompletionContext();
      loadEditorCompletionKeywords();
      setDirty(false);
      renderActiveFile();
      renderFileTree();
      renderMetadata(state.snapshot.metadata);
      renderRemoteStatus();
      appendLog("info", `Opened ${result.relativePath}`);
    } catch (error) {
      appendLog("error", errorMessage(error));
    }
  }

  function renderActiveFile() {
    if (!state.currentFile) {
      clearEditor("从左侧打开文件");
      return;
    }

    const file = currentFileRecord();
    const readonlySource = state.readonlySource;
    const fileName = readonlySource
      ? fileNameFromPath(readonlySource.path)
      : state.currentFile.split("/").pop();
    el.activeTab.textContent = fileName;
    el.fileTitle.textContent = fileName;
    el.filePath.textContent = readonlySource ? readonlySource.path : state.currentFile;
    el.editorMeta.textContent = `${CM6.lineCount()} 行 · ${languageLabel(file)} · UTF-8 · Spaces: 4${readonlySource ? " · Readonly source" : ""}`;
    el.problemCount.textContent = String(selectedConfigErrors().length);
    el.variableCount.textContent = String(
      Object.keys(selectedMergedConfig()).length,
    );
    updateFileActionState();
    previewCommand(currentCommand(), { force: true });
  }

  function getEditableFiles(snapshot = state.snapshot) {
    if (!snapshot) {
      return [];
    }
    return snapshot.editableFiles || snapshot.dslFiles || [];
  }

  function currentFileRecord() {
    return getEditableFiles().find((file) => file.relativePath === state.currentFile) || null;
  }

  function detectLanguage(relativePath) {
    const name = String(relativePath || "").toLowerCase();
    if (name.endsWith(".dsl")) return "dsl";
    if (name.endsWith(".resource")) return "resource";
    if (name.endsWith(".yaml") || name.endsWith(".yml")) return "yaml";
    if (name.endsWith(".py")) return "python";
    if (name.endsWith(".md") || name.endsWith(".markdown")) return "markdown";
    return "plain";
  }

  function languageLabel(file) {
    const language = file && file.language
      ? file.language
      : detectLanguage(state.currentFile);
    const labels = {
      dsl: "DSL",
      resource: "Resource",
      yaml: "YAML",
      python: "Python",
      markdown: "Markdown",
      plain: "Text",
    };
    return labels[language] || "Text";
  }

  function isDslFile(relativePath) {
    return detectLanguage(relativePath) === "dsl";
  }

  function isExecutableFile(relativePath) {
    const language = detectLanguage(relativePath);
    return language === "dsl" || language === "resource";
  }

  function isRunnableWholeFile(relativePath) {
    return detectLanguage(relativePath) === "dsl";
  }

  function updateFileActionState() {
    const hasFile = Boolean(state.snapshot && state.currentFile);
    const readonlySource = Boolean(state.readonlySource);
    const executable = hasFile && !readonlySource && isExecutableFile(state.currentFile);
    const showKeywordTools = hasFile && isExecutableFile(state.currentFile);
    const runnableWholeFile = hasFile && !readonlySource && isRunnableWholeFile(state.currentFile);
    const selection = executable ? CM6.getSelection() : null;
    const hasSelection = Boolean(selection);
    const hasDebugStart = executable && Boolean(state.debugStartLine);
    const isRunning = Boolean(state.currentTaskId);
    const isDebugRunning = isRunning && state.currentTaskMode === "debug";
    const pythonReady = isPythonRuntimeAvailable(state);
    const hasDebugSuites = currentSelectedSuiteIds("debug").length > 0;
    const canRun = executable && (runnableWholeFile || hasSelection);
    const canDebug = executable && (runnableWholeFile || hasSelection || hasDebugStart);
    const pythonHint = pythonRuntimeUnavailableMessage(state);

    el.executionActionGroup.hidden = !executable;
    el.debugSessionGroup.hidden = !isDebugRunning;
    el.keywordBtn.hidden = !showKeywordTools;
    el.commandBtn.hidden = !showKeywordTools;
    el.commandBar.hidden = !showKeywordTools;
    el.saveBtn.disabled = !hasFile || readonlySource;
    el.keywordBtn.disabled = !hasFile || readonlySource || !isExecutableFile(state.currentFile);
    el.commandBtn.disabled = !showKeywordTools;
    el.regenerateCommandBtn.disabled = !showKeywordTools;
    el.copyCommandBtn.disabled = !showKeywordTools || !state.commandBar.command;
    el.syntaxBtn.disabled = !executable || isRunning || !pythonReady;
    el.runBtn.disabled = !canRun || isRunning || !pythonReady;
    el.debugStepsBtn.disabled = !canDebug || isRunning || !pythonReady;
    el.nextStepBtn.disabled = !isDebugRunning || !state.debugPaused;
    el.continueDebugBtn.disabled = !isDebugRunning || !state.debugPaused;
    el.stopBtn.disabled = !isRunning;
    el.runAllBtn.disabled = !state.snapshot || isRunning || !pythonReady || !hasDebugSuites;
    el.runAllBtn.title = !pythonReady && state.snapshot
      ? pythonHint
      : hasDebugSuites ? "运行所选测试套" : "请选择测试套";
    [el.syntaxBtn, el.runBtn, el.debugStepsBtn].forEach((button) => {
      if (!button) return;
      if (!pythonReady && state.snapshot) {
        button.title = pythonHint;
      } else {
        button.removeAttribute("title");
      }
    });
    if ((el.keywordBtn.hidden || el.keywordBtn.disabled) && state.keywordPanelOpen) {
      closeKeywordPanel();
    }
    updateExecutionActionLabels(selection);
    previewCommand(currentCommand());
    updateBuildActionState();
  }

  function updateExecutionActionLabels(selection = null) {
    if (!state.currentFile) {
      el.syntaxBtn.textContent = "语法检查";
      el.runBtn.textContent = "运行文件";
      el.debugStepsBtn.textContent = "单步调试";
      return;
    }

    const selectionLabel = selection
      ? `${selection.startLine}-${selection.endLine}`
      : null;
    el.syntaxBtn.textContent = selectionLabel
      ? `语法检查 ${selectionLabel}`
      : "语法检查";

    if (selectionLabel) {
      el.runBtn.textContent = `运行选中 ${selectionLabel}`;
    } else if (isRunnableWholeFile(state.currentFile)) {
      el.runBtn.textContent = "运行文件";
    } else {
      el.runBtn.textContent = "运行选中";
    }

    if (state.debugStartLine) {
      el.debugStepsBtn.textContent = `从第 ${state.debugStartLine} 行调试`;
    } else if (selectionLabel) {
      el.debugStepsBtn.textContent = `调试选中 ${selectionLabel}`;
    } else {
      el.debugStepsBtn.textContent = "单步调试";
    }
  }

  async function saveCurrentFile(options = {}) {
    if (!state.snapshot || !state.currentFile) {
      appendLog("warn", "No file selected");
      if (options.source === "shortcut") {
        showActionFeedback("没有可保存的文件", "warn");
      }
      return;
    }
    if (state.readonlySource) {
      appendLog("warn", "只读源码不能保存");
      if (options.source === "shortcut") {
        showActionFeedback("只读源码不能保存", "warn");
      }
      return;
    }
    if (options.source === "shortcut" && !state.dirty) {
      showActionFeedback("当前文件已是最新", "info");
      return;
    }

    try {
      const content = CM6.getContent();
      const result = await api.saveFile(
        state.snapshot.project.rootPath,
        state.currentFile,
        content,
      );
      state.snapshot.metadata = result.metadata || state.snapshot.metadata;
      if (detectLanguage(state.currentFile) === "resource") {
        resetEditorCompletionKeywords();
        loadEditorCompletionKeywords();
      }
      setDirty(false);
      renderMetadata(state.snapshot.metadata);
      appendLog("pass", `Saved ${result.relativePath} (${result.bytes} bytes)`);
      showActionFeedback(`已保存 ${result.relativePath}`, "pass");
    } catch (error) {
      appendLog("error", errorMessage(error));
      showActionFeedback(`保存失败: ${errorMessage(error)}`, "error");
    }
  }

  function clearEditor(message) {
    state.currentFile = null;
    state.readonlySource = null;
    state.currentDebugLine = null;
    state.debugStartLine = null;
    state.debugSelection = null;
    state.debugPaused = false;
    CM6.setContent("");
    CM6.setEnabled(false);
    setDirty(false);
    el.activeTab.textContent = "未选择文件";
    el.fileTitle.textContent = message;
    el.filePath.textContent = "从左侧打开文件";
    el.editorMeta.textContent = "UTF-8 · Spaces: 4";
    resetCommandPreview();
    updateFileActionState();
  }

  function setDirty(isDirty) {
    state.dirty = isDirty;
    el.dirtyDot.classList.toggle("is-dirty", isDirty);
    if (state.currentFile) {
      renderActiveFile();
    }
  }

  function fileKind(file) {
    const language = file.language || detectLanguage(file.relativePath || file.path || file.name);
    const name = String(file.name || file.path || file.relativePath || "").toLowerCase();
    if (language === "yaml") return "yaml";
    if (language === "python") return "python";
    if (language === "markdown") return "markdown";
    if (language === "dsl") return "dsl";
    if (name.endsWith(".resource")) return "resource";
    return "text";
  }

  function fileIcon(file) {
    const kind = fileKind(file);
    if (kind === "yaml") return "YAML";
    if (kind === "python") return "PY";
    if (kind === "markdown") return "MD";
    if (kind === "resource") return "RES";
    if (kind === "text") return "TXT";
    return "DSL";
  }

  function folderIcon(stateName) {
    if (stateName === "open") {
      return `<svg width="17" height="17" viewBox="0 0 24 24" fill="none" focusable="false">
      <path d="M3.5 8.5V7a2 2 0 0 1 2-2h4.1l2.1 2.2h6.8a2 2 0 0 1 2 2v1.3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M4.5 10.5h16l-2.4 8.5H6.1L4.5 10.5Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
    </svg>`;
    }
    return `<svg width="17" height="17" viewBox="0 0 24 24" fill="none" focusable="false">
    <path d="M4 6.5h5.7l2.1 2.2H20v9.8H4V6.5Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
  </svg>`;
  }

  return {
    selectFile,
    renderActiveFile,
    clearEditor,
    setDirty,
    saveCurrentFile,
    updateFileActionState,
    updateExecutionActionLabels,
    getEditableFiles,
    currentFileRecord,
    detectLanguage,
    languageLabel,
    isDslFile,
    isExecutableFile,
    isRunnableWholeFile,
    fileKind,
    fileIcon,
    folderIcon,
  };
}
