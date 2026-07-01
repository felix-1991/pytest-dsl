import { errorMessage, fileNameFromPath } from "./utils.js";
import {
  isPythonRuntimeAvailable,
  pythonRuntimeUnavailableMessage,
  createOpenFileEntry,
  syncActiveFileState,
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
  debugFromLine,
  handleDefinitionRequest,
}) {
  // ---- Multi-tab helpers ----

  function ensureEditorContainer() {
    // Ensure #codeEditor exists as a container for cm-instance divs
    if (!el.codeEditor) return;
    // Remove the placeholder class if it was previously an empty target div
    if (!el.codeEditor._initialized) {
      el.codeEditor._initialized = true;
      // Clear any stale content; let CM6.create() append its child divs
    }
  }

  function activeFileEntry() {
    return state.activeFileKey
      ? (state.openFiles.find((f) => f.key === state.activeFileKey) || null)
      : null;
  }

  function findTabByPath(relativePath) {
    return state.openFiles.find(
      (f) => f.relativePath === relativePath && !f.readonlySource,
    );
  }

  function switchToTab(key) {
    if (!key) return;
    if (key === state.activeFileKey) {
      syncActiveFileState(state, "in");
      renderActiveFile();
      syncEditorCompletionContext();
      loadEditorCompletionKeywords();
      updateFileActionState();
      return;
    }
    syncActiveFileState(state, "out");
    state.activeFileKey = key;
    CM6.show(key);
    // syncActiveFileState("in") must happen AFTER show() so CM6.setDebugState delegates to the right instance
    syncActiveFileState(state, "in");
    const entry = activeFileEntry();
    if (entry) {
      state.currentFile = entry.relativePath || null;
      state.readonlySource = entry.readonlySource || null;
      state.dirty = entry.dirty;
    }
    renderActiveFile();
    syncEditorCompletionContext();
    loadEditorCompletionKeywords();
    updateFileActionState();
  }

  function closeTab(key, opts = {}) {
    const entry = state.openFiles.find((f) => f.key === key);
    if (!entry) return;

    if (entry.dirty && !opts.skipDirtyCheck) {
      showDirtyConfirm(key, {
        onSave: async () => {
          if (state.activeFileKey !== key) {
            switchToTab(key);
          }
          const saved = await saveCurrentFile({ force: true });
          if (saved) {
            closeTab(key, { skipDirtyCheck: true });
          }
        },
        onDiscard: () => {
          closeTab(key, { skipDirtyCheck: true });
        },
        onCancel: () => {},
      });
      return;
    }

    const wasActive = state.activeFileKey === key;
    const idx = state.openFiles.indexOf(entry);
    if (idx >= 0) state.openFiles.splice(idx, 1);

    CM6.destroy(key);

    if (wasActive) {
      // Find next tab to activate
      const remaining = state.openFiles;
      if (remaining.length === 0) {
        state.activeFileKey = null;
        clearEditor("从左侧打开文件");
        return;
      }
      const nextEntry = remaining[Math.min(idx, remaining.length - 1)];
      state.activeFileKey = nextEntry.key;
      CM6.show(nextEntry.key);
      syncActiveFileState(state, "in");
    }

    renderActiveFile();
    if (wasActive) {
      syncEditorCompletionContext();
      loadEditorCompletionKeywords();
      updateFileActionState();
    }
  }

  function showDirtyConfirm(key, { onSave, onDiscard, onCancel }) {
    // Use a simple confirm + custom dialog approach
    const entry = state.openFiles.find((f) => f.key === key);
    const label = entry ? entry.label : "文件";
    const result = window.confirm(
      `"${label}" 有未保存的修改。是否保存？\n\n确定 = 保存\n取消 = 不保存`,
    );
    if (result) {
      onSave();
    } else if (result === false) {
      onDiscard();
    }
    // if result is null (user closed dialog), treat as cancel
  }

  // ---- Tab bar rendering ----

  function renderTabBar() {
    if (!el.editorTabs) return;
    el.editorTabs.innerHTML = state.openFiles
      .map((entry) => renderTab(entry))
      .join("");
  }

  function renderTab(entry) {
    const isActive = entry.key === state.activeFileKey;
    const dirtyClass = entry.dirty ? "is-dirty" : "is-clean";
    return `
      <button class="editor-tab${isActive ? " is-active" : ""}" role="tab" type="button" data-tab-key="${entry.key}" title="${entry.relativePath || entry.label}">
        <span class="dot ${dirtyClass}"></span>
        <span class="tab-label">${escapeTabLabel(entry.label)}</span>
        <span class="tab-close" data-tab-close="${entry.key}" title="关闭标签">×</span>
      </button>
    `;
  }

  function escapeTabLabel(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // ---- Core file operations (multi-tab) ----

  async function selectFile(relativePath) {
    ensureEditorContainer();

    // Already open in a tab? Just switch.
    const existing = findTabByPath(relativePath);
    if (existing) {
      switchToTab(existing.key);
      return;
    }

    try {
      const result = await api.readFile(
        state.snapshot.project.rootPath,
        relativePath,
      );
      const language = detectLanguage(result.relativePath);
      const label = relativePath.split("/").pop();

      // Save current tab state before creating a new one
      syncActiveFileState(state, "out");

      // Create editor instance — pass #codeEditor as parent so CM6 creates
      // its own .cm-instance container inside it
      const key = relativePath;

      CM6.create(key, el.codeEditor, {
        onContentChange() {
          state.debugSelection = null;
          state.currentDebugLine = null;
          if (state.debugStartLine && state.debugStartLine > CM6.lineCount()) {
            state.debugStartLine = null;
          }
          setDirty(true);
          updateFileActionState();
        },
        onSelectionChange() {
          if (state.currentFile) updateFileActionState();
        },
        onGutterClick(line) {
          debugFromLine(line);
        },
        onDefinitionRequest(request) {
          handleDefinitionRequest(request);
        },
      });

      // Create and add the entry
      const entry = createOpenFileEntry({
        key,
        relativePath: result.relativePath,
        label,
        language,
        dirty: false,
      });
      state.openFiles.push(entry);

      // Keep activeFileKey + root state in sync before setContent triggers
      // CodeMirror change listeners.
      state.activeFileKey = key;
      state.currentFile = result.relativePath;
      state.readonlySource = null;
      state.currentDebugLine = null;
      state.debugStartLine = null;
      state.debugSelection = null;
      state.debugPaused = false;
      state.snapshot.metadata = result.metadata || state.snapshot.metadata;

      CM6.show(key);
      CM6.setContent(result.content);
      CM6.setLanguage(language);
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

  async function openExternalReadonlySource(definition) {
    ensureEditorContainer();

    try {
      const result = await api.readSourceFile({
        projectRoot: state.snapshot.project.rootPath,
        path: definition.path,
      });
      const language = result.language || detectLanguage(result.path);
      const label = fileNameFromPath(result.path);
      const roKey = `readonly-${Date.now()}`;

      // Save current tab state
      syncActiveFileState(state, "out");

      // Create editor instance — pass #codeEditor as parent

      CM6.create(roKey, el.codeEditor, {
        onContentChange() {},
        onSelectionChange() {},
        onGutterClick() {},
        onDefinitionRequest() {},
      });

      // Activate first so setContent/setLanguage delegate to the new instance
      CM6.show(roKey);

      CM6.setContent(result.content);
      CM6.setLanguage(language);
      CM6.setEnabled(false);

      const entry = createOpenFileEntry({
        key: roKey,
        relativePath: "",
        label,
        language,
        dirty: false,
        readonlySource: { ...definition, path: result.path },
      });
      state.openFiles.push(entry);

      // Activate (show already called above)
      state.activeFileKey = roKey;

      state.currentFile = result.path;
      state.readonlySource = { ...definition, path: result.path };
      state.currentDebugLine = null;
      state.debugStartLine = null;
      state.debugSelection = null;
      state.debugPaused = false;

      syncEditorCompletionContext();
      setDirty(false);
      renderActiveFile();
      renderFileTree();
      CM6.scrollToLine(definition.line);
      appendLog("info", `Go to readonlySource: ${definition.name} -> ${result.path}:${definition.line}`);
    } catch (error) {
      appendLog("error", errorMessage(error));
    }
  }

  function renderActiveFile() {
    renderTabBar();

    if (!state.currentFile) {
      // No active file, but keep tab bar visible if there are tabs
      updateEmptyStateView("从左侧打开文件");
      updateFileActionState();
      return;
    }

    const file = currentFileRecord();
    const readonlySource = state.readonlySource;
    const fileName = readonlySource
      ? fileNameFromPath(readonlySource.path)
      : state.currentFile.split("/").pop();
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

  function updateEmptyStateView(message) {
    el.fileTitle.textContent = message;
    el.filePath.textContent = message;
    el.editorMeta.textContent = "UTF-8 · Spaces: 4";
    el.problemCount.textContent = "0";
    el.variableCount.textContent = "0";
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
      return false;
    }
    if (state.readonlySource) {
      appendLog("warn", "只读源码不能保存");
      if (options.source === "shortcut") {
        showActionFeedback("只读源码不能保存", "warn");
      }
      return false;
    }
    if (options.source === "shortcut" && !state.dirty) {
      showActionFeedback("当前文件已是最新", "info");
      return true;
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
      return true;
    } catch (error) {
      appendLog("error", errorMessage(error));
      showActionFeedback(`保存失败: ${errorMessage(error)}`, "error");
      return false;
    }
  }

  async function reloadOpenFiles(relativePaths = []) {
    if (!state.snapshot || !Array.isArray(relativePaths) || relativePaths.length === 0) {
      return;
    }
    const changed = new Set(relativePaths);
    const originalKey = state.activeFileKey;
    const reloadTargets = state.openFiles.filter((entry) => (
      changed.has(entry.relativePath) && !entry.dirty && !entry.readonlySource
    ));

    for (const entry of reloadTargets) {
      try {
        switchToTab(entry.key);
        const result = await api.readFile(
          state.snapshot.project.rootPath,
          entry.relativePath,
        );
        CM6.setContent(result.content);
        CM6.setLanguage(detectLanguage(result.relativePath));
        setDirty(false);
      } catch (error) {
        appendLog("warn", `刷新已打开文件失败: ${errorMessage(error)}`);
      }
    }

    if (originalKey && state.openFiles.some((entry) => entry.key === originalKey)) {
      switchToTab(originalKey);
    }
    renderActiveFile();
  }

  function clearEditor(message) {
    state.currentFile = null;
    state.readonlySource = null;
    state.currentDebugLine = null;
    state.debugStartLine = null;
    state.debugSelection = null;
    state.debugPaused = false;
    state.activeFileKey = null;
    // Don't call CM6.setContent or CM6.setEnabled — no active instance
    setDirty(false);
    renderActiveFile();
    resetCommandPreview();
    updateFileActionState();
  }

  function setDirty(isDirty) {
    state.dirty = isDirty;
    // Update the active tab entry
    const entry = activeFileEntry();
    if (entry) {
      entry.dirty = isDirty;
    }
    // Re-render tab bar to reflect dirty state
    if (state.currentFile) {
      renderTabBar();
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
    activeFileEntry,
    selectFile,
    openExternalReadonlySource,
    switchToTab,
    closeTab,
    renderActiveFile,
    renderTabBar,
    clearEditor,
    setDirty,
    saveCurrentFile,
    reloadOpenFiles,
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
