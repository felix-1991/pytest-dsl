const api = window.pytestDslGui;

function createConsoleBuffer() {
  return {
    lines: [],
    commandOutputChunks: [],
    droppedLineCount: 0,
  };
}

function createConsoleView() {
  return {
    wrap: true,
    open: false,
    expanded: false,
  };
}

function createCommandPreview(command = "pytest-dsl") {
  return {
    command,
    context: "preview",
    persistent: false,
    taskId: null,
  };
}

function createCommandBar(command = "pytest-dsl") {
  return {
    command,
    context: "preview",
    locked: false,
    taskId: null,
  };
}

const state = {
  snapshot: null,
  currentFile: null,
  dirty: false,
  filter: "",
  buildCaseFilter: "",
  selectedConfigPaths: [],
  selectedSuiteIds: [],
  selectedFileOverrides: {},
  selectedBuildSuiteIds: [],
  selectedBuildFileOverrides: {},
  expandedSuiteNodes: new Set(),
  suiteSelectionTouched: false,
  buildSelectionTouched: false,
  selectedTreePath: "",
  selectedTreeKind: "directory",
  activeView: "debug",
  buildCaseTreeSignature: null,
  collapsedTreeDirs: new Set(),
  configSignature: null,
  remoteStatus: emptyRemoteStatus(),
  remoteProbeSeq: 0,
  remoteMonitorTimer: null,
  remoteMonitorRunning: false,
  currentTaskId: null,
  currentTaskMode: null,
  currentBuildId: null,
  currentBuildStatus: "",
  currentBuildReportUrl: "",
  currentBuildReportText: "",
  currentBuildResultsDir: "",
  buildReportReloadTimer: null,
  buildReportReloadSeq: 0,
  buildReportRevealRaf: null,
  buildReportRevealTimer: null,
  buildHistory: [],
  currentDebugLine: null,
  debugStartLine: null,
  debugPaused: false,
  debugSelection: null,
  readonlySource: null,
  keywordPanelOpen: false,
  keywordSearchTimer: null,
  keywordLoadSeq: 0,
  keywordLoading: false,
  keywords: [],
  completionKeywords: [],
  completionKeywordProjectRoot: null,
  completionKeywordsLoaded: false,
  completionKeywordLoadPromise: null,
  consoleBuffers: {
    debug: createConsoleBuffer(),
    build: createConsoleBuffer(),
  },
  console: {
    activeScope: "debug",
    debug: createConsoleView(),
    build: createConsoleView(),
  },
  commandPreviews: {
    debug: createCommandPreview(),
    build: createCommandPreview(),
  },
  commandBar: createCommandBar(),
  consoleRenderScheduled: false,
  consoleRenderRaf: null,
  consoleRenderTimer: null,
  fileTreeRenderScheduled: false,
  fileTreeRenderRaf: null,
  fileTreeRenderTimer: null,
  buildCaseTreeRenderScheduled: false,
  buildCaseTreeRenderRaf: null,
  buildCaseTreeRenderTimer: null,
  treeContext: null,
  draggedTreeFile: null,
  treeDropTargetPath: null,
  entryDialogResolve: null,
  entryDialogPreviousFocus: null,
};

const REMOTE_MONITOR_INTERVAL_MS = 5000;
const MAX_CONSOLE_BUFFER_LINES = 2000;
const MAX_CONSOLE_RENDER_LINES = 600;
const TREE_ROW_HEIGHT = 34;
const TREE_RENDER_OVERSCAN = 12;
const TREE_FALLBACK_VIEW_ROWS = 80;
const LAYOUT_STORAGE_KEY = "pytest-dsl-gui-layout";
const LAYOUT_SIZES = {
  nav: {
    cssVar: "--nav-width",
    defaultValue: 308,
    min: 248,
    max: 560,
    axis: "x",
  },
  console: {
    cssVar: "--console-height",
    defaultValue: 190,
    min: 120,
    max: 380,
    axis: "y",
  },
};

const REMOTE_STATUS_LABELS = {
  online: "在线",
  offline: "离线",
  unchecked: "未探测",
};

const COMMAND_CONTEXT_LABELS = {
  preview: "当前命令",
  syntax: "语法检查",
  run: "文件运行",
  debug: "调试",
  suite: "测试套运行",
  build: "构建运行",
};

const BUILD_STATUS_LABELS = {
  passed: "构建通过",
  failed: "构建失败",
  stopped: "构建已停止",
};

const el = {};

document.addEventListener("DOMContentLoaded", () => {
  cacheElements();
  initializeLayoutSizing();
  bindEvents();
  applyConsoleViewState();
  CM6.createEditor(el.codeEditor, {
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
  CM6.setEnabled(false);
  syncEditorCompletionContext();
  setEmptyProjectState();
  appendLog("info", "Electron GUI initialized");
  appendLog("info", "请选择要打开的 pytest-dsl 项目");
});

function cacheElements() {
  [
    "projectName",
    "projectRoot",
    "topbar",
    "suitePicker",
    "suiteTrigger",
    "suiteSummary",
    "suiteMenu",
    "suiteList",
    "configPicker",
    "configTrigger",
    "configSummary",
    "remoteStatusSummary",
    "remoteStatusPopover",
    "remoteServiceRows",
    "openProjectBtn",
    "refreshBtn",
    "settingsBtn",
    "runAllBtn",
    "debugNavBtn",
    "buildNavBtn",
    "treeRefreshBtn",
    "collapseAllBtn",
    "branchName",
    "treePaneTitle",
    "fileFilter",
    "fileTree",
    "buildCaseTree",
    "treeContextMenu",
    "dirtyDot",
    "activeTab",
    "fileTitle",
    "filePath",
    "mainStage",
    "debugWorkspace",
    "buildPanel",
    "buildRunBtn",
    "buildStopBtn",
    "buildOpenReportBtn",
    "buildDownloadReportBtn",
    "buildDownloadLogsBtn",
    "buildToggleConsoleBtn",
    "buildStatus",
    "buildScope",
    "buildConfigSummary",
    "buildPytestArgs",
    "buildAllureStatus",
    "buildCommand",
    "buildResultsDir",
    "buildReportUrl",
    "buildReportFrame",
    "buildReportEmpty",
    "buildHistoryList",
    "editActionGroup",
    "executionActionGroup",
    "debugSessionGroup",
    "saveBtn",
    "syntaxBtn",
    "runBtn",
    "debugStepsBtn",
    "nextStepBtn",
    "continueDebugBtn",
    "stopBtn",
    "keywordBtn",
    "commandBtn",
    "commandBar",
    "generatedCommandStatus",
    "generatedCommandText",
    "copyCommandBtn",
    "regenerateCommandBtn",
    "keywordPanel",
    "keywordSearch",
    "keywordStatus",
    "keywordList",
    "codeEditor",
    "editorMeta",
    "problemCount",
    "variableCount",
    "commandContext",
    "commandPreview",
    "bottomConsole",
    "consoleToggleBtn",
    "consoleStatusToggleBtn",
    "consoleActions",
    "copyConsoleBtn",
    "wrapConsoleBtn",
    "expandConsoleBtn",
    "clearConsoleBtn",
    "consoleBody",
    "configCount",
    "configList",
    "configMerged",
    "metadataList",
    "deductionList",
    "workspaceStatus",
    "actionStatus",
    "gitStatus",
    "remoteStatusBar",
    "entryDialog",
    "entryDialogForm",
    "entryDialogTitle",
    "entryDialogLabel",
    "entryDialogInput",
    "entryDialogError",
    "entryDialogCancel",
  ].forEach((id) => {
    el[id] = document.getElementById(id);
  });
}

function bindEvents() {
  bindPanelResizers();
  el.openProjectBtn.addEventListener("click", openProject);
  el.refreshBtn.addEventListener("click", refreshProject);
  el.saveBtn.addEventListener("click", saveCurrentFile);
  el.syntaxBtn.addEventListener("click", () => runExecutionTask("syntax"));
  el.runBtn.addEventListener("click", () => runExecutionTask("run"));
  el.debugStepsBtn.addEventListener("click", () =>
    runExecutionTask("debug", currentDebugRunOptions()),
  );
  el.debugNavBtn.addEventListener("click", () => switchWorkspaceView("debug"));
  el.buildNavBtn.addEventListener("click", () => switchWorkspaceView("build"));
  el.buildRunBtn.addEventListener("click", runBuildExecution);
  el.buildStopBtn.addEventListener("click", stopCurrentTask);
  el.buildOpenReportBtn.addEventListener("click", openCurrentBuildReport);
  el.buildDownloadReportBtn.addEventListener("click", downloadCurrentBuildReport);
  el.buildDownloadLogsBtn.addEventListener("click", downloadCurrentBuildLogs);
  el.buildToggleConsoleBtn.addEventListener("click", toggleConsoleOpen);
  el.nextStepBtn.addEventListener("click", () => sendDebugCommand("next"));
  el.continueDebugBtn.addEventListener("click", () => sendDebugCommand("continue"));
  el.stopBtn.addEventListener("click", stopCurrentTask);
  el.runAllBtn.addEventListener("click", runSuiteExecution);
  el.consoleToggleBtn.addEventListener("click", toggleConsoleOpen);
  el.consoleStatusToggleBtn.addEventListener("click", toggleConsoleOpen);
  el.copyConsoleBtn.addEventListener("click", copyConsoleOutput);
  el.wrapConsoleBtn.addEventListener("click", toggleConsoleWrap);
  el.expandConsoleBtn.addEventListener("click", toggleConsoleExpanded);
  el.clearConsoleBtn.addEventListener("click", () => clearConsole());
  el.treeRefreshBtn.addEventListener("click", () =>
    refreshProject({ logMessage: "Refreshed project tree" }),
  );
  el.fileTree.addEventListener("contextmenu", handleFileTreeContextMenu);
  el.fileTree.addEventListener("click", handleFileTreeClick);
  el.fileTree.addEventListener("scroll", handleProjectTreeScroll);
  el.fileTree.addEventListener("dragstart", handleTreeDragStart);
  el.fileTree.addEventListener("dragend", handleTreeDragEnd);
  el.fileTree.addEventListener("dragover", handleTreeDragOver);
  el.fileTree.addEventListener("dragleave", handleTreeDragLeave);
  el.fileTree.addEventListener("drop", handleTreeDrop);
  el.suiteList.addEventListener("change", handleSuiteTreeChange);
  el.suiteList.addEventListener("click", handleSuiteTreeClick);
  el.buildCaseTree.addEventListener("change", handleSuiteTreeChange);
  el.buildCaseTree.addEventListener("click", handleSuiteTreeClick);
  el.buildCaseTree.addEventListener("scroll", handleBuildCaseTreeScroll);
  el.keywordList.addEventListener("click", handleKeywordListClick);
  el.treeContextMenu.addEventListener("click", handleTreeContextMenuClick);
  el.entryDialogForm.addEventListener("submit", handleEntryDialogSubmit);
  el.entryDialogCancel.addEventListener("click", () => closeEntryDialog(null));
  el.entryDialog.addEventListener("click", (event) => {
    if (event.target === el.entryDialog) {
      closeEntryDialog(null);
    }
  });
  el.entryDialog.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      closeEntryDialog(null);
    }
  });
  document.addEventListener("click", closeTransientPanelsForOutsideClick);
  document.addEventListener("keydown", handleEditorSaveShortcut, true);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeTreeContextMenu();
      closeTopPickers();
      closeKeywordPanel();
    }
  });
  el.suiteTrigger.addEventListener("click", () => {
    closeConfigPicker();
    closeKeywordPanel();
    el.suitePicker.classList.toggle("is-open");
    el.suiteTrigger.setAttribute(
      "aria-expanded",
      String(el.suitePicker.classList.contains("is-open")),
    );
  });
  el.collapseAllBtn.addEventListener("click", () => {
    if (state.activeView === "build") {
      setAllBuildCaseGroupsExpanded(false);
    } else {
      setAllTreeGroupsCollapsed(true);
    }
  });
  el.settingsBtn.addEventListener("click", () =>
    appendLog("info", "Settings shell is not implemented in this MVP"),
  );
  el.keywordBtn.addEventListener("click", () =>
    toggleKeywordPanel(),
  );
  el.commandBtn.addEventListener("click", () =>
    generateCurrentCommand(),
  );
  el.regenerateCommandBtn.addEventListener("click", () =>
    generateCurrentCommand(),
  );
  el.copyCommandBtn.addEventListener("click", () =>
    copyGeneratedCommand(),
  );
  el.keywordSearch.addEventListener("input", handleKeywordSearchInput);
  el.configTrigger.addEventListener("click", () => {
    closeSuitePicker();
    closeKeywordPanel();
    el.configPicker.classList.toggle("is-open");
    el.configTrigger.setAttribute(
      "aria-expanded",
      String(el.configPicker.classList.contains("is-open")),
    );
  });
  el.fileFilter.addEventListener("input", () => {
    const value = el.fileFilter.value.trim().toLowerCase();
    if (state.activeView === "build") {
      state.buildCaseFilter = value;
      scheduleBuildCaseTreeRender();
      return;
    }
    state.filter = value;
    scheduleFileTreeRender();
  });
  if (typeof api.onExecutionEvent === "function") {
    api.onExecutionEvent(handleExecutionEvent);
  }
  if (typeof api.onBuildEvent === "function") {
    api.onBuildEvent(handleBuildEvent);
  }
}

function closeSuitePicker() {
  el.suitePicker.classList.remove("is-open");
  el.suiteTrigger.setAttribute("aria-expanded", "false");
}

function closeConfigPicker() {
  el.configPicker.classList.remove("is-open");
  el.configTrigger.setAttribute("aria-expanded", "false");
}

function closeTopPickers() {
  closeSuitePicker();
  closeConfigPicker();
}

function switchWorkspaceView(view) {
  const nextView = view === "build" ? "build" : "debug";
  const isBuildView = nextView === "build";
  if (isBuildView && !confirmDiscardDirtyBeforeBuild()) {
    return;
  }
  state.activeView = nextView;
  el.debugWorkspace.hidden = isBuildView;
  el.buildPanel.hidden = !isBuildView;
  el.topbar.classList.toggle("is-build-view", isBuildView);
  el.suitePicker.hidden = isBuildView;
  el.runAllBtn.hidden = isBuildView;
  if (isBuildView) {
    closeSuitePicker();
  }
  el.debugNavBtn.classList.toggle("is-active", !isBuildView);
  el.buildNavBtn.classList.toggle("is-active", isBuildView);
  updateTreePaneForActiveView();
  setConsoleScope(nextView);
  syncBuildReportFrameVisibility({ defer: isBuildView });
  if (isBuildView) {
    ensureBuildCaseTreeRootExpanded();
    ensureBuildCaseTreeRendered();
    updateBuildSummary();
    previewCommand(buildCommandLabel(), { force: true, scope: "build" });
  } else {
    previewCommand(currentCommand(), { force: true, scope: "debug" });
  }
}

function confirmDiscardDirtyBeforeBuild() {
  if (!state.dirty) {
    return true;
  }
  const confirmed = window.confirm("当前文件有未保存修改，切换到构建页面前请确认。继续切换？");
  if (!confirmed) {
    showActionFeedback("当前文件有未保存修改，已停留在调试页面", "warn");
  }
  return confirmed;
}

function isSaveShortcut(event) {
  if (!event || event.defaultPrevented) {
    return false;
  }
  return (
    event.key.toLowerCase() === "s" &&
    (event.ctrlKey || event.metaKey) &&
    !event.altKey && !event.shiftKey
  );
}

async function handleEditorSaveShortcut(event) {
  if (!isSaveShortcut(event)) {
    return;
  }
  event.preventDefault();
  event.stopPropagation();
  await saveCurrentFile({ source: "shortcut" });
}

function closeTransientPanelsForOutsideClick(event) {
  if (!el.treeContextMenu.contains(event.target)) {
    closeTreeContextMenu();
  }
  if (!el.suitePicker.contains(event.target)) {
    closeSuitePicker();
  }
  if (!el.configPicker.contains(event.target)) {
    closeConfigPicker();
  }
  if (
    !el.keywordPanel.contains(event.target) &&
    !el.keywordBtn.contains(event.target)
  ) {
    closeKeywordPanel();
  }
}

function initializeLayoutSizing() {
  const saved = readLayoutSizing();
  Object.keys(LAYOUT_SIZES).forEach((kind) => {
    setLayoutSize(kind, saved[kind] || LAYOUT_SIZES[kind].defaultValue, {
      persist: false,
    });
  });
}

function bindPanelResizers() {
  document.querySelectorAll("[data-resizer]").forEach((resizer) => {
    const kind = resizer.dataset.resizer;
    if (!LAYOUT_SIZES[kind]) {
      return;
    }
    resizer.addEventListener("pointerdown", (event) =>
      startPanelResize(kind, event),
    );
    resizer.addEventListener("keydown", (event) =>
      handleResizerKeydown(kind, event),
    );
  });
}

function startPanelResize(kind, event) {
  if (event.button !== 0) {
    return;
  }
  event.preventDefault();
  const resizer = event.currentTarget;
  if (resizer && typeof resizer.setPointerCapture === "function") {
    resizer.setPointerCapture(event.pointerId);
  }
  const config = LAYOUT_SIZES[kind];
  const startPosition = config.axis === "y" ? event.clientY : event.clientX;
  const startSize = getLayoutSize(kind);
  let pendingSize = startSize;
  let animationFrame = null;
  document.body.classList.add(
    config.axis === "y" ? "is-resizing-console" : "is-resizing-layout",
  );

  const flushResize = () => {
    animationFrame = null;
    setLayoutSize(kind, pendingSize, { persist: false });
  };

  const handlePointerMove = (moveEvent) => {
    const currentPosition = config.axis === "y"
      ? moveEvent.clientY
      : moveEvent.clientX;
    const delta = currentPosition - startPosition;
    const nextSize = config.axis === "y"
      ? startSize - delta
      : startSize + delta;
    pendingSize = nextSize;
    if (animationFrame === null) {
      animationFrame = requestAnimationFrame(flushResize);
    }
  };

  const stopResize = (event) => {
    if (animationFrame !== null) {
      cancelAnimationFrame(animationFrame);
      flushResize();
    }
    persistLayoutSizing();
    if (
      resizer &&
      typeof resizer.releasePointerCapture === "function" &&
      typeof resizer.hasPointerCapture === "function" &&
      event &&
      resizer.hasPointerCapture(event.pointerId)
    ) {
      resizer.releasePointerCapture(event.pointerId);
    }
    document.body.classList.remove("is-resizing-layout", "is-resizing-console");
    document.removeEventListener("pointermove", handlePointerMove);
    document.removeEventListener("pointercancel", stopResize);
  };

  document.addEventListener("pointermove", handlePointerMove);
  document.addEventListener("pointerup", stopResize, { once: true });
  document.addEventListener("pointercancel", stopResize, { once: true });
}

function handleResizerKeydown(kind, event) {
  const config = LAYOUT_SIZES[kind];
  const keys = config && config.axis === "y"
    ? ["ArrowUp", "ArrowDown"]
    : ["ArrowLeft", "ArrowRight"];
  if (!keys.includes(event.key)) {
    return;
  }
  event.preventDefault();
  const step = event.shiftKey ? 40 : 16;
  const direction = event.key === "ArrowRight" || event.key === "ArrowUp"
    ? 1
    : -1;
  setLayoutSize(kind, getLayoutSize(kind) + direction * step);
}

function setLayoutSize(kind, size, options = {}) {
  const config = LAYOUT_SIZES[kind];
  if (!config) {
    return;
  }
  const clamped = clamp(Math.round(Number(size) || config.defaultValue), config.min, config.max);
  document.documentElement.style.setProperty(config.cssVar, `${clamped}px`);

  const resizer = document.querySelector(`[data-resizer="${kind}"]`);
  if (resizer) {
    resizer.setAttribute("aria-valuemin", String(config.min));
    resizer.setAttribute("aria-valuemax", String(config.max));
    resizer.setAttribute("aria-valuenow", String(clamped));
  }

  if (options.persist !== false) {
    persistLayoutSizing();
  }
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function getLayoutSize(kind) {
  const config = LAYOUT_SIZES[kind];
  if (!config) {
    return 0;
  }
  const rawValue = getComputedStyle(document.documentElement)
    .getPropertyValue(config.cssVar)
    .trim();
  return parseFloat(rawValue) || config.defaultValue;
}

function readLayoutSizing() {
  try {
    return JSON.parse(localStorage.getItem(LAYOUT_STORAGE_KEY) || "{}");
  } catch (_error) {
    return {};
  }
}

function persistLayoutSizing() {
  try {
    localStorage.setItem(
      LAYOUT_STORAGE_KEY,
      JSON.stringify({
        nav: getLayoutSize("nav"),
        console: getLayoutSize("console"),
      }),
    );
  } catch (_error) {
    // Layout sizing is a convenience preference; failing to persist is harmless.
  }
}

async function openProject() {
  try {
    const snapshot = await api.openProject();
    if (!snapshot) {
      appendLog("info", "Open project canceled");
      return;
    }
    applySnapshot(snapshot, "Opened project");
  } catch (error) {
    appendLog("error", errorMessage(error));
  }
}

async function refreshProject(options = {}) {
  if (!state.snapshot) {
    appendLog("warn", "请先打开一个项目");
    return;
  }

  try {
    const snapshot = await api.scanProject(state.snapshot.project.rootPath);
    applySnapshot(
      snapshot,
      options.logMessage || "Refreshed project",
      Object.prototype.hasOwnProperty.call(options, "preferredFile")
        ? options.preferredFile
        : state.currentFile,
    );
  } catch (error) {
    appendLog("error", errorMessage(error));
  }
}

function applySnapshot(snapshot, logMessage, preferredFile = null) {
  const previousRoot = state.snapshot && state.snapshot.project.rootPath;
  const previousSelected = previousRoot === snapshot.project.rootPath
    ? new Set(state.selectedConfigPaths)
    : null;
  const projectChanged = previousRoot !== snapshot.project.rootPath;

  state.snapshot = snapshot;
  state.currentFile = null;
  state.dirty = false;
  state.configSignature = snapshot.config && snapshot.config.signature
    ? snapshot.config.signature
    : null;
  if (projectChanged) {
    resetKeywordBrowser();
    resetEditorCompletionKeywords();
    state.currentBuildId = null;
    state.currentBuildStatus = "";
    state.currentBuildResultsDir = "";
    state.buildHistory = [];
    invalidateBuildCaseTreeRender();
    resetBuildReport();
    state.suiteSelectionTouched = false;
    state.buildSelectionTouched = false;
    state.selectedTreePath = "";
    state.selectedTreeKind = "directory";
    collapseTreeDirsBelowRoot();
    state.selectedFileOverrides = {};
    state.selectedBuildFileOverrides = {};
    state.expandedSuiteNodes.clear();
    closeEntryDialog(null);
  }
  initializeConfigSelection(snapshot, previousSelected);

  renderProject();
  renderFileTree();
  renderConfig();
  refreshRemoteStatuses();
  startDynamicRemoteMonitoring();
  renderMetadata(snapshot.metadata);
  renderDeductions();
  appendLog("info", `${logMessage}: ${snapshot.project.rootPath}`);

  const editableFiles = getEditableFiles(snapshot);
  const lastOpened = preferredFile || snapshot.metadata.lastOpenedFile;
  const initialFile =
    editableFiles.find((file) => file.relativePath === lastOpened) ||
    editableFiles[0];

  if (initialFile) {
    selectFile(initialFile.relativePath);
  } else {
    clearEditor("项目中没有找到可编辑文本文件");
  }
}

function setEmptyProjectState() {
  stopDynamicRemoteMonitoring();
  state.snapshot = null;
  state.currentFile = null;
  state.dirty = false;
  state.selectedConfigPaths = [];
  state.selectedSuiteIds = [];
  state.selectedFileOverrides = {};
  state.selectedBuildSuiteIds = [];
  state.selectedBuildFileOverrides = {};
  state.expandedSuiteNodes.clear();
  state.suiteSelectionTouched = false;
  state.buildSelectionTouched = false;
  state.selectedTreePath = "";
  state.selectedTreeKind = "directory";
  state.activeView = "debug";
  state.buildCaseTreeSignature = null;
  state.filter = "";
  state.buildCaseFilter = "";
  state.collapsedTreeDirs.clear();
  closeTreeContextMenu();
  closeEntryDialog(null);
  clearTreeDragState();
  state.configSignature = null;
  state.remoteStatus = emptyRemoteStatus();
  state.currentTaskId = null;
  state.currentTaskMode = null;
  state.currentBuildId = null;
  state.currentBuildStatus = "";
  state.currentBuildReportUrl = "";
  state.currentBuildReportText = "";
  state.currentBuildResultsDir = "";
  state.buildHistory = [];
  state.currentDebugLine = null;
  state.debugStartLine = null;
  state.debugPaused = false;
  state.debugSelection = null;
  state.readonlySource = null;
  resetAllConsoleState();
  resetKeywordBrowser();
  resetEditorCompletionKeywords();
  el.projectName.textContent = "Pytest DSL Studio";
  el.projectRoot.textContent = "选择一个外部项目开始";
  showActionFeedback("就绪", "info");
  el.branchName.textContent = "local";
  el.gitStatus.textContent = "local";
  el.workspaceStatus.textContent = "未打开项目";
  el.configCount.textContent = "0";
  el.configSummary.textContent = "未加载配置";
  renderRemoteStatus();
  el.suiteSummary.textContent = "打开项目后自动识别";
  el.suiteList.innerHTML = `<p class="empty">打开项目后显示 convention 测试套</p>`;
  el.buildCaseTree.innerHTML = `<p class="empty">打开项目后显示可构建案例</p>`;
  resetBuildReport();
  renderBuildHistory();
  switchWorkspaceView("debug");
  updateBuildSummary();
  el.fileTree.innerHTML = `<p class="empty">点击“打开项目”选择本地 pytest-dsl 项目</p>`;
  el.configList.innerHTML = `<p class="empty">打开项目后显示可加载的 YAML 配置</p>`;
  el.configMerged.textContent = "{}";
  renderMetadata({ lastOpenedFile: null, recentFiles: [], updatedAt: null });
  el.deductionList.innerHTML = `<li>未打开项目</li>`;
  clearEditor("选择一个文件");
  setRunningState(false);
}

function renderProject() {
  const snapshot = state.snapshot;
  const editableFiles = getEditableFiles(snapshot);
  el.projectName.textContent = snapshot.project.name;
  el.projectRoot.textContent = snapshot.project.rootPath;
  el.branchName.textContent = snapshot.git.displayName;
  el.gitStatus.textContent = snapshot.git.isGit
    ? `git: ${snapshot.git.displayName}`
    : "local";
  el.workspaceStatus.textContent = `${editableFiles.length} 文件 · ${snapshot.dslFiles.length} DSL · ${state.selectedConfigPaths.length}/${snapshot.config.sources.length} config · score ${snapshot.score.value}`;
  el.configCount.textContent = `${state.selectedConfigPaths.length}/${snapshot.config.sources.length}`;
  renderSuiteOptions(snapshot.suites || [], snapshot.suiteTree);
  updateBuildSummary();
}

function showActionFeedback(message, level = "info") {
  if (!el.actionStatus) {
    return;
  }
  el.actionStatus.textContent = message;
  el.actionStatus.title = message;
  el.actionStatus.classList.remove("is-info", "is-pass", "is-warn", "is-error");
  el.actionStatus.classList.add(`is-${level}`);
}

function updateTreePaneForActiveView() {
  const isBuildView = state.activeView === "build";
  el.treePaneTitle.textContent = isBuildView ? "构建案例" : "目录树";
  el.fileTree.hidden = isBuildView;
  el.buildCaseTree.hidden = !isBuildView;
  el.fileFilter.placeholder = isBuildView ? "筛选案例" : "筛选文件";
  const nextFilter = isBuildView ? state.buildCaseFilter : state.filter;
  if (el.fileFilter.value !== nextFilter) {
    el.fileFilter.value = nextFilter;
  }
}

function scheduleFileTreeRender() {
  if (state.fileTreeRenderScheduled) {
    return;
  }
  state.fileTreeRenderScheduled = true;
  const flush = () => {
    state.fileTreeRenderRaf = null;
    state.fileTreeRenderTimer = null;
    state.fileTreeRenderScheduled = false;
    renderFileTree();
  };
  if (typeof window.requestAnimationFrame === "function") {
    state.fileTreeRenderRaf = window.requestAnimationFrame(flush);
  } else {
    state.fileTreeRenderTimer = window.setTimeout(flush, 0);
  }
}

function virtualTreeWindow(container, totalRows) {
  const viewportHeight = container && container.clientHeight
    ? container.clientHeight
    : TREE_ROW_HEIGHT * TREE_FALLBACK_VIEW_ROWS;
  const scrollTop = container && container.scrollTop ? container.scrollTop : 0;
  const start = Math.max(0, Math.floor(scrollTop / TREE_ROW_HEIGHT) - TREE_RENDER_OVERSCAN);
  const end = Math.min(
    totalRows,
    Math.ceil((scrollTop + viewportHeight) / TREE_ROW_HEIGHT) + TREE_RENDER_OVERSCAN,
  );
  return {
    start,
    end,
    topSpacer: start * TREE_ROW_HEIGHT,
    bottomSpacer: Math.max(0, totalRows - end) * TREE_ROW_HEIGHT,
  };
}

function renderVirtualTreeRows(container, rows, renderRow) {
  const window = virtualTreeWindow(container, rows.length);
  const visibleRows = rows.slice(window.start, window.end);
  container.innerHTML = `
    <div class="tree-virtual-spacer" style="--tree-spacer-height: ${window.topSpacer}px"></div>
    <div class="tree-virtual-window">
      ${visibleRows.map(renderRow).join("")}
    </div>
    <div class="tree-virtual-spacer" style="--tree-spacer-height: ${window.bottomSpacer}px"></div>
  `;
}

function handleProjectTreeScroll() {
  closeTreeContextMenu();
  scheduleFileTreeRender();
}

function handleBuildCaseTreeScroll() {
  scheduleBuildCaseTreeRender();
}

function renderFileTree() {
  if (!state.snapshot) {
    return;
  }

  const tree = filterProjectTree(state.snapshot.tree, state.filter);
  const rows = flattenVisibleProjectTreeRows(tree);
  if (rows.length === 0) {
    el.fileTree.innerHTML = `<p class="empty">${state.filter ? "没有匹配的文件或目录" : "项目中没有可编辑文本文件"}</p>`;
    return;
  }

  renderVirtualTreeRows(el.fileTree, rows, renderProjectTreeRow);
}

function flattenVisibleProjectTreeRows(tree) {
  const rows = [];
  const visit = (node, depth) => {
    if (!node) {
      return;
    }
    if (node.type === "directory" && depth === -1) {
      (node.children || []).forEach((child) => visit(child, 0));
      return;
    }
    rows.push({ node, depth });
    if (node.type === "directory" && !state.collapsedTreeDirs.has(node.path)) {
      (node.children || []).forEach((child) => visit(child, depth + 1));
    }
  };
  visit(tree, tree && tree.type === "directory" ? -1 : 0);
  return rows;
}

function renderProjectTreeRow(row) {
  const node = row && row.node;
  const depth = row ? row.depth : 0;
  if (!node) {
    return "";
  }
  if (node.type === "directory") {
    return renderDirectoryRow(node, depth);
  }
  return renderFileRow(node, depth);
}

function renderDirectoryRow(group, depth = 0) {
  const collapsed = state.collapsedTreeDirs.has(group.path);
  const selected = state.selectedTreeKind === "directory" && state.selectedTreePath === group.path;
  return `
    <div class="tree-row tree-folder-row${selected ? " is-selected" : ""}" style="--depth: ${depth}" data-tree-row data-drop-target data-kind="directory" data-path="${escapeAttr(group.path)}">
      <button class="tree-row-main" type="button" data-tree-action="toggle-directory" data-kind="directory" data-path="${escapeAttr(group.path)}">
        <span class="folderIcon" aria-hidden="true">${folderIcon(collapsed ? "closed" : "open")}</span>
        <span class="name" title="${escapeAttr(group.path || group.name)}">${escapeHtml(group.name)}</span>
        <span class="count">${group.fileCount || 0}</span>
      </button>
    </div>
  `;
}

function renderProjectTreeNode(node, depth = 0) {
  if (!node) {
    return "";
  }
  if (node.type === "directory") {
    return renderDirectoryGroup(node, depth);
  }
  return renderFileRow(node, depth);
}

function renderDirectoryGroup(group, depth = 0) {
  const collapsed = state.collapsedTreeDirs.has(group.path);
  const selected = state.selectedTreeKind === "directory" && state.selectedTreePath === group.path;
  return `
    <div class="tree-group${collapsed ? " is-collapsed" : ""}" data-directory="${escapeAttr(group.path)}">
      <div class="tree-row tree-folder-row${selected ? " is-selected" : ""}" style="--depth: ${depth}" data-tree-row data-drop-target data-kind="directory" data-path="${escapeAttr(group.path)}">
        <button class="tree-row-main" type="button" data-tree-action="toggle-directory" data-kind="directory" data-path="${escapeAttr(group.path)}">
          <span class="folderIcon" aria-hidden="true">${folderIcon(collapsed ? "closed" : "open")}</span>
          <span class="name" title="${escapeAttr(group.path || group.name)}">${escapeHtml(group.name)}</span>
          <span class="count">${group.fileCount || 0}</span>
        </button>
      </div>
      <div class="tree-children">
        ${(group.children || []).map((child) => renderProjectTreeNode(child, depth + 1)).join("")}
      </div>
    </div>
  `;
}

function renderFileRow(file, depth = 0) {
  const relativePath = file.relativePath || file.path;
  const selected = state.currentFile === relativePath ||
    (state.selectedTreeKind === "file" && state.selectedTreePath === relativePath);
  return `
    <div class="tree-row tree-file-row${selected ? " is-selected" : ""}" style="--depth: ${depth}" data-tree-row data-draggable-file draggable="true" data-kind="file" data-path="${escapeAttr(relativePath)}">
      <button class="tree-row-main" type="button" data-tree-action="open-file" data-kind="file" data-path="${escapeAttr(relativePath)}">
        <span class="fileIcon ${fileKind(file)}" aria-hidden="true">${fileIcon(file)}</span>
        <span class="name" title="${escapeAttr(relativePath)}">${escapeHtml(file.name)}</span>
        <span class="count">${file.lineCount}</span>
      </button>
    </div>
  `;
}

function filterProjectTree(node, filter) {
  if (!node) {
    return null;
  }
  const needle = String(filter || "").trim().toLowerCase();
  if (!needle) {
    return node;
  }
  const matches = String(node.path || node.name || "").toLowerCase().includes(needle);
  if (node.type === "file") {
    return matches ? node : null;
  }
  const children = (node.children || [])
    .map((child) => filterProjectTree(child, needle))
    .filter(Boolean);
  if (matches) {
    return node;
  }
  return children.length > 0 ? { ...node, children } : null;
}

function handleTreeAction(event) {
  const action = event.currentTarget.dataset.treeAction;
  const kind = event.currentTarget.dataset.kind;
  const relativePath = event.currentTarget.dataset.path || "";
  closeTreeContextMenu();
  if (action === "toggle-directory") {
    toggleDirectory(relativePath);
    return;
  }
  if (action === "open-file") {
    openProjectTreeFile(relativePath);
    return;
  }
  if (action === "create-file") {
    handleCreateFile(relativePath);
    return;
  }
  if (action === "create-folder") {
    handleCreateFolder(relativePath);
    return;
  }
  if (action === "rename") {
    handleRenameEntry(kind, relativePath);
    return;
  }
  if (action === "delete") {
    handleDeleteEntry(kind, relativePath);
  }
}

function handleFileTreeClick(event) {
  const target = event.target && typeof event.target.closest === "function"
    ? event.target.closest("[data-tree-action]")
    : null;
  if (!target || !el.fileTree.contains(target)) {
    return;
  }
  handleTreeAction({ currentTarget: target });
}

function handleFileTreeContextMenu(event) {
  if (!state.snapshot) {
    return;
  }
  event.preventDefault();

  const row = event.target.closest("[data-tree-row]");
  const target = row && el.fileTree.contains(row)
    ? {
        kind: row.dataset.kind || "directory",
        path: row.dataset.path || "",
      }
    : {
        kind: "directory",
        path: "",
      };

  state.selectedTreeKind = target.kind;
  state.selectedTreePath = target.path;
  renderFileTree();
  openTreeContextMenu(target.kind, target.path, event.clientX, event.clientY);
}

function handleTreeDragStart(event) {
  const row = event.target.closest("[data-draggable-file]");
  if (!row || !el.fileTree.contains(row)) {
    return;
  }
  const relativePath = row.dataset.path || "";
  if (!relativePath) {
    return;
  }

  state.draggedTreeFile = relativePath;
  row.classList.add("is-dragging");
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", relativePath);
  }
  closeTreeContextMenu();
}

function handleTreeDragEnd() {
  clearTreeDragState();
}

function handleTreeDragOver(event) {
  const target = treeDropTargetFromEvent(event);
  if (!target || !canMoveTreeFileToDirectory(state.draggedTreeFile, target.path)) {
    clearTreeDropTarget();
    return;
  }

  event.preventDefault();
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = "move";
  }
  markTreeDropTarget(target.path);
}

function handleTreeDragLeave(event) {
  const currentTarget = event.target.closest("[data-drop-target]");
  if (!currentTarget || currentTarget.contains(event.relatedTarget)) {
    return;
  }
  clearTreeDropTarget();
}

async function handleTreeDrop(event) {
  const target = treeDropTargetFromEvent(event);
  if (!target || !canMoveTreeFileToDirectory(state.draggedTreeFile, target.path)) {
    clearTreeDragState();
    return;
  }

  event.preventDefault();
  const sourcePath = state.draggedTreeFile;
  const targetDirectory = target.path || "";
  clearTreeDragState();
  await handleMoveEntry(sourcePath, targetDirectory);
}

function treeDropTargetFromEvent(event) {
  const row = event.target.closest("[data-drop-target]");
  if (!row || !el.fileTree.contains(row)) {
    return null;
  }
  return {
    path: row.dataset.path || "",
  };
}

function canMoveTreeFileToDirectory(sourcePath, targetDirectory) {
  if (!sourcePath) {
    return false;
  }
  return normalizeTreeDirectory(parentDirectoryOf(sourcePath)) !== normalizeTreeDirectory(targetDirectory);
}

function markTreeDropTarget(relativePath) {
  if (state.treeDropTargetPath === relativePath) {
    return;
  }
  clearTreeDropTarget();
  state.treeDropTargetPath = relativePath;
  const selector = `[data-drop-target][data-path="${cssEscape(relativePath)}"]`;
  const row = el.fileTree.querySelector(selector);
  if (row) {
    row.classList.add("is-drop-target");
  }
}

function clearTreeDropTarget() {
  state.treeDropTargetPath = null;
  el.fileTree.querySelectorAll(".is-drop-target").forEach((row) => {
    row.classList.remove("is-drop-target");
  });
}

function clearTreeDragState() {
  state.draggedTreeFile = null;
  clearTreeDropTarget();
  el.fileTree.querySelectorAll(".is-dragging").forEach((row) => {
    row.classList.remove("is-dragging");
  });
}

function openTreeContextMenu(kind, relativePath, x, y) {
  if (!el.treeContextMenu) {
    return;
  }
  state.treeContext = {
    kind,
    path: relativePath || "",
  };

  el.treeContextMenu.dataset.contextKind = kind;
  el.treeContextMenu.dataset.contextPath = relativePath || "";
  el.treeContextMenu.innerHTML = renderTreeContextMenu(kind, relativePath);
  el.treeContextMenu.hidden = false;
  el.treeContextMenu.style.left = "0px";
  el.treeContextMenu.style.top = "0px";

  const menuRect = el.treeContextMenu.getBoundingClientRect();
  const maxLeft = Math.max(8, window.innerWidth - menuRect.width - 8);
  const maxTop = Math.max(8, window.innerHeight - menuRect.height - 8);
  const left = clamp(x, 8, maxLeft);
  const top = clamp(y, 8, maxTop);
  el.treeContextMenu.style.left = `${left}px`;
  el.treeContextMenu.style.top = `${top}px`;

  const firstAction = el.treeContextMenu.querySelector("[data-context-action]");
  if (firstAction) {
    firstAction.focus();
  }
}

function renderTreeContextMenu(kind, relativePath) {
  const label = relativePath || "项目根目录";
  const items = [
    `<div class="context-menu-label" title="${escapeAttr(label)}">${escapeHtml(label)}</div>`,
  ];

  if (kind === "directory") {
    items.push(contextMenuItem("create-file", "新建文件"));
    items.push(contextMenuItem("create-folder", "新建目录"));
    if (relativePath) {
      items.push(contextMenuSeparator());
      items.push(contextMenuItem("rename", "重命名"));
      items.push(contextMenuItem("delete", "删除", "danger"));
    }
  } else {
    items.push(contextMenuItem("open-file", "打开文件"));
    items.push(contextMenuSeparator());
    items.push(contextMenuItem("rename", "重命名"));
    items.push(contextMenuItem("delete", "删除", "danger"));
  }

  return items.join("");
}

function contextMenuItem(action, label, tone = "") {
  const toneClass = tone ? ` ${tone}` : "";
  return `<button class="context-menu-item${toneClass}" type="button" role="menuitem" data-context-action="${escapeAttr(action)}">${escapeHtml(label)}</button>`;
}

function contextMenuSeparator() {
  return `<div class="context-menu-separator" role="separator"></div>`;
}

async function handleTreeContextMenuClick(event) {
  const button = event.target.closest("[data-context-action]");
  if (!button || !el.treeContextMenu.contains(button)) {
    return;
  }
  event.preventDefault();
  event.stopPropagation();

  const action = button.dataset.contextAction;
  const context = readTreeContextMenuContext();
  if (!context) {
    closeTreeContextMenu();
    return;
  }
  closeTreeContextMenu();

  if (action === "open-file") {
    await openProjectTreeFile(context.path);
    return;
  }
  if (action === "create-file") {
    await handleCreateFile(context.path);
    return;
  }
  if (action === "create-folder") {
    await handleCreateFolder(context.path);
    return;
  }
  if (action === "rename") {
    await handleRenameEntry(context.kind, context.path);
    return;
  }
  if (action === "delete") {
    await handleDeleteEntry(context.kind, context.path);
  }
}

function readTreeContextMenuContext() {
  if (el.treeContextMenu.dataset.contextKind) {
    return {
      kind: el.treeContextMenu.dataset.contextKind,
      path: el.treeContextMenu.dataset.contextPath || "",
    };
  }
  return state.treeContext ? { ...state.treeContext } : null;
}

function closeTreeContextMenu() {
  state.treeContext = null;
  if (!el.treeContextMenu) {
    return;
  }
  el.treeContextMenu.hidden = true;
  el.treeContextMenu.innerHTML = "";
  delete el.treeContextMenu.dataset.contextKind;
  delete el.treeContextMenu.dataset.contextPath;
}

function toggleDirectory(relativePath) {
  state.selectedTreeKind = "directory";
  state.selectedTreePath = relativePath;
  if (state.collapsedTreeDirs.has(relativePath)) {
    state.collapsedTreeDirs.delete(relativePath);
  } else {
    state.collapsedTreeDirs.add(relativePath);
  }
  renderFileTree();
}

async function openProjectTreeFile(relativePath) {
  state.selectedTreeKind = "file";
  state.selectedTreePath = relativePath;
  if (
    state.dirty &&
    !window.confirm("当前文件尚未保存，是否继续打开其他文件？")
  ) {
    renderFileTree();
    return;
  }
  await selectFile(relativePath);
}

async function handleCreateFile(directory = null) {
  await createTreeEntry("file", directory);
}

async function handleCreateFolder(directory = null) {
  await createTreeEntry("directory", directory);
}

function requestEntryName({ title, label, defaultValue = "" }) {
  if (state.entryDialogResolve) {
    closeEntryDialog(null);
  }

  return new Promise((resolve) => {
    state.entryDialogResolve = resolve;
    state.entryDialogPreviousFocus =
      document.activeElement && typeof document.activeElement.focus === "function"
        ? document.activeElement
        : null;
    el.entryDialogTitle.textContent = title;
    el.entryDialogLabel.textContent = label;
    el.entryDialogInput.value = defaultValue;
    el.entryDialogError.hidden = true;
    el.entryDialogError.textContent = "";
    el.entryDialog.hidden = false;
    requestAnimationFrame(() => {
      el.entryDialogInput.focus();
      el.entryDialogInput.select();
    });
  });
}

function handleEntryDialogSubmit(event) {
  event.preventDefault();
  const value = el.entryDialogInput.value.trim();
  if (!value) {
    showEntryDialogError("名称不能为空");
    return;
  }
  closeEntryDialog(value);
}

function showEntryDialogError(message) {
  el.entryDialogError.textContent = message;
  el.entryDialogError.hidden = false;
  el.entryDialogInput.focus();
}

function closeEntryDialog(value) {
  if (!el.entryDialog) {
    return;
  }
  const resolve = state.entryDialogResolve;
  const previousFocus = state.entryDialogPreviousFocus;
  state.entryDialogResolve = null;
  state.entryDialogPreviousFocus = null;
  el.entryDialog.hidden = true;
  el.entryDialogInput.value = "";
  el.entryDialogError.hidden = true;
  el.entryDialogError.textContent = "";
  if (resolve) {
    resolve(value);
  }
  if (previousFocus && document.contains(previousFocus)) {
    previousFocus.focus();
  }
}

async function createTreeEntry(kind, directory = null) {
  if (!state.snapshot) {
    appendLog("warn", "请先打开一个项目");
    return;
  }
  const targetDirectory = normalizeTreeDirectory(
    directory === null ? selectedTargetDirectory() : directory,
  );
  const defaultName = kind === "directory" ? "new_folder" : "new_file.dsl";
  const name = await requestEntryName({
    title: kind === "directory" ? "新建目录" : "新建文件",
    label: kind === "directory" ? "目录名称" : "文件名称",
    defaultValue: defaultName,
  });
  if (!name) {
    return;
  }
  const relativePath = joinRelativePath(targetDirectory, name);
  try {
    const result = await api.createEntry(state.snapshot.project.rootPath, {
      kind,
      relativePath,
      content: kind === "file" ? "" : undefined,
    });
    if (kind === "directory") {
      state.selectedTreeKind = "directory";
      state.selectedTreePath = result.relativePath;
      state.collapsedTreeDirs.delete(result.relativePath);
    } else {
      state.selectedTreeKind = "file";
      state.selectedTreePath = result.relativePath;
    }
    await refreshProject({
      logMessage: `${kind === "directory" ? "Created folder" : "Created file"} ${result.relativePath}`,
      preferredFile: kind === "file" ? result.relativePath : state.currentFile,
    });
  } catch (error) {
    appendLog("error", errorMessage(error));
  }
}

async function handleRenameEntry(kind, relativePath) {
  if (!state.snapshot || !relativePath) {
    return;
  }
  if (!confirmDirtyTreeMutation(kind, relativePath)) {
    return;
  }
  const currentName = fileNameFromPath(relativePath);
  const newName = await requestEntryName({
    title: "重命名",
    label: "新名称",
    defaultValue: currentName,
  });
  if (!newName || newName === currentName) {
    return;
  }
  try {
    const result = await api.renameEntry(state.snapshot.project.rootPath, {
      relativePath,
      newName,
    });
    const preferredFile = remapPathAfterRename(relativePath, result.relativePath, state.currentFile);
    state.selectedTreeKind = kind;
    state.selectedTreePath = result.relativePath;
    await refreshProject({
      logMessage: `Renamed ${relativePath} -> ${result.relativePath}`,
      preferredFile,
    });
  } catch (error) {
    appendLog("error", errorMessage(error));
  }
}

async function handleMoveEntry(relativePath, targetDirectory) {
  if (!state.snapshot || !relativePath) {
    return;
  }
  const normalizedTargetDirectory = normalizeTreeDirectory(targetDirectory);
  if (!canMoveTreeFileToDirectory(relativePath, normalizedTargetDirectory)) {
    appendLog("info", `File already in ${normalizedTargetDirectory || "project root"}: ${relativePath}`);
    return;
  }
  if (!confirmDirtyTreeMutation("file", relativePath)) {
    return;
  }

  try {
    const result = await api.moveEntry(state.snapshot.project.rootPath, {
      relativePath,
      targetDirectory: normalizedTargetDirectory,
    });
    state.selectedTreeKind = "file";
    state.selectedTreePath = result.relativePath;
    state.collapsedTreeDirs.delete(normalizedTargetDirectory);
    await refreshProject({
      logMessage: `Moved ${relativePath} -> ${result.relativePath}`,
      preferredFile: state.currentFile === relativePath ? result.relativePath : state.currentFile,
    });
  } catch (error) {
    appendLog("error", errorMessage(error));
  }
}

async function handleDeleteEntry(kind, relativePath) {
  if (!state.snapshot || !relativePath) {
    return;
  }
  if (!confirmDirtyTreeMutation(kind, relativePath)) {
    return;
  }
  const label = kind === "directory" ? `目录 ${relativePath} 及其内容` : `文件 ${relativePath}`;
  if (!window.confirm(`确认删除${label}？`)) {
    return;
  }
  try {
    const affectsCurrent = pathAffectsCurrentFile(kind, relativePath);
    const result = await api.deleteEntry(state.snapshot.project.rootPath, {
      relativePath,
      recursive: kind === "directory",
    });
    state.selectedTreeKind = "directory";
    state.selectedTreePath = parentDirectoryOf(relativePath);
    await refreshProject({
      logMessage: `Deleted ${result.relativePath}`,
      preferredFile: affectsCurrent ? null : state.currentFile,
    });
  } catch (error) {
    appendLog("error", errorMessage(error));
  }
}

function selectedTargetDirectory() {
  if (state.selectedTreeKind === "directory") {
    return state.selectedTreePath || "";
  }
  if (state.selectedTreeKind === "file" && state.selectedTreePath) {
    return parentDirectoryOf(state.selectedTreePath);
  }
  if (state.currentFile) {
    return parentDirectoryOf(state.currentFile);
  }
  return "";
}

function confirmDirtyTreeMutation(kind, relativePath) {
  if (!state.dirty || !pathAffectsCurrentFile(kind, relativePath)) {
    return true;
  }
  return window.confirm("当前文件尚未保存，继续操作会丢失未保存内容，是否继续？");
}

function pathAffectsCurrentFile(kind, relativePath) {
  if (!state.currentFile) {
    return false;
  }
  if (kind === "file") {
    return state.currentFile === relativePath;
  }
  return state.currentFile === relativePath || state.currentFile.startsWith(`${relativePath}/`);
}

function remapPathAfterRename(oldPath, newPath, currentPath) {
  if (!currentPath) {
    return currentPath;
  }
  if (currentPath === oldPath) {
    return newPath;
  }
  if (currentPath.startsWith(`${oldPath}/`)) {
    return `${newPath}${currentPath.slice(oldPath.length)}`;
  }
  return currentPath;
}

function parentDirectoryOf(relativePath) {
  const parts = String(relativePath || "").split("/").filter(Boolean);
  parts.pop();
  return parts.join("/");
}

function normalizeTreeDirectory(relativePath) {
  return String(relativePath || "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
}

function joinRelativePath(directory, name) {
  return [normalizeTreeDirectory(directory), String(name || "").trim()]
    .filter(Boolean)
    .join("/");
}

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

function renderConfig() {
  const config = state.snapshot.config;
  const selectedSources = selectedConfigSources({ includeErrors: true });
  el.configSummary.textContent =
    selectedSources.length <= 1
      ? selectedSources[0]
        ? selectedSources[0].relativePath
        : "未选择配置"
      : `${selectedSources[0].relativePath} +${selectedSources.length - 1}`;
  el.configCount.textContent = `${selectedSources.length}/${config.sources.length}`;

  if (config.sources.length === 0) {
    el.configList.innerHTML = `<p class="empty">未找到可加载的 YAML 配置</p>`;
  } else {
    el.configList.innerHTML = config.sources
      .map(
        (source) => `
      <label class="config-option${source.ok ? "" : " is-error"}${source.defaultSelected ? " is-default" : ""}">
        <input
          type="checkbox"
          value="${escapeAttr(source.relativePath)}"
          ${state.selectedConfigPaths.includes(source.relativePath) ? "checked" : ""}
          ${source.ok ? "" : "disabled"}
        >
        <span title="${escapeAttr(source.relativePath)}">${escapeHtml(source.relativePath)}</span>
        <small>${source.ok ? `${Object.keys(source.data || {}).length} keys` : escapeHtml(source.error)}</small>
      </label>
    `,
      )
      .join("");
  }

  el.configList.querySelectorAll("input[type='checkbox']").forEach((input) => {
    input.addEventListener("change", handleConfigSelectionChange);
  });

  el.configMerged.textContent = JSON.stringify(selectedMergedConfig(), null, 2);
  updateBuildSummary();
}

function renderMetadata(metadata) {
  const rows = [
    ["存储", ".pytest-dsl-gui/metadata.json"],
    ["最近文件", metadata.lastOpenedFile || "未记录"],
    ["历史数量", String((metadata.recentFiles || []).length)],
    ["更新时间", metadata.updatedAt || "未写入"],
  ];

  el.metadataList.innerHTML = rows
    .map(
      ([key, value]) => `
    <dt>${escapeHtml(key)}</dt>
    <dd title="${escapeAttr(value)}">${escapeHtml(value)}</dd>
  `,
    )
    .join("");
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
  const canRun = executable && (runnableWholeFile || hasSelection);
  const canDebug = executable && (runnableWholeFile || hasSelection || hasDebugStart);

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
  el.syntaxBtn.disabled = !executable || isRunning;
  el.runBtn.disabled = !canRun || isRunning;
  el.debugStepsBtn.disabled = !canDebug || isRunning;
  el.nextStepBtn.disabled = !isDebugRunning || !state.debugPaused;
  el.continueDebugBtn.disabled = !isDebugRunning || !state.debugPaused;
  el.stopBtn.disabled = !isRunning;
  if ((el.keywordBtn.hidden || el.keywordBtn.disabled) && state.keywordPanelOpen) {
    closeKeywordPanel();
  }
  updateExecutionActionLabels(selection);
  previewCommand(currentCommand());
  updateBuildActionState();
}

function updateBuildActionState() {
  const hasProject = Boolean(state.snapshot);
  const hasSuites = currentSelectedSuiteIds("build").length > 0;
  const isBuildRunning = state.currentTaskId && state.currentTaskMode === "build";
  const isAnyTaskRunning = Boolean(state.currentTaskId);
  const hasCompletedBuild = Boolean(state.snapshot && state.currentBuildId && state.currentBuildStatus && state.currentBuildStatus !== "running");
  el.buildRunBtn.disabled = !hasProject || !hasSuites || isAnyTaskRunning;
  el.buildStopBtn.hidden = !isBuildRunning;
  el.buildStopBtn.disabled = !isBuildRunning;
  el.buildOpenReportBtn.disabled = !state.currentBuildReportUrl;
  el.buildDownloadReportBtn.disabled = !hasCompletedBuild || isAnyTaskRunning || !state.currentBuildResultsDir;
  el.buildDownloadLogsBtn.disabled = !hasCompletedBuild || isAnyTaskRunning;
}

function updateBuildSummary(options = {}) {
  if (!el.buildScope) {
    return;
  }
  const selectedSuiteIds = currentSelectedSuiteIds("build");
  const yamlVars = selectedConfigSources().map((source) => source.relativePath);
  const scopeLabel = state.snapshot
    ? selectedSuiteIds.length > 0
      ? suiteBuildScopeLabel(selectedSuiteIds)
      : "未选择构建案例"
    : "未打开项目";
  const command = options.command || buildCommandLabel(activeBuildCommandId());
  const resultsDir = options.resultsDir || state.currentBuildResultsDir || (
    state.currentBuildId
      ? buildResultsDirForBuild(state.currentBuildId)
      : "运行后生成"
  );
  const reportText = options.reportText ||
    state.currentBuildReportUrl ||
    state.currentBuildReportText ||
    "等待 Allure 报告";
  const pytestArgs = buildPytestArgsLabel(yamlVars, activeBuildCommandId());
  const configText = yamlVars.length > 0 ? yamlVars.join(", ") : "未选择 YAML 配置";

  el.buildScope.textContent = yamlVars.length > 0
    ? `${scopeLabel} · ${yamlVars.length} config`
    : scopeLabel;
  el.buildScope.title = el.buildScope.textContent;
  el.buildConfigSummary.textContent = configText;
  el.buildConfigSummary.title = configText;
  el.buildPytestArgs.textContent = pytestArgs;
  el.buildPytestArgs.title = pytestArgs;
  el.buildAllureStatus.textContent = reportText;
  el.buildAllureStatus.title = reportText;
  el.buildCommand.textContent = command;
  el.buildCommand.title = command;
  el.buildResultsDir.textContent = resultsDir;
  el.buildResultsDir.title = resultsDir;
  el.buildReportUrl.textContent = reportText;
  el.buildReportUrl.title = reportText;
  if (options.status) {
    el.buildStatus.textContent = options.status;
  } else if (!state.snapshot) {
    el.buildStatus.textContent = "打开项目后选择构建案例";
  } else if (selectedSuiteIds.length === 0) {
    el.buildStatus.textContent = "请在左侧选择要构建的案例";
  } else if (state.currentTaskMode === "build") {
    el.buildStatus.textContent = "构建运行中";
  } else {
    el.buildStatus.textContent = "准备运行 pytest 并生成 Allure 报告";
  }
  updateBuildActionState();
}

function resetBuildReport() {
  clearBuildReportReloadTimer();
  cancelBuildReportFrameReveal();
  state.currentBuildReportUrl = "";
  state.currentBuildReportText = "";
  state.buildReportReloadSeq = 0;
  el.buildReportFrame.src = "about:blank";
  el.buildReportFrame.hidden = true;
  el.buildReportEmpty.hidden = false;
  el.buildReportEmpty.textContent = "运行后会在这里直接显示 Allure 报告";
  el.buildReportUrl.textContent = "等待 Allure 报告";
  el.buildAllureStatus.textContent = "等待 Allure 报告";
  el.buildOpenReportBtn.disabled = true;
}

function setBuildReportUrl(url) {
  state.currentBuildReportUrl = normalizeAllureReportUrl(url);
  if (!state.currentBuildReportUrl) {
    resetBuildReport();
    return;
  }
  state.currentBuildReportText = "";
  el.buildReportFrame.src = buildReportFrameUrl(state.currentBuildReportUrl);
  syncBuildReportFrameVisibility({ defer: state.activeView === "build" });
  el.buildReportUrl.textContent = state.currentBuildReportUrl;
  el.buildReportUrl.title = state.currentBuildReportUrl;
  el.buildOpenReportBtn.disabled = false;
  scheduleBuildReportFrameReload();
}

function syncBuildReportFrameVisibility(options = {}) {
  cancelBuildReportFrameReveal();
  if (!state.currentBuildReportUrl) {
    el.buildReportFrame.hidden = true;
    el.buildReportEmpty.hidden = false;
    el.buildReportEmpty.textContent = "运行后会在这里直接显示 Allure 报告";
    return;
  }

  if (state.activeView !== "build") {
    el.buildReportFrame.hidden = true;
    el.buildReportEmpty.hidden = false;
    el.buildReportEmpty.textContent = "Allure 报告已生成，切到构建页后显示";
    return;
  }

  if (options.defer) {
    el.buildReportFrame.hidden = true;
    el.buildReportEmpty.hidden = false;
    el.buildReportEmpty.textContent = "Allure 报告准备就绪，正在加载视图";
    deferBuildReportFrameReveal();
    return;
  }

  revealBuildReportFrame();
}

function deferBuildReportFrameReveal() {
  const reveal = () => {
    state.buildReportRevealRaf = null;
    state.buildReportRevealTimer = window.setTimeout(() => {
      state.buildReportRevealTimer = null;
      revealBuildReportFrame();
    }, 0);
  };

  if (typeof window.requestAnimationFrame === "function") {
    state.buildReportRevealRaf = window.requestAnimationFrame(reveal);
  } else {
    state.buildReportRevealTimer = window.setTimeout(revealBuildReportFrame, 0);
  }
}

function revealBuildReportFrame() {
  if (!state.currentBuildReportUrl || state.activeView !== "build") {
    return;
  }
  el.buildReportFrame.hidden = false;
  el.buildReportEmpty.hidden = true;
}

function cancelBuildReportFrameReveal() {
  if (state.buildReportRevealRaf !== null && typeof window.cancelAnimationFrame === "function") {
    window.cancelAnimationFrame(state.buildReportRevealRaf);
  }
  state.buildReportRevealRaf = null;
  if (state.buildReportRevealTimer) {
    window.clearTimeout(state.buildReportRevealTimer);
    state.buildReportRevealTimer = null;
  }
}

function buildReportFrameUrl(url) {
  const value = String(url || "").trim();
  if (!value) {
    return "";
  }
  const reloadSeq = Number(arguments[1] || 0);
  const token = encodeURIComponent(state.currentBuildId || String(Date.now()));
  const hashIndex = value.indexOf("#");
  const base = hashIndex >= 0 ? value.slice(0, hashIndex) : value;
  const hash = hashIndex >= 0 ? value.slice(hashIndex) : "";
  const separator = base.includes("?") ? "&" : "?";
  const reloadToken = reloadSeq > 0 ? `-${encodeURIComponent(String(reloadSeq))}` : "";
  return `${base}${separator}pytestDslBuild=${token}${reloadToken}${hash}`;
}

function scheduleBuildReportFrameReload() {
  clearBuildReportReloadTimer();
  scheduleBuildReportReloadAttempt(1);
}

function scheduleBuildReportReloadAttempt(attempt) {
  if (!state.currentBuildReportUrl || attempt > 2) {
    return;
  }
  const buildId = state.currentBuildId;
  const reportUrl = state.currentBuildReportUrl;
  const delayMs = attempt === 1 ? 500 : 1500;
  state.buildReportReloadTimer = window.setTimeout(() => {
    if (state.currentBuildId !== buildId || state.currentBuildReportUrl !== reportUrl) {
      return;
    }
    state.buildReportReloadSeq += 1;
    el.buildReportFrame.src = buildReportFrameUrl(state.currentBuildReportUrl, state.buildReportReloadSeq);
    scheduleBuildReportReloadAttempt(attempt + 1);
  }, delayMs);
}

function clearBuildReportReloadTimer() {
  if (state.buildReportReloadTimer) {
    window.clearTimeout(state.buildReportReloadTimer);
    state.buildReportReloadTimer = null;
  }
}

function normalizeAllureReportUrl(url) {
  const value = String(url || "").trim();
  if (!value) {
    return "";
  }
  try {
    const parsed = new URL(value);
    const normalizedPath = parsed.pathname.replace(/\/+$/, "");
    if (!normalizedPath) {
      parsed.pathname = "/awesome/";
    } else if (normalizedPath.endsWith("/awesome")) {
      parsed.pathname = `${normalizedPath}/`;
    }
    return parsed.toString();
  } catch (_error) {
    return value;
  }
}

function openCurrentBuildReport() {
  if (!state.currentBuildReportUrl) {
    appendLog("warn", "当前没有可打开的 Allure 报告");
    return;
  }
  window.open(state.currentBuildReportUrl, "_blank", "noopener");
}

function currentBuildDownloadOptions() {
  if (!state.snapshot || !state.currentBuildId) {
    return null;
  }
  return {
    projectRoot: state.snapshot.project.rootPath,
    buildId: state.currentBuildId,
  };
}

async function downloadCurrentBuildReport() {
  const options = currentBuildDownloadOptions();
  if (!options || !state.currentBuildStatus || state.currentBuildStatus === "running") {
    appendLog("warn", "当前没有已完成的构建报告可下载", { scope: "build" });
    return;
  }
  if (!state.currentBuildResultsDir) {
    appendLog("warn", "当前构建没有 Allure results 目录", { scope: "build" });
    return;
  }
  if (typeof api.downloadBuildReport !== "function") {
    appendLog("warn", "当前环境不支持保存 Allure 报告", { scope: "build" });
    return;
  }

  el.buildDownloadReportBtn.disabled = true;
  appendLog("info", "正在生成并保存 Allure 报告", { scope: "build" });
  try {
    const result = await api.downloadBuildReport(options);
    if (result && result.canceled) {
      appendLog("info", "已取消保存 Allure 报告", { scope: "build" });
      return;
    }
    appendLog("pass", `Allure 报告已保存: ${result.path}`, { scope: "build" });
    showActionFeedback("Allure 报告已保存", "pass");
  } catch (error) {
    appendLog("error", `保存 Allure 报告失败: ${errorMessage(error)}`, { scope: "build" });
    showActionFeedback("保存 Allure 报告失败", "error");
  } finally {
    updateBuildActionState();
  }
}

async function downloadCurrentBuildLogs() {
  const options = currentBuildDownloadOptions();
  if (!options || !state.currentBuildStatus || state.currentBuildStatus === "running") {
    appendLog("warn", "当前没有已完成的构建日志可下载", { scope: "build" });
    return;
  }
  if (typeof api.downloadBuildLogs !== "function") {
    appendLog("warn", "当前环境不支持保存构建日志", { scope: "build" });
    return;
  }

  el.buildDownloadLogsBtn.disabled = true;
  appendLog("info", "正在保存构建日志", { scope: "build" });
  try {
    const result = await api.downloadBuildLogs(options);
    if (result && result.canceled) {
      appendLog("info", "已取消保存构建日志", { scope: "build" });
      return;
    }
    appendLog("pass", `构建日志已保存: ${result.path}`, { scope: "build" });
    showActionFeedback("构建日志已保存", "pass");
  } catch (error) {
    appendLog("error", `保存构建日志失败: ${errorMessage(error)}`, { scope: "build" });
    showActionFeedback("保存构建日志失败", "error");
  } finally {
    updateBuildActionState();
  }
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

function renderDeductions() {
  const deductions = state.snapshot.score.deductions;
  if (deductions.length === 0) {
    el.deductionList.innerHTML = `<li>无扣分项</li>`;
    return;
  }

  el.deductionList.innerHTML = deductions
    .map((item) => `<li>${escapeHtml(item.reason)} · -${item.points}</li>`)
    .join("");
}

function initializeConfigSelection(snapshot, previousSelected) {
  const availablePaths = new Set(
    snapshot.config.sources.map((source) => source.relativePath),
  );

  if (previousSelected) {
    state.selectedConfigPaths = Array.from(previousSelected).filter((item) =>
      availablePaths.has(item),
    );
    return;
  }

  const defaults = Array.isArray(snapshot.config.selectedPaths)
    ? snapshot.config.selectedPaths
    : snapshot.config.sources
        .filter((source) => source.defaultSelected)
        .map((source) => source.relativePath);
  const errorDefaults = snapshot.config.sources
    .filter((source) => source.defaultSelected && !source.ok)
    .map((source) => source.relativePath);
  state.selectedConfigPaths = Array.from(new Set([...defaults, ...errorDefaults]))
    .filter((item) => availablePaths.has(item));
}

function handleConfigSelectionChange() {
  state.selectedConfigPaths = Array.from(
    el.configList.querySelectorAll("input[type='checkbox']:checked"),
  ).map((input) => input.value);
  syncEditorCompletionContext();
  renderConfig();
  renderProject();
  refreshRemoteStatuses();
  if (state.currentFile) {
    renderActiveFile();
  } else {
    previewCommand(currentCommand(), { force: true });
  }
}

function selectedConfigSources(options = {}) {
  if (!state.snapshot) {
    return [];
  }
  const selected = new Set(state.selectedConfigPaths);
  return state.snapshot.config.sources.filter((source) => (
    selected.has(source.relativePath) && (options.includeErrors || source.ok)
  ));
}

function selectedConfigErrors() {
  if (!state.snapshot) {
    return [];
  }
  const selected = new Set(state.selectedConfigPaths);
  return state.snapshot.config.errors.filter((error) =>
    selected.has(error.relativePath),
  );
}

function selectedMergedConfig() {
  const merged = {};
  selectedConfigSources().forEach((source) => {
    if (isPlainObject(source.data)) {
      Object.assign(merged, source.data);
    }
  });
  return merged;
}

function syncEditorCompletionContext() {
  const language = state.currentFile && !state.readonlySource
    ? detectLanguage(state.currentFile)
    : "plain";
  const shouldComplete = language === "dsl" || language === "resource";
  if (typeof CM6.setCompletionContext === "function") {
    CM6.setCompletionContext({
      language,
      keywords: shouldComplete ? state.completionKeywords : [],
      variables: shouldComplete ? flattenConfigVariablePaths(selectedMergedConfig()) : [],
    });
  }
}

async function loadEditorCompletionKeywords() {
  if (!state.snapshot || !state.currentFile || state.readonlySource) {
    syncEditorCompletionContext();
    return;
  }
  const language = detectLanguage(state.currentFile);
  if (!(language === "dsl" || language === "resource")) {
    syncEditorCompletionContext();
    return;
  }

  const projectRoot = state.snapshot.project.rootPath;
  if (
    state.completionKeywordsLoaded &&
    state.completionKeywordProjectRoot === projectRoot
  ) {
    syncEditorCompletionContext();
    return;
  }
  if (state.completionKeywordLoadPromise) {
    return state.completionKeywordLoadPromise;
  }

  state.completionKeywordProjectRoot = projectRoot;
  state.completionKeywordLoadPromise = (async () => {
    try {
      const result = await api.listKeywords({
        projectRoot: state.snapshot.project.rootPath,
        query: "",
        limit: 500,
      });
      if (!state.snapshot || state.snapshot.project.rootPath !== projectRoot) {
        return;
      }
      state.completionKeywords = Array.isArray(result.keywords) ? result.keywords : [];
      state.completionKeywordsLoaded = true;
      syncEditorCompletionContext();
    } catch (error) {
      if (state.snapshot && state.snapshot.project.rootPath === projectRoot) {
        state.completionKeywords = [];
        state.completionKeywordsLoaded = true;
        syncEditorCompletionContext();
        appendLog("warn", `关键字补全加载失败: ${errorMessage(error)}`);
      }
    } finally {
      if (state.completionKeywordProjectRoot === projectRoot) {
        state.completionKeywordLoadPromise = null;
      }
    }
  })();

  return state.completionKeywordLoadPromise;
}

function resetEditorCompletionKeywords() {
  state.completionKeywords = [];
  state.completionKeywordProjectRoot = null;
  state.completionKeywordsLoaded = false;
  state.completionKeywordLoadPromise = null;
  syncEditorCompletionContext();
}

function flattenConfigVariablePaths(value, prefix = "", result = []) {
  if (isPlainObject(value)) {
    Object.keys(value)
      .sort((left, right) => left.localeCompare(right, "zh-CN"))
      .forEach((key) => {
        const path = prefix ? `${prefix}.${key}` : key;
        flattenConfigVariablePaths(value[key], path, result);
      });
    if (prefix) {
      result.push(prefix);
    }
    return result;
  }

  if (prefix) {
    result.push(prefix);
  }
  return Array.from(new Set(result));
}

function emptyRemoteStatus() {
  return {
    servers: [],
    counts: { online: 0, offline: 0, unchecked: 0 },
    checkedAt: null,
    loading: false,
  };
}

function startDynamicRemoteMonitoring() {
  stopDynamicRemoteMonitoring();
  if (!state.snapshot) {
    return;
  }
  state.remoteMonitorTimer = setInterval(
    runDynamicRemoteMonitorTick,
    REMOTE_MONITOR_INTERVAL_MS
  );
}

function stopDynamicRemoteMonitoring() {
  if (state.remoteMonitorTimer) {
    clearInterval(state.remoteMonitorTimer);
    state.remoteMonitorTimer = null;
  }
  state.remoteMonitorRunning = false;
}

async function runDynamicRemoteMonitorTick() {
  if (!state.snapshot || state.remoteMonitorRunning || state.remoteStatus.loading) {
    return;
  }

  state.remoteMonitorRunning = true;
  try {
    await refreshProjectConfigIfChanged();
    if (state.snapshot) {
      await refreshRemoteStatuses();
    }
  } catch (error) {
    appendLog("error", `Dynamic remote monitor failed: ${errorMessage(error)}`);
  } finally {
    state.remoteMonitorRunning = false;
  }
}

async function refreshProjectConfigIfChanged() {
  if (!state.snapshot || typeof api.scanProjectConfig !== "function") {
    return false;
  }

  const result = await api.scanProjectConfig(state.snapshot.project.rootPath);
  const config = result && result.config ? result.config : null;
  if (!config || config.signature === state.configSignature) {
    return false;
  }

  const previousSelected = new Set(state.selectedConfigPaths);
  state.snapshot.config = config;
  state.configSignature = config.signature || null;
  initializeConfigSelection(state.snapshot, previousSelected);
  renderConfig();
  renderProject();
  renderDeductions();
  if (state.currentFile) {
    renderActiveFile();
  } else {
    previewCommand(currentCommand());
  }
  appendLog("info", "Config files changed; remote status will refresh");
  return true;
}

async function refreshRemoteStatuses() {
  if (!state.snapshot) {
    state.remoteStatus = emptyRemoteStatus();
    renderRemoteStatus();
    return;
  }

  const servers = extractRemoteServers(selectedMergedConfig());
  const probeSeq = state.remoteProbeSeq + 1;
  state.remoteProbeSeq = probeSeq;
  state.remoteStatus = {
    servers: servers.map((server) => ({
      ...server,
      status: "unchecked",
      keywords: 0,
      latencyMs: null,
      error: null,
    })),
    counts: countRemoteStatuses(servers),
    checkedAt: null,
    loading: servers.length > 0,
  };
  renderRemoteStatus();

  if (servers.length === 0) {
    return;
  }

  try {
    const result = await api.checkRemoteServers(servers);
    if (probeSeq !== state.remoteProbeSeq) {
      return;
    }
    state.remoteStatus = { ...result, loading: false };
    renderRemoteStatus();
  } catch (error) {
    if (probeSeq !== state.remoteProbeSeq) {
      return;
    }
    state.remoteStatus = {
      servers: servers.map((server) => ({
        ...server,
        status: "offline",
        keywords: 0,
        latencyMs: null,
        error: errorMessage(error),
      })),
      counts: { online: 0, offline: servers.length, unchecked: 0 },
      checkedAt: new Date().toISOString(),
      loading: false,
    };
    renderRemoteStatus();
    appendLog("error", `Remote status check failed: ${errorMessage(error)}`);
  }
}

function renderRemoteStatus() {
  if (!el.remoteStatusSummary || !el.remoteServiceRows || !el.remoteStatusBar) {
    return;
  }

  const remote = state.remoteStatus || emptyRemoteStatus();
  const servers = (remote.servers || []).map((server) => ({
    ...server,
    current: isRemoteServerCurrent(server),
  }));
  const counts = remote.counts || countRemoteStatuses(servers);
  const total = servers.length;
  const dot = remoteDotClass(counts, total, remote.loading);
  const className = `remote-summary ${remoteSummaryClass(counts, total, remote.loading)}`;
  const unchecked = counts.unchecked || 0;

  el.remoteStatusSummary.className = className;
  if (total === 0) {
    el.remoteStatusSummary.innerHTML =
      `<span class="status-dot unchecked"></span><span>无远程服务</span>`;
    el.remoteStatusBar.innerHTML =
      `<span class="status-dot unchecked"></span>远程: 无远程服务`;
  } else {
    const checkingText = remote.loading ? " · 探测中" : "";
    el.remoteStatusSummary.innerHTML =
      `<span class="status-dot ${dot}"></span><span>远程 ${counts.online}/${total} · ${counts.offline} 离线 · ${unchecked} 未探测${checkingText}</span>`;
    el.remoteStatusBar.innerHTML =
      `<span class="status-dot ${dot}"></span>远程: ${counts.online} 在线 · ${counts.offline} 离线 · ${unchecked} 未探测${formatCheckedAt(remote.checkedAt)}`;
  }

  if (total === 0) {
    el.remoteServiceRows.innerHTML = `<p class="empty">选中的配置中没有 remote_servers</p>`;
    return;
  }

  const sorted = [...servers].sort((left, right) => {
    const rank = { offline: 0, unchecked: 1, online: 2 };
    if (left.current !== right.current) return left.current ? -1 : 1;
    return rank[left.status] - rank[right.status];
  });

  el.remoteServiceRows.innerHTML = sorted
    .map((server) => `
      <div class="remote-service-row${server.current ? " is-current" : ""}">
        <span class="status-dot ${escapeAttr(server.status)}"></span>
        <span class="remote-service-name">
          <strong title="${escapeAttr(server.alias)}">${escapeHtml(server.alias)}</strong>
          <span title="${escapeAttr(server.url || "未配置 URL")}">${escapeHtml(server.url || "未配置 URL")}</span>
        </span>
        <span class="remote-service-meta">${escapeHtml(REMOTE_STATUS_LABELS[server.status] || "未知")} · ${escapeHtml(formatRemoteMeta(server, remote.loading))}</span>
      </div>
    `)
    .join("");
}

function extractRemoteServers(configData) {
  const remoteServers = configData && configData.remote_servers;
  if (!remoteServers) {
    return [];
  }

  const servers = [];
  if (Array.isArray(remoteServers)) {
    remoteServers.forEach((server, index) => {
      if (isPlainObject(server)) {
        servers.push(normalizeRemoteServer(server, `remote_${index + 1}`));
      }
    });
  } else if (isPlainObject(remoteServers)) {
    Object.entries(remoteServers).forEach(([name, server]) => {
      if (typeof server === "string") {
        servers.push(normalizeRemoteServer({ alias: name, url: server }, name));
        return;
      }
      if (isPlainObject(server)) {
        servers.push(normalizeRemoteServer({ alias: name, ...server }, name));
      }
    });
  }

  const seen = new Set();
  return servers.filter((server) => {
    const key = server.alias || server.url;
    if (!key || seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function normalizeRemoteServer(server, fallbackAlias) {
  return {
    alias: String(server.alias || server.name || fallbackAlias),
    url: server.url ? String(server.url) : "",
    timeout: server.timeout,
  };
}

function countRemoteStatuses(servers) {
  return (servers || []).reduce(
    (counts, server) => {
      const status = server.status || "unchecked";
      counts[status] = (counts[status] || 0) + 1;
      return counts;
    },
    { online: 0, offline: 0, unchecked: 0 },
  );
}

function remoteSummaryClass(counts, total, loading) {
  if (total === 0) return "is-empty";
  if (loading) return "is-unchecked";
  if (counts.offline > 0 && counts.online === 0) return "is-offline";
  if (counts.offline > 0) return "is-warning";
  if (counts.unchecked > 0) return "is-unchecked";
  return "is-online";
}

function remoteDotClass(counts, total, loading) {
  if (total === 0 || loading) return "unchecked";
  if (counts.offline > 0) return "warning";
  if (counts.unchecked > 0) return "unchecked";
  return "online";
}

function formatRemoteMeta(server, loading) {
  if (loading && server.status === "unchecked") {
    return "探测中";
  }
  if (server.status === "online") {
    return `${server.keywords || 0} 关键字 · ${server.latencyMs || 0}ms`;
  }
  if (server.status === "offline") {
    return server.error || "连接失败";
  }
  return server.error || "未探测";
}

function formatCheckedAt(checkedAt) {
  if (!checkedAt) {
    return "";
  }
  const date = new Date(checkedAt);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return ` · 已检查 ${date.toTimeString().slice(0, 5)}`;
}

function isRemoteServerCurrent(server) {
  if (!server || !server.alias || !state.currentFile) {
    return false;
  }
  const content = CM6.getContent();
  const alias = escapeRegExp(server.alias);
  return new RegExp(`(^|\\s)${alias}\\|`).test(content) ||
    new RegExp(`\\bas\\s+${alias}\\b`).test(content);
}

function handleDefinitionRequest(request) {
  if (!request || !request.keywordName) {
    return;
  }
  goToKeywordDefinition(request.keywordName, {
    showAll: Boolean(request.showAll),
    source: request.source || "editor",
  });
}

async function goToKeywordDefinition(keywordName, options = {}) {
  if (!state.snapshot) {
    appendLog("warn", "请先打开一个项目");
    return;
  }
  if (!state.currentFile || state.readonlySource || !isExecutableFile(state.currentFile)) {
    appendLog("warn", "当前文件不支持关键字跳转");
    return;
  }

  try {
    const result = await api.findKeywordDefinitions({
      projectRoot: state.snapshot.project.rootPath,
      keywordName,
    });
    const definitions = Array.isArray(result.definitions) ? result.definitions : [];
    if (definitions.length === 0) {
      appendLog("warn", `未找到关键字定义: ${keywordName}`);
      return;
    }
    const target = chooseDefinitionTarget(definitions, options);
    await openDefinitionTarget(target);
  } catch (error) {
    appendLog("error", errorMessage(error));
  }
}

function chooseDefinitionTarget(definitions, options = {}) {
  if (definitions.length > 1 && options.showAll) {
    appendLog(
      "info",
      `Definition candidates: ${definitions.map((item) => `${item.sourceType}:${item.path}:${item.line}`).join(" | ")}`,
    );
  }
  return definitions[0];
}

async function openDefinitionTarget(definition) {
  if (definition.relativePath) {
    await selectFile(definition.relativePath);
    CM6.scrollToLine(definition.line);
    appendLog("info", `Go to definition: ${definition.name} -> ${definition.relativePath}:${definition.line}`);
    return;
  }

  await openExternalReadonlySource(definition);
}

async function openExternalReadonlySource(definition) {
  const result = await api.readSourceFile({
    projectRoot: state.snapshot.project.rootPath,
    path: definition.path,
  });
  state.currentFile = result.path;
  state.readonlySource = {
    ...definition,
    path: result.path,
  };
  state.currentDebugLine = null;
  state.debugStartLine = null;
  state.debugSelection = null;
  state.debugPaused = false;
  CM6.setContent(result.content);
  CM6.setLanguage(result.language || detectLanguage(result.path));
  CM6.setEnabled(false);
  syncEditorCompletionContext();
  setDirty(false);
  renderActiveFile();
  renderFileTree();
  CM6.scrollToLine(definition.line);
  appendLog("info", `Go to readonlySource: ${definition.name} -> ${result.path}:${definition.line}`);
}

function resetKeywordBrowser() {
  if (state.keywordSearchTimer) {
    clearTimeout(state.keywordSearchTimer);
    state.keywordSearchTimer = null;
  }
  state.keywordPanelOpen = false;
  state.keywordLoadSeq += 1;
  state.keywordLoading = false;
  state.keywords = [];
  if (el.keywordPanel) {
    el.keywordPanel.hidden = true;
  }
  if (el.keywordSearch) {
    el.keywordSearch.value = "";
  }
  if (el.keywordStatus) {
    el.keywordStatus.textContent = "未加载";
  }
  if (el.keywordList) {
    el.keywordList.innerHTML = "";
  }
}

function closeKeywordPanel() {
  state.keywordPanelOpen = false;
  if (el.keywordPanel) {
    el.keywordPanel.hidden = true;
  }
}

function toggleKeywordPanel() {
  if (!state.snapshot) {
    appendLog("warn", "请先打开一个项目");
    return;
  }

  state.keywordPanelOpen = !state.keywordPanelOpen;
  el.keywordPanel.hidden = !state.keywordPanelOpen;

  if (!state.keywordPanelOpen) {
    return;
  }

  el.keywordSearch.focus();
  loadKeywords(el.keywordSearch.value.trim());
}

function handleKeywordSearchInput() {
  if (state.keywordSearchTimer) {
    clearTimeout(state.keywordSearchTimer);
  }
  state.keywordSearchTimer = setTimeout(() => {
    state.keywordSearchTimer = null;
    loadKeywords(el.keywordSearch.value.trim());
  }, 220);
}

async function loadKeywords(query = "") {
  if (!state.snapshot || !state.keywordPanelOpen) {
    return;
  }

  const loadSeq = state.keywordLoadSeq + 1;
  state.keywordLoadSeq = loadSeq;
  state.keywordLoading = true;
  el.keywordStatus.textContent = query ? `查找: ${query}` : "加载中";
  el.keywordList.innerHTML = `<p class="empty">加载关键字...</p>`;

  try {
    const result = await api.listKeywords({
      projectRoot: state.snapshot.project.rootPath,
      query,
      limit: 80,
    });
    if (loadSeq !== state.keywordLoadSeq) {
      return;
    }
    state.keywords = Array.isArray(result.keywords) ? result.keywords : [];
    state.keywordLoading = false;
    renderKeywordList(result.summary || {});
  } catch (error) {
    if (loadSeq !== state.keywordLoadSeq) {
      return;
    }
    state.keywordLoading = false;
    state.keywords = [];
    el.keywordStatus.textContent = "加载失败";
    el.keywordList.innerHTML = `<p class="empty">无法加载关键字</p>`;
    appendLog("error", errorMessage(error));
  }
}

function renderKeywordList(summary = {}) {
  if (!state.keywordPanelOpen) {
    return;
  }
  const visibleCount = state.keywords.length;
  const totalCount = Number(summary.total_count) || visibleCount;
  el.keywordStatus.textContent = `${visibleCount}/${totalCount} 关键字`;

  if (visibleCount === 0) {
    el.keywordList.innerHTML = `<p class="empty">没有匹配的关键字</p>`;
    return;
  }

  el.keywordList.innerHTML = state.keywords
    .map(renderKeywordRow)
    .join("");
}

function handleKeywordListClick(event) {
  const button = event.target && typeof event.target.closest === "function"
    ? event.target.closest(".keyword-row[data-index]")
    : null;
  if (!button || !el.keywordList.contains(button)) {
    return;
  }
  insertKeyword(Number(button.dataset.index));
}

function renderKeywordRow(keyword, index) {
  const parameters = (keyword.parameters || [])
    .map((param) => param.name || param.mapping)
    .filter(Boolean)
    .slice(0, 4);
  const parameterText = parameters.length > 0
    ? parameters.join(", ")
    : "无参数";
  const metaParts = [
    keyword.categoryName,
    keyword.source,
    keyword.documentation,
  ].filter(Boolean);

  return `
    <button class="keyword-row" type="button" data-index="${index}">
      <span class="keyword-name">
        <strong>${escapeHtml(keyword.name)}</strong>
        <span title="${escapeAttr(metaParts.join(" · "))}">${escapeHtml(metaParts.join(" · ") || "pytest-dsl 关键字")}</span>
      </span>
      <span class="keyword-param" title="${escapeAttr(parameterText)}">${escapeHtml(parameterText)}</span>
    </button>
  `;
}

function insertKeyword(index) {
  const keyword = state.keywords[index];
  if (!keyword) {
    return;
  }
  if (!canInsertKeywordIntoCurrentFile()) {
    appendLog("warn", "打开可编辑的 DSL 或 Resource 文件后可插入关键字");
    return;
  }
  const snippet = buildKeywordSnippet(keyword);
  CM6.insertText(snippet);
  appendLog("info", `Inserted keyword: ${keyword.name}`);
}

function canInsertKeywordIntoCurrentFile() {
  return Boolean(
    state.currentFile &&
      !state.readonlySource &&
      isExecutableFile(state.currentFile),
  );
}

function buildKeywordSnippet(keyword) {
  const parameters = (keyword.parameters || [])
    .map((param) => param.name || param.mapping)
    .filter(Boolean);
  if (parameters.length === 0) {
    return `[${keyword.name}]`;
  }
  return `[${keyword.name}], ${parameters.map((name) => `${name}: `).join(", ")}`;
}

function normalizeCommandText(command) {
  return String(command || "pytest-dsl").replace(/\s+/g, " ").trim() || "pytest-dsl";
}

async function generateCurrentCommand() {
  const command = normalizeCommandText(currentCommand());
  previewCommand(command, { force: true });
  lockGeneratedCommand(command);
  appendLog("info", `命令已锁定: ${command}`);
  showActionFeedback("命令已锁定", "info");
  return command;
}

async function copyGeneratedCommand() {
  const command = normalizeCommandText(state.commandBar.command || currentCommand());
  if (!command) {
    appendLog("warn", "没有可复制的命令");
    return "";
  }

  if (typeof api.copyText !== "function") {
    appendLog("warn", "当前环境不支持复制命令");
    return command;
  }

  try {
    await api.copyText(command);
    appendLog("pass", "命令已复制");
    showActionFeedback("命令已复制", "pass");
  } catch (error) {
    appendLog("warn", `复制命令失败: ${errorMessage(error)}`);
  }

  return command;
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
  resetConsoleForExecution("debug");
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
    if (mode === "syntax") {
      showActionFeedback("语法检查失败", "error");
    }
    if (state.currentTaskId === taskId) {
      releaseExecutionCommand(taskId);
      setRunningState(false);
    }
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

  const selectedSuiteIds = currentSelectedSuiteIds("debug");
  if (selectedSuiteIds.length === 0) {
    appendLog("warn", "没有可运行的测试套");
    return;
  }
  const yamlVars = selectedConfigSources().map((source) => source.relativePath);
  const taskId = createTaskId("suite");
  const command = suiteCommandLabel(selectedSuiteIds, yamlVars);
  resetConsoleForExecution("debug");
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
    if (state.currentTaskId === taskId) {
      releaseExecutionCommand(taskId);
      setRunningState(false);
    }
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
  resetConsoleForExecution("build");
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
    if (state.currentTaskId === buildId) {
      releaseExecutionCommand(buildId);
      setRunningState(false);
      state.currentBuildStatus = "";
      updateBuildSummary({ status: "构建启动失败" });
    }
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
    state.currentBuildReportText = `Allure 实时报告不可用: ${event.reason || "unknown"}`;
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
  }
}

function buildStatusLabel(status) {
  return BUILD_STATUS_LABELS[status] || `构建 ${status || "完成"}`;
}

function recordBuildHistory(event) {
  const entry = {
    buildId: event.buildId,
    status: event.status,
    durationMs: event.durationMs,
    exitCode: event.exitCode,
    resultsDir: event.allureResultsDir || "",
    reportUrl: event.reportUrl || state.currentBuildReportUrl || "",
    command: buildCommandLabel(event.buildId),
    completedAt: new Date().toLocaleTimeString(),
  };
  state.buildHistory = [entry, ...state.buildHistory]
    .filter((item, index, list) =>
      index === list.findIndex((candidate) => candidate.buildId === item.buildId),
    )
    .slice(0, 8);
  renderBuildHistory();
}

function renderBuildHistory() {
  if (!el.buildHistoryList) {
    return;
  }
  if (!state.buildHistory.length) {
    el.buildHistoryList.innerHTML = `<p class="empty">还没有构建记录</p>`;
    return;
  }
  el.buildHistoryList.innerHTML = state.buildHistory
    .map((entry) => `
      <article class="build-history-item">
        <div class="build-history-line">
          <strong>${escapeHtml(buildStatusLabel(entry.status))}</strong>
          <span>${escapeHtml(entry.completedAt)}</span>
        </div>
        <code title="${escapeAttr(entry.command)}">${escapeHtml(entry.command)}</code>
        <dl>
          <div>
            <dt>耗时</dt>
            <dd>${Number(entry.durationMs || 0)}ms</dd>
          </div>
          <div>
            <dt>退出码</dt>
            <dd>${entry.exitCode === null || entry.exitCode === undefined ? "-" : escapeHtml(String(entry.exitCode))}</dd>
          </div>
        </dl>
        <p title="${escapeAttr(entry.resultsDir)}">${escapeHtml(entry.resultsDir || "无结果目录")}</p>
        ${entry.reportUrl ? `<a href="${escapeAttr(entry.reportUrl)}" target="_blank" rel="noreferrer">打开报告</a>` : ""}
      </article>
    `)
    .join("");
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

function currentCommand() {
  if (!state.snapshot) {
    return "pytest-dsl";
  }
  if (state.activeView === "build") {
    return buildCommandLabel(activeBuildCommandId());
  }
  if (!state.currentFile || !isExecutableFile(state.currentFile)) {
    return suiteCommandLabel(currentSelectedSuiteIds("debug"), selectedConfigSources().map((source) => source.relativePath), "debug");
  }
  const selection = CM6.getSelection();
  const sourceLabel = executionSourceLabel(state.currentFile, selection, null);
  return executionCommandLabel("run", sourceLabel, selectedConfigSources().map((source) => source.relativePath));
}

function configArgs() {
  const sources = selectedConfigSources();
  if (!state.snapshot || sources.length === 0) {
    return "";
  }
  return sources
    .map((source) => `--yaml-vars ${source.relativePath}`)
    .join(" ");
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

function previewCommand(command = currentCommand(), options = {}) {
  const scope = normalizeConsoleScope(options.scope || state.console.activeScope);
  const preview = commandPreviewForScope(scope);
  if (preview.taskId) {
    return preview.command;
  }
  if (preview.persistent && !options.force) {
    return preview.command;
  }
  return updateCommandPreview(command, {
    context: "preview",
    persistent: false,
    taskId: null,
    scope,
  });
}

function setExecutionCommand(command, options = {}) {
  const scope = normalizeConsoleScope(options.scope || consoleScopeForMode(options.mode));
  const updated = updateCommandPreview(command, {
    context: commandContextForMode(options.mode),
    persistent: true,
    taskId: options.taskId || null,
    scope,
  });
  if (scope === "debug") {
    lockGeneratedCommand(updated, {
      context: commandContextForMode(options.mode),
      taskId: options.taskId || null,
    });
  }
  return updated;
}

function releaseExecutionCommand(taskId) {
  const preview = commandPreviewForTask(taskId) || currentCommandPreview();
  if (
    taskId &&
    preview.taskId &&
    preview.taskId !== taskId
  ) {
    return preview.command;
  }
  preview.taskId = null;
  preview.persistent = false;
  preview.context = "preview";
  releaseCommandBarTask(taskId);
  updateCommandPreview(currentCommand(), {
    context: "preview",
    persistent: false,
    taskId: null,
    scope: consoleScopeForMode(state.currentTaskMode),
  });
  return preview.command;
}

function resetCommandPreview(command = "pytest-dsl") {
  const preview = currentCommandPreview();
  preview.command = command;
  preview.context = "preview";
  preview.persistent = false;
  preview.taskId = null;
  resetCommandBar(command);
  renderCommandPreview();
  return command;
}

function updateCommandPreview(command, options = {}) {
  const scope = normalizeConsoleScope(options.scope || consoleScopeForMode(options.context));
  const preview = state.commandPreviews[scope];
  const normalized = normalizeCommandText(command);
  preview.command = normalized;
  preview.context = options.context || preview.context || "preview";
  preview.persistent = Boolean(options.persistent);
  preview.taskId = options.taskId || null;

  if (scope === state.console.activeScope) {
    renderCommandPreview();
  }
  if (scope === "debug") {
    syncCommandBarPreview(normalized, { context: preview.context });
  }
  return normalized;
}

function syncCommandBarPreview(command, options = {}) {
  if (state.commandBar.locked) {
    return state.commandBar.command;
  }
  state.commandBar.command = normalizeCommandText(command);
  state.commandBar.context = options.context || "preview";
  state.commandBar.taskId = null;
  renderCommandBar();
  return state.commandBar.command;
}

function lockGeneratedCommand(command, options = {}) {
  state.commandBar.command = normalizeCommandText(command);
  state.commandBar.context = options.context || "preview";
  state.commandBar.locked = true;
  state.commandBar.taskId = options.taskId || null;
  renderCommandBar();
  return state.commandBar.command;
}

function releaseCommandBarTask(taskId) {
  if (taskId && state.commandBar.taskId === taskId) {
    state.commandBar.taskId = null;
    renderCommandBar();
  }
}

function resetCommandBar(command = "pytest-dsl") {
  state.commandBar = createCommandBar(normalizeCommandText(command));
  renderCommandBar();
  return state.commandBar.command;
}

function currentCommandPreview() {
  return commandPreviewForScope(state.console.activeScope);
}

function commandPreviewForScope(scope) {
  return state.commandPreviews[normalizeConsoleScope(scope)];
}

function commandPreviewForTask(taskId) {
  if (!taskId) {
    return null;
  }
  return Object.values(state.commandPreviews)
    .find((preview) => preview.taskId === taskId) || null;
}

function renderCommandPreview() {
  const preview = currentCommandPreview();
  const label = commandContextLabel(preview.context);
  el.commandContext.textContent = label;
  el.commandContext.title = label;
  el.commandPreview.textContent = preview.command;
  el.commandPreview.title = preview.command;
}

function renderCommandBar() {
  if (!el.commandBar) {
    return;
  }
  const title = state.commandBar.locked
    ? `保持到下次生成或执行 · ${commandContextLabel(state.commandBar.context)}`
    : "随当前文件、选择和配置实时更新";
  el.commandBar.classList.toggle("is-locked", state.commandBar.locked);
  el.commandBar.classList.toggle("is-live", !state.commandBar.locked);
  el.generatedCommandStatus.textContent = state.commandBar.locked ? "已锁定" : "实时预览";
  el.generatedCommandStatus.title = title;
  el.generatedCommandText.textContent = state.commandBar.command;
  el.generatedCommandText.title = state.commandBar.command;
  el.copyCommandBtn.disabled = !state.commandBar.command || el.commandBar.hidden;
  el.regenerateCommandBtn.textContent = state.commandBar.locked ? "重新生成" : "生成并锁定";
  el.regenerateCommandBtn.title = state.commandBar.locked
    ? "用当前选择重新生成并替换锁定命令"
    : "生成并锁定当前命令";
}

function commandContextForMode(mode) {
  return COMMAND_CONTEXT_LABELS[mode] ? mode : "preview";
}

function commandContextLabel(context) {
  return COMMAND_CONTEXT_LABELS[context] || COMMAND_CONTEXT_LABELS.preview;
}

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

function resetConsoleForExecution(scope) {
  clearConsole(scope);
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

function appendConsoleEntries(scope, entries) {
  if (!Array.isArray(entries) || entries.length === 0) {
    return;
  }
  const buffer = consoleBufferForScope(scope);
  buffer.lines.push(...entries);
  trimConsoleBuffer(buffer);
  if (scope === state.console.activeScope && shouldRenderConsoleBuffer()) {
    scheduleConsoleBufferRender();
  }
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

function setAllTreeGroupsCollapsed(collapsed) {
  if (!state.snapshot || !state.snapshot.tree) {
    return;
  }
  if (collapsed) {
    collectProjectDirectoryPaths(state.snapshot.tree)
      .filter(Boolean)
      .forEach((directory) => state.collapsedTreeDirs.add(directory));
  } else {
    state.collapsedTreeDirs.clear();
  }
  renderFileTree();
}

function collectProjectDirectoryPaths(node) {
  if (!node || node.type !== "directory") {
    return [];
  }
  return [
    node.path,
    ...(node.children || []).flatMap(collectProjectDirectoryPaths),
  ];
}

// Default project-tree state: expand only the project root, so the first
// level of children stays visible while every deeper directory starts
// collapsed. This keeps the per-interaction flatten cost bounded for large
// projects while still showing what users open a project to find.
function collapseTreeDirsBelowRoot() {
  state.collapsedTreeDirs.clear();
  if (!state.snapshot || !state.snapshot.tree) {
    return;
  }
  const root = state.snapshot.tree;
  if (!root || root.type !== "directory") {
    return;
  }
  // Root's own children are rendered because the root is not in the collapsed
  // set; we only need to fold the children that are themselves directories.
  (root.children || []).forEach((child) => {
    collectProjectDirectoryPaths(child)
      .filter(Boolean)
      .forEach((directory) => state.collapsedTreeDirs.add(directory));
  });
}

function ensureBuildCaseTreeExpanded() {
  if (!state.snapshot || !state.snapshot.suiteTree) {
    return;
  }
  collectSuiteDirectoryPaths(state.snapshot.suiteTree).forEach((nodePath) => {
    state.expandedSuiteNodes.add(nodePath);
  });
}

function ensureBuildCaseTreeRootExpanded() {
  if (!state.snapshot) {
    return;
  }
  const tree = state.snapshot.suiteTree || buildFlatSuiteTree(state.snapshot.suites || []);
  if (tree && tree.path) {
    state.expandedSuiteNodes.add(tree.path);
  }
}

function buildCaseTreeRenderSignature() {
  if (!state.snapshot) {
    return "empty";
  }
  const suiteKey = (state.snapshot.suites || [])
    .map((suite) => `${suite.id}:${suite.rootPath || ""}`)
    .join("|");
  const expandedKey = [...state.expandedSuiteNodes].sort().join("|");
  return [
    state.snapshot.project && state.snapshot.project.rootPath,
    suiteKey,
    state.buildCaseFilter,
    expandedKey,
  ].join("\n");
}

function invalidateBuildCaseTreeRender() {
  state.buildCaseTreeSignature = null;
}

function ensureBuildCaseTreeRendered() {
  const signature = buildCaseTreeRenderSignature();
  if (state.buildCaseTreeSignature === signature) {
    return;
  }
  renderBuildCaseTree();
}

function scheduleBuildCaseTreeRender() {
  invalidateBuildCaseTreeRender();
  if (state.buildCaseTreeRenderScheduled) {
    return;
  }
  state.buildCaseTreeRenderScheduled = true;
  const flush = () => {
    state.buildCaseTreeRenderRaf = null;
    state.buildCaseTreeRenderTimer = null;
    state.buildCaseTreeRenderScheduled = false;
    ensureBuildCaseTreeRendered();
  };
  if (typeof window.requestAnimationFrame === "function") {
    state.buildCaseTreeRenderRaf = window.requestAnimationFrame(flush);
  } else {
    state.buildCaseTreeRenderTimer = window.setTimeout(flush, 0);
  }
}

function setAllBuildCaseGroupsExpanded(expanded) {
  if (!state.snapshot || !state.snapshot.suiteTree) {
    return;
  }
  if (expanded) {
    ensureBuildCaseTreeExpanded();
  } else {
    collectSuiteDirectoryPaths(state.snapshot.suiteTree).forEach((nodePath) => {
      state.expandedSuiteNodes.delete(nodePath);
    });
  }
  invalidateBuildCaseTreeRender();
  ensureBuildCaseTreeRendered();
}

function collectSuiteDirectoryPaths(node) {
  if (!node || node.type === "file") {
    return [];
  }
  return [
    node.path,
    ...(node.children || []).flatMap(collectSuiteDirectoryPaths),
  ].filter(Boolean);
}

function renderSuiteOptions(suites, suiteTree = null) {
  const availableSuites = Array.isArray(suites) ? suites : [];
  const ids = availableSuites.map((suite) => suite.id);
  const previous = state.selectedSuiteIds.filter((id) => ids.includes(id));
  const previousBuild = state.selectedBuildSuiteIds.filter((id) => ids.includes(id));
  state.selectedSuiteIds = state.suiteSelectionTouched ? previous : ids;
  state.selectedBuildSuiteIds = state.buildSelectionTouched ? previousBuild : ids;
  updateSuiteSummary(availableSuites);
  renderDebugSuiteTree(availableSuites, suiteTree);
  if (state.activeView === "build") {
    invalidateBuildCaseTreeRender();
    ensureBuildCaseTreeRendered();
  } else {
    invalidateBuildCaseTreeRender();
  }
  previewCommand(currentCommand());
}

function renderDebugSuiteTree(suites = null, suiteTree = null) {
  const availableSuites = Array.isArray(suites)
    ? suites
    : (state.snapshot ? state.snapshot.suites || [] : []);
  const tree = suiteTree || (state.snapshot && state.snapshot.suiteTree) || buildFlatSuiteTree(availableSuites);
  el.suiteList.innerHTML =
    availableSuites.length === 0
      ? `<p class="empty">未找到 convention 测试套</p>`
      : renderSuiteTreeNode(tree, 0, "debug");
  bindSuiteTreeEvents(el.suiteList);
  syncSuiteTreeCheckboxStates("debug");
}

function renderBuildCaseTree() {
  const signature = buildCaseTreeRenderSignature();
  if (!state.snapshot) {
    el.buildCaseTree.innerHTML = `<p class="empty">打开项目后显示可构建案例</p>`;
    state.buildCaseTreeSignature = signature;
    return;
  }

  const suites = state.snapshot.suites || [];
  if (suites.length === 0) {
    el.buildCaseTree.innerHTML = `<p class="empty">未找到 convention 测试套</p>`;
    state.buildCaseTreeSignature = signature;
    return;
  }

  const tree = filteredSuiteTree(state.snapshot.suiteTree || buildFlatSuiteTree(suites), state.buildCaseFilter);
  if (!tree) {
    el.buildCaseTree.innerHTML = `<p class="empty">没有匹配的构建案例</p>`;
    state.buildCaseTreeSignature = signature;
    return;
  }

  const rows = flattenVisibleSuiteTreeRows(tree, "build");
  renderVirtualTreeRows(el.buildCaseTree, rows, renderSuiteTreeRow);
  syncSuiteTreeCheckboxStates("build");
  state.buildCaseTreeSignature = signature;
}

function bindSuiteTreeEvents(container) {
  return container;
}

function filteredSuiteTree(node, filter) {
  if (!node) {
    return null;
  }
  const query = String(filter || "").trim().toLowerCase();
  if (!query) {
    return node;
  }

  const label = [
    node.name,
    node.path,
    node.rootPath,
    node.filePath,
    node.suiteId,
  ].filter(Boolean).join(" ").toLowerCase();
  const children = (node.children || [])
    .map((child) => filteredSuiteTree(child, query))
    .filter(Boolean);
  if (label.includes(query) || children.length > 0) {
    return {
      ...node,
      children,
    };
  }
  return null;
}

function renderSuiteTreeNode(node, depth = 0, scope = "debug") {
  if (!node) {
    return "";
  }
  
  if (node.type === "file") {
    const isChecked = isFileSelected(node.suiteId, node.path, scope);
    const fileCheckedStr = isChecked ? " checked" : "";
    const fileIcon = node.fileType === "dsl" ? "DSL" : "PY";
    return `
      <div class="suite-node suite-file-node" style="--depth: ${depth}">
        <label class="suite-option is-file">
          <span class="suite-spacer"></span>
          <input type="checkbox" data-file-checkbox 
                 data-suite-scope="${escapeAttr(scope)}"
                 data-suite-id="${escapeAttr(node.suiteId || "")}" 
                 data-file-path="${escapeAttr(node.path || "")}"${fileCheckedStr}>
          <span class="file-icon">${fileIcon}</span>
          <span title="${escapeAttr(node.path)}">${escapeHtml(node.name)}</span>
        </label>
      </div>
    `;
  }

  const suiteId = node.suiteId;
  const suiteIds = collectSuiteNodeSuiteIds(node);
  const checked = suiteIds.length > 0 && suiteIds.every((id) => selectedSuiteIdsForScope(scope).includes(id))
    ? " checked"
    : "";
  const counts = `${node.dslCaseCount || 0} DSL / ${node.pythonTestCount || 0} py`;
  const label = suiteId === "__root__" ? "根目录" : node.name;
  
  const hasChildren = node.children && node.children.length > 0;
  const isExpanded = state.expandedSuiteNodes.has(node.path);
  
  const toggleArrow = hasChildren
    ? `<span class="suite-toggle ${isExpanded ? 'is-open' : ''}" data-suite-toggle="${escapeAttr(node.path)}">▶</span>`
    : `<span class="suite-spacer"></span>`;

  return `
    <div class="suite-node" style="--depth: ${depth}">
      <label class="suite-option${suiteId ? "" : " is-group"}">
        ${toggleArrow}
        ${suiteIds.length > 0
          ? `<input type="checkbox" data-suite-checkbox data-suite-scope="${escapeAttr(scope)}" data-suite-id="${escapeAttr(suiteId || "")}" data-suite-ids="${escapeAttr(JSON.stringify(suiteIds))}"${checked}>`
          : `<span class="suite-spacer"></span>`}
        <span title="${escapeAttr(node.rootPath || node.path || label)}">${escapeHtml(label)}</span>
        <small>${suiteId ? escapeHtml(counts) : ""}</small>
      </label>
      ${hasChildren ? `
        <div class="suite-children ${isExpanded ? '' : 'is-collapsed'}">
          ${isExpanded ? (node.children || []).map((child) => renderSuiteTreeNode(child, depth + 1, scope)).join("") : ""}
        </div>
      ` : ""}
    </div>
  `;
}

function flattenVisibleSuiteTreeRows(root, scope = "debug") {
  const rows = [];
  const visit = (node, depth) => {
    if (!node) {
      return;
    }
    rows.push({ node, depth, scope });
    if (node.type !== "file" && state.expandedSuiteNodes.has(node.path)) {
      (node.children || []).forEach((child) => visit(child, depth + 1));
    }
  };
  visit(root, 0);
  return rows;
}

function renderSuiteTreeRow(row) {
  const node = row && row.node;
  const depth = row ? row.depth : 0;
  const scope = row ? row.scope : "debug";
  if (!node) {
    return "";
  }

  if (node.type === "file") {
    const isChecked = isFileSelected(node.suiteId, node.path, scope);
    const fileCheckedStr = isChecked ? " checked" : "";
    const fileIcon = node.fileType === "dsl" ? "DSL" : "PY";
    return `
      <div class="suite-node suite-file-node" style="--depth: ${depth}">
        <label class="suite-option is-file">
          <span class="suite-spacer"></span>
          <input type="checkbox" data-file-checkbox
                 data-suite-scope="${escapeAttr(scope)}"
                 data-suite-id="${escapeAttr(node.suiteId || "")}"
                 data-file-path="${escapeAttr(node.path || "")}"${fileCheckedStr}>
          <span class="file-icon">${fileIcon}</span>
          <span title="${escapeAttr(node.path)}">${escapeHtml(node.name)}</span>
        </label>
      </div>
    `;
  }

  const suiteId = node.suiteId;
  const suiteIds = collectSuiteNodeSuiteIds(node);
  const checked = suiteIds.length > 0 && suiteIds.every((id) => selectedSuiteIdsForScope(scope).includes(id))
    ? " checked"
    : "";
  const counts = `${node.dslCaseCount || 0} DSL / ${node.pythonTestCount || 0} py`;
  const label = suiteId === "__root__" ? "根目录" : node.name;
  const hasChildren = node.children && node.children.length > 0;
  const isExpanded = state.expandedSuiteNodes.has(node.path);
  const toggleArrow = hasChildren
    ? `<span class="suite-toggle ${isExpanded ? "is-open" : ""}" data-suite-toggle="${escapeAttr(node.path)}">▶</span>`
    : `<span class="suite-spacer"></span>`;

  return `
    <div class="suite-node" style="--depth: ${depth}">
      <label class="suite-option${suiteId ? "" : " is-group"}">
        ${toggleArrow}
        ${suiteIds.length > 0
          ? `<input type="checkbox" data-suite-checkbox data-suite-scope="${escapeAttr(scope)}" data-suite-id="${escapeAttr(suiteId || "")}" data-suite-ids="${escapeAttr(JSON.stringify(suiteIds))}"${checked}>`
          : `<span class="suite-spacer"></span>`}
        <span title="${escapeAttr(node.rootPath || node.path || label)}">${escapeHtml(label)}</span>
        <small>${suiteId ? escapeHtml(counts) : ""}</small>
      </label>
    </div>
  `;
}

function buildFlatSuiteTree(suites) {
  return {
    type: "directory",
    path: "tests",
    name: "tests",
    suiteId: null,
    children: suites.map((suite) => ({
      ...suite,
      type: "directory",
      path: suite.id,
      suiteId: suite.id,
      children: [],
    })),
  };
}

function handleSuiteSelectionChange(event) {
  const input = event.currentTarget;
  const scope = input.dataset.suiteScope || "debug";
  markSuiteSelectionTouched(scope);
  const suiteIds = suiteIdsFromSuiteInput(input);
  const selected = new Set(selectedSuiteIdsForScope(scope));
  const overrides = selectedFileOverridesForScope(scope);

  suiteIds.forEach((suiteId) => {
    if (input.checked) {
      selected.add(suiteId);
    } else {
      selected.delete(suiteId);
    }
    delete overrides[suiteId];
  });

  setSelectedSuiteIdsForScope(scope, [...selected]);
  syncSuiteTreeCheckboxStates(scope);
  updateSuiteSummary(state.snapshot ? state.snapshot.suites || [] : []);
  updateBuildSummary();
  previewCommand(currentCommand(), { force: true });
}

function handleFileSelectionChange(event) {
  const input = event.currentTarget;
  const scope = input.dataset.suiteScope || "debug";
  markSuiteSelectionTouched(scope);
  const suiteId = input.dataset.suiteId;
  const filePath = input.dataset.filePath;
  const selectedSuiteIds = selectedSuiteIdsForScope(scope);
  const overrides = selectedFileOverridesForScope(scope);
  
  if (!overrides[suiteId]) {
    const isSuiteSelected = selectedSuiteIds.includes(suiteId);
    const files = getSuiteFiles(suiteId);
    if (isSuiteSelected) {
      overrides[suiteId] = new Set(files);
    } else {
      overrides[suiteId] = new Set();
    }
  }
  
  if (input.checked) {
    overrides[suiteId].add(filePath);
  } else {
    overrides[suiteId].delete(filePath);
  }
  
  syncSuiteCheckboxFromFiles(suiteId, scope);
  syncSuiteTreeCheckboxStates(scope);
  updateSuiteSummary(state.snapshot ? state.snapshot.suites || [] : []);
  updateBuildSummary();
  
  previewCommand(currentCommand(), { force: true });
}

function handleSuiteTreeChange(event) {
  const input = event.target && typeof event.target.closest === "function"
    ? event.target.closest("[data-suite-checkbox], [data-file-checkbox]")
    : null;
  if (!input || !event.currentTarget.contains(input)) {
    return;
  }
  if (input.hasAttribute("data-suite-checkbox")) {
    handleSuiteSelectionChange({ currentTarget: input });
    return;
  }
  handleFileSelectionChange({ currentTarget: input });
}

function handleSuiteTreeClick(event) {
  const toggle = event.target && typeof event.target.closest === "function"
    ? event.target.closest("[data-suite-toggle]")
    : null;
  if (!toggle || !event.currentTarget.contains(toggle)) {
    return;
  }
  event.stopPropagation();
  event.preventDefault();
  toggleSuiteTreeNode(toggle);
}

function handleSuiteToggleClick(event) {
  event.stopPropagation();
  event.preventDefault();
  toggleSuiteTreeNode(event.currentTarget);
}

function toggleSuiteTreeNode(toggle) {
  const path = toggle.dataset.suiteToggle;
  const scope = suiteScopeFromElement(toggle);
  if (!path) {
    return;
  }
  
  if (state.expandedSuiteNodes.has(path)) {
    state.expandedSuiteNodes.delete(path);
  } else {
    state.expandedSuiteNodes.add(path);
  }

  if (scope === "build") {
    invalidateBuildCaseTreeRender();
    ensureBuildCaseTreeRendered();
    return;
  }

  renderDebugSuiteTree();
}

function findSuiteTreeNodeByPath(root, targetPath) {
  if (!root) return null;
  if (root.path === targetPath) return root;
  for (const child of root.children || []) {
    const found = findSuiteTreeNodeByPath(child, targetPath);
    if (found) return found;
  }
  return null;
}


function syncSuiteCheckboxFromFiles(suiteId, scope = "debug") {
  const files = getSuiteFiles(suiteId);
  const selectedSuiteIds = selectedSuiteIdsForScope(scope);
  const overrides = selectedFileOverridesForScope(scope);
  const override = overrides[suiteId];
  
  if (override) {
    if (override.size === 0) {
      setSelectedSuiteIdsForScope(scope, selectedSuiteIds.filter((id) => id !== suiteId));
    } else {
      if (!selectedSuiteIds.includes(suiteId)) {
        setSelectedSuiteIdsForScope(scope, [...selectedSuiteIds, suiteId]);
      }
      if (override.size === files.length) {
        delete overrides[suiteId];
      }
    }
  }
}

function collectSuiteNodeSuiteIds(node) {
  if (!node || node.type === "file") {
    return [];
  }
  return [
    node.suiteId,
    ...(node.children || []).filter(c => c.type !== "file").flatMap(collectSuiteNodeSuiteIds),
  ].filter(Boolean);
}

function syncSuiteTreeCheckboxStates(scope = null) {
  suiteTreeContainers(scope).forEach((container) => {
    container.querySelectorAll("[data-file-checkbox]").forEach((input) => {
      const scope = input.dataset.suiteScope || "debug";
      const suiteId = input.dataset.suiteId;
      const filePath = input.dataset.filePath;
      input.checked = isFileSelected(suiteId, filePath, scope);
    });

    container.querySelectorAll("[data-suite-checkbox]").forEach((input) => {
      const scope = input.dataset.suiteScope || "debug";
      const suiteId = input.dataset.suiteId;
      const suiteIds = suiteIdsFromSuiteInput(input);
      const selectedSuiteIds = selectedSuiteIdsForScope(scope);
      const overrides = selectedFileOverridesForScope(scope);

      if (suiteIds.length === 0) {
        input.checked = false;
        input.indeterminate = false;
        return;
      }

      let totalFilesCount = 0;
      let selectedFilesCount = 0;
      let anySuiteChecked = false;
      let anySuiteUnchecked = false;
      let anySuitePartial = false;

      suiteIds.forEach((id) => {
        const isSuiteSelected = selectedSuiteIds.includes(id);
        const files = getSuiteFiles(id);

        if (files.length === 0) {
          if (isSuiteSelected) {
            anySuiteChecked = true;
          } else {
            anySuiteUnchecked = true;
          }
          return;
        }

        totalFilesCount += files.length;

        if (!isSuiteSelected) {
          anySuiteUnchecked = true;
          return;
        }

        const override = overrides[id];
        if (!override) {
          selectedFilesCount += files.length;
          anySuiteChecked = true;
        } else {
          selectedFilesCount += override.size;
          if (override.size === files.length) {
            anySuiteChecked = true;
          } else if (override.size === 0) {
            anySuiteUnchecked = true;
          } else {
            anySuitePartial = true;
          }
        }
      });

      let checked = false;
      let indeterminate = false;

      if (totalFilesCount > 0) {
        checked = (selectedFilesCount === totalFilesCount);
        indeterminate = (selectedFilesCount > 0 && selectedFilesCount < totalFilesCount);
      } else {
        checked = anySuiteChecked && !anySuiteUnchecked;
        indeterminate = anySuiteChecked && anySuiteUnchecked;
      }

      if (anySuitePartial) {
        indeterminate = true;
        checked = false;
      }

      input.checked = checked;
      input.indeterminate = indeterminate;
      input.closest(".suite-option")?.classList.toggle("is-partial", indeterminate);
    });
  });
}

function suiteTreeContainers(scope = null) {
  if (scope === "debug") {
    return [el.suiteList].filter(Boolean);
  }
  if (scope === "build") {
    return [el.buildCaseTree].filter(Boolean);
  }
  return [el.suiteList, el.buildCaseTree].filter(Boolean);
}

function suiteScopeFromElement(element) {
  const scopedElement = element && typeof element.closest === "function"
    ? element.closest("[data-suite-scope]")
    : null;
  if (scopedElement && scopedElement.dataset.suiteScope) {
    return scopedElement.dataset.suiteScope;
  }
  if (el.buildCaseTree && el.buildCaseTree.contains(element)) {
    return "build";
  }
  if (el.suiteList && el.suiteList.contains(element)) {
    return "debug";
  }
  return activeSuiteSelectionScope();
}

function activeSuiteSelectionScope() {
  return state.activeView === "build" ? "build" : "debug";
}

function selectedSuiteIdsForScope(scope = "debug") {
  return scope === "build" ? state.selectedBuildSuiteIds : state.selectedSuiteIds;
}

function setSelectedSuiteIdsForScope(scope, suiteIds) {
  if (scope === "build") {
    state.selectedBuildSuiteIds = normalizeSelectedSuiteIds(suiteIds);
    return;
  }
  state.selectedSuiteIds = normalizeSelectedSuiteIds(suiteIds);
}

function selectedFileOverridesForScope(scope = "debug") {
  return scope === "build" ? state.selectedBuildFileOverrides : state.selectedFileOverrides;
}

function markSuiteSelectionTouched(scope = "debug") {
  if (scope === "build") {
    state.buildSelectionTouched = true;
    return;
  }
  state.suiteSelectionTouched = true;
}

function suiteIdsFromSuiteInput(input) {
  try {
    const parsed = JSON.parse(input.dataset.suiteIds || "[]");
    return Array.isArray(parsed) ? parsed.filter(Boolean) : [];
  } catch (_error) {
    return [];
  }
}

function normalizeSelectedSuiteIds(suiteIds) {
  const selected = new Set(Array.isArray(suiteIds) ? suiteIds : []);
  return availableSuiteIds().filter((suiteId) => selected.has(suiteId));
}

function availableSuiteIds() {
  if (!state.snapshot || !Array.isArray(state.snapshot.suites)) {
    return [];
  }
  return state.snapshot.suites.map((suite) => suite.id);
}

function updateSuiteSummary(suites) {
  const total = Array.isArray(suites) ? suites.length : 0;
  const selected = currentSelectedSuiteIds("debug");
  if (total === 0) {
    el.suiteSummary.textContent = "无测试套";
    return;
  }
  if (selected.length === 0) {
    el.suiteSummary.textContent = "未选择测试套";
    return;
  }
  
  let hasOverride = false;
  let totalFiles = 0;
  let selectedFiles = 0;
  
  selected.forEach((suiteId) => {
    const files = getSuiteFiles(suiteId);
    totalFiles += files.length;
    
    const override = state.selectedFileOverrides[suiteId];
    if (override) {
      hasOverride = true;
      selectedFiles += override.size;
    } else {
      selectedFiles += files.length;
    }
  });
  
  if (selected.length === total) {
    if (!hasOverride) {
      el.suiteSummary.textContent = `全部测试套 (${total})`;
    } else {
      el.suiteSummary.textContent = `全部测试套 (${selectedFiles}/${totalFiles} 文件)`;
    }
    return;
  }
  
  if (selected.length === 1) {
    const suite = suites.find((item) => item.id === selected[0]);
    const name = suite ? suiteDisplayName(suite) : selected[0];
    const override = state.selectedFileOverrides[selected[0]];
    if (override) {
      const files = getSuiteFiles(selected[0]);
      el.suiteSummary.textContent = `${name} (${override.size}/${files.length} 文件)`;
    } else {
      el.suiteSummary.textContent = name;
    }
    return;
  }
  
  if (hasOverride) {
    el.suiteSummary.textContent = `${selected.length}/${total} 已选 · 部分文件`;
  } else {
    el.suiteSummary.textContent = `${selected.length}/${total} 已选`;
  }
}

function currentSelectedSuiteIds(scope = activeSuiteSelectionScope()) {
  if (!state.snapshot || !Array.isArray(state.snapshot.suites)) {
    return [];
  }
  const availableIds = state.snapshot.suites.map((suite) => suite.id);
  return selectedSuiteIdsForScope(scope).filter((id) => availableIds.includes(id));
}

function suiteCommandLabel(selectedSuiteIds, yamlVars, scope = "debug") {
  const selectedFiles = computeSelectedFiles(scope);
  const targets = selectedFiles ? selectedFiles : suiteTargetPathsForSelection(selectedSuiteIds);
  const suiteLabel = targets.length > 0
    ? targets.join(" ")
    : "<未选择测试套>";
  const args = yamlVars.length > 0
    ? ` ${yamlVars.map((item) => `--yaml-vars ${item}`).join(" ")}`
    : "";
  return `pytest ${suiteLabel}${args}`;
}

function buildCommandLabel(buildId = null) {
  const yamlVars = selectedConfigSources().map((source) => source.relativePath);
  const selectedFiles = computeSelectedFiles("build");
  const targets = selectedFiles ? selectedFiles : suiteTargetPathsForSelection(currentSelectedSuiteIds("build"));
  const targetLabel = targets.length > 0
    ? targets.join(" ")
    : "<未选择测试套>";
  const resultsDir = buildResultsDirForBuild(buildId || "<build-id>");
  const args = yamlVars.length > 0
    ? ` ${yamlVars.map((item) => `--yaml-vars ${item}`).join(" ")}`
    : "";
  return `pytest ${targetLabel} --alluredir ${resultsDir}${args}`;
}

function buildPytestArgsLabel(yamlVars, buildId = null) {
  const args = [
    "--alluredir",
    buildResultsDirForBuild(buildId || "<build-id>"),
    ...yamlVars.flatMap((item) => ["--yaml-vars", item]),
  ];
  return args.join(" ");
}

function activeBuildCommandId() {
  return state.currentTaskMode === "build" ? state.currentBuildId : null;
}

function buildResultsDirForBuild(buildId) {
  return `.pytest-dsl-gui/builds/${buildId}/allure-results`;
}

function suiteBuildScopeLabel(selectedSuiteIds, scope = "build") {
  const selectedFiles = computeSelectedFiles(scope);
  if (selectedFiles && selectedFiles.length > 0) {
    return `${selectedFiles.length} 文件`;
  }
  const targets = suiteTargetPathsForSelection(selectedSuiteIds);
  return targets.length > 0 ? targets.join(" ") : "未选择测试套";
}

function computeSelectedFiles(scope = activeSuiteSelectionScope()) {
  const selectedFiles = [];
  const selectedSuiteIds = currentSelectedSuiteIds(scope);
  const overrides = selectedFileOverridesForScope(scope);
  let hasOverride = false;
  
  selectedSuiteIds.forEach((suiteId) => {
    const override = overrides[suiteId];
    if (override) {
      hasOverride = true;
      override.forEach((file) => {
        selectedFiles.push(file);
      });
    } else {
      const files = getSuiteFiles(suiteId);
      files.forEach((file) => {
        selectedFiles.push(file);
      });
    }
  });
  
  return hasOverride ? selectedFiles : null;
}

function isFileSelected(suiteId, filePath, scope = "debug") {
  const isSuiteSelected = selectedSuiteIdsForScope(scope).includes(suiteId);
  if (!isSuiteSelected) {
    return false;
  }
  const override = selectedFileOverridesForScope(scope)[suiteId];
  if (!override) {
    return true;
  }
  return override.has(filePath);
}

function getSuiteFiles(suiteId) {
  if (!state.snapshot || !Array.isArray(state.snapshot.suites)) {
    return [];
  }
  const suite = state.snapshot.suites.find((s) => s.id === suiteId);
  if (!suite) {
    return [];
  }
  return (suite.dslCaseFiles || []).concat(suite.pythonTestFiles || []);
}

function suiteTargetPathsForSelection(selectedSuiteIds) {
  const selected = Array.isArray(selectedSuiteIds) ? selectedSuiteIds : [];
  if (selected.length === 0) {
    return [];
  }
  if (selected.includes("all")) {
    return ["tests"];
  }
  if (!state.snapshot || !Array.isArray(state.snapshot.suites)) {
    return selected;
  }

  const suitesById = new Map(state.snapshot.suites.map((suite) => [suite.id, suite]));
  const targets = selected
    .map((suiteId) => suitesById.get(suiteId))
    .filter(Boolean)
    .map((suite) => suite.rootPath || suite.id)
    .filter(Boolean);
  return compactRelativeTargets(targets);
}

function compactRelativeTargets(paths) {
  const unique = [...new Set(paths.map((item) => String(item || "").replace(/\\/g, "/")).filter(Boolean))]
    .sort((left, right) => {
      const depthDiff = left.split("/").length - right.split("/").length;
      return depthDiff || left.localeCompare(right);
    });
  const compacted = [];
  unique.forEach((target) => {
    if (!compacted.some((selected) => target === selected || target.startsWith(`${selected}/`))) {
      compacted.push(target);
    }
  });
  return compacted;
}

function suiteDisplayName(suite) {
  if (!suite) {
    return "";
  }
  return suite.id === "__root__" ? "根目录 (__root__)" : suite.name || suite.id;
}

function groupFilesByDirectory(files) {
  const byDirectory = new Map();
  files.forEach((file) => {
    const directory = file.directory || ".";
    if (!byDirectory.has(directory)) {
      byDirectory.set(directory, []);
    }
    byDirectory.get(directory).push(file);
  });
  return Array.from(byDirectory.entries()).map(([name, groupFiles]) => ({
    name,
    files: groupFiles,
  }));
}

function countLines(content) {
  if (!content) {
    return 0;
  }
  return content.endsWith("\n")
    ? content.split("\n").length - 1
    : content.split("\n").length;
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

function fileNameFromPath(filePath) {
  const parts = String(filePath || "").split(/[\\/]/);
  return parts[parts.length - 1] || "source";
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

function errorMessage(error) {
  return error && error.message ? error.message : String(error);
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value);
}

function cssEscape(value) {
  if (window.CSS && typeof window.CSS.escape === "function") {
    return window.CSS.escape(String(value || ""));
  }
  return String(value || "").replace(/["\\]/g, "\\$&");
}
