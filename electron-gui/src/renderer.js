const api = window.pytestDslGui;

const state = {
  snapshot: null,
  currentFile: null,
  dirty: false,
  filter: "",
  selectedConfigPaths: [],
  configSignature: null,
  remoteStatus: emptyRemoteStatus(),
  remoteProbeSeq: 0,
  remoteMonitorTimer: null,
  remoteMonitorRunning: false,
  currentTaskId: null,
  currentTaskMode: null,
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
};

const REMOTE_MONITOR_INTERVAL_MS = 5000;
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

const el = {};

document.addEventListener("DOMContentLoaded", () => {
  cacheElements();
  initializeLayoutSizing();
  bindEvents();
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
  setEmptyProjectState();
  appendLog("info", "Electron GUI initialized");
  appendLog("info", "请选择要打开的 pytest-dsl 项目");
});

function cacheElements() {
  [
    "projectName",
    "projectRoot",
    "suiteDirectory",
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
    "expandAllBtn",
    "collapseAllBtn",
    "branchName",
    "fileFilter",
    "fileTree",
    "dirtyDot",
    "activeTab",
    "fileTitle",
    "filePath",
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
    "keywordPanel",
    "keywordSearch",
    "keywordStatus",
    "keywordList",
    "codeEditor",
    "editorMeta",
    "problemCount",
    "variableCount",
    "commandPreview",
    "consoleBody",
    "configCount",
    "configList",
    "configMerged",
    "metadataList",
    "deductionList",
    "workspaceStatus",
    "gitStatus",
    "remoteStatusBar",
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
  el.nextStepBtn.addEventListener("click", () => sendDebugCommand("next"));
  el.continueDebugBtn.addEventListener("click", () => sendDebugCommand("continue"));
  el.stopBtn.addEventListener("click", stopCurrentTask);
  el.runAllBtn.addEventListener("click", previewRunSuite);
  el.expandAllBtn.addEventListener("click", () =>
    setAllTreeGroupsCollapsed(false),
  );
  el.collapseAllBtn.addEventListener("click", () =>
    setAllTreeGroupsCollapsed(true),
  );
  el.settingsBtn.addEventListener("click", () =>
    appendLog("info", "Settings shell is not implemented in this MVP"),
  );
  el.keywordBtn.addEventListener("click", () =>
    toggleKeywordPanel(),
  );
  el.commandBtn.addEventListener("click", () =>
    generateCurrentCommand(),
  );
  el.keywordSearch.addEventListener("input", handleKeywordSearchInput);
  el.configTrigger.addEventListener("click", () => {
    el.configPicker.classList.toggle("is-open");
    el.configTrigger.setAttribute(
      "aria-expanded",
      String(el.configPicker.classList.contains("is-open")),
    );
  });
  el.fileFilter.addEventListener("input", () => {
    state.filter = el.fileFilter.value.trim().toLowerCase();
    renderFileTree();
  });
  if (typeof api.onExecutionEvent === "function") {
    api.onExecutionEvent(handleExecutionEvent);
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
  const config = LAYOUT_SIZES[kind];
  const startPosition = config.axis === "y" ? event.clientY : event.clientX;
  const startSize = getLayoutSize(kind);
  document.body.classList.add(
    config.axis === "y" ? "is-resizing-console" : "is-resizing-layout",
  );

  const handlePointerMove = (moveEvent) => {
    const currentPosition = config.axis === "y"
      ? moveEvent.clientY
      : moveEvent.clientX;
    const delta = currentPosition - startPosition;
    const nextSize = config.axis === "y"
      ? startSize - delta
      : startSize + delta;
    setLayoutSize(kind, nextSize);
  };

  const stopResize = () => {
    document.body.classList.remove("is-resizing-layout", "is-resizing-console");
    document.removeEventListener("pointermove", handlePointerMove);
  };

  document.addEventListener("pointermove", handlePointerMove);
  document.addEventListener("pointerup", stopResize, { once: true });
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

async function refreshProject() {
  if (!state.snapshot) {
    appendLog("warn", "请先打开一个项目");
    return;
  }

  try {
    const snapshot = await api.scanProject(state.snapshot.project.rootPath);
    applySnapshot(snapshot, "Refreshed project", state.currentFile);
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
  state.configSignature = null;
  state.remoteStatus = emptyRemoteStatus();
  state.currentTaskId = null;
  state.currentTaskMode = null;
  state.currentDebugLine = null;
  state.debugStartLine = null;
  state.debugPaused = false;
  state.debugSelection = null;
  state.readonlySource = null;
  resetKeywordBrowser();
  el.projectName.textContent = "pytest-dsl Local Workbench";
  el.projectRoot.textContent = "选择一个外部项目开始";
  el.branchName.textContent = "local";
  el.gitStatus.textContent = "local";
  el.workspaceStatus.textContent = "未打开项目";
  el.configCount.textContent = "0";
  el.configSummary.textContent = "未加载配置";
  renderRemoteStatus();
  el.suiteDirectory.innerHTML = `<option value=".">.</option>`;
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
  renderSuiteOptions(snapshot.dslFiles);
}

function renderFileTree() {
  if (!state.snapshot) {
    return;
  }

  const files = getEditableFiles().filter((file) => {
    if (!state.filter) {
      return true;
    }
    return file.relativePath.toLowerCase().includes(state.filter);
  });

  if (files.length === 0) {
    el.fileTree.innerHTML = `<p class="empty">${state.filter ? "没有匹配的文件" : "项目中没有可编辑文本文件"}</p>`;
    return;
  }

  const groups = groupFilesByDirectory(files);
  const rootFiles = (groups.find((group) => group.name === ".") || { files: [] }).files;
  const directoryGroups = groups.filter((group) => group.name !== ".");
  el.fileTree.innerHTML = [
    ...rootFiles.map(renderFileRow),
    ...directoryGroups.map(renderDirectoryGroup),
  ].join("");

  el.fileTree.querySelectorAll(".tree-folder-row").forEach((button) => {
    button.addEventListener("click", () => {
      button.closest(".tree-group").classList.toggle("is-collapsed");
    });
  });

  el.fileTree.querySelectorAll(".tree-row[data-path]").forEach((button) => {
    button.addEventListener("click", () => {
      if (
        state.dirty &&
        !window.confirm("当前文件尚未保存，是否继续打开其他文件？")
      ) {
        return;
      }
      selectFile(button.dataset.path);
    });
  });
}

function renderDirectoryGroup(group) {
  return `
    <div class="tree-group">
      <button class="tree-row tree-folder-row" type="button" data-directory="${escapeAttr(group.name)}">
        <span class="folderIcon" aria-hidden="true">
          <span class="folder-open">${folderIcon("open")}</span>
          <span class="folder-closed">${folderIcon("closed")}</span>
        </span>
        <span class="name">${escapeHtml(group.name)}</span>
        <span class="count">${group.files.length}</span>
      </button>
      <div class="tree-children">
        ${group.files.map(renderFileRow).join("")}
      </div>
    </div>
  `;
}

function renderFileRow(file) {
  return `
    <button class="tree-row${file.relativePath === state.currentFile ? " is-selected" : ""}" type="button" data-path="${escapeAttr(file.relativePath)}">
      <span class="fileIcon ${fileKind(file)}" aria-hidden="true">${fileIcon(file)}</span>
      <span class="name" title="${escapeAttr(file.relativePath)}">${escapeHtml(file.name)}</span>
      <span class="count">${file.lineCount}</span>
    </button>
  `;
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
  updateCommandPreview(currentCommand());
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
  const runnableWholeFile = hasFile && !readonlySource && isRunnableWholeFile(state.currentFile);
  const selection = executable ? CM6.getSelection() : null;
  const hasSelection = Boolean(selection);
  const hasDebugStart = executable && Boolean(state.debugStartLine);
  const isRunning = Boolean(state.currentTaskId);
  const isDebugRunning = isRunning && state.currentTaskMode === "debug";
  const canRun = executable && (runnableWholeFile || hasSelection);
  const canDebug = executable && (runnableWholeFile || hasSelection || hasDebugStart);

  el.executionActionGroup.hidden = !executable;
  el.debugSessionGroup.hidden = !isRunning;
  el.saveBtn.disabled = !hasFile || readonlySource;
  el.keywordBtn.disabled = !executable || isRunning;
  el.syntaxBtn.disabled = !executable || isRunning;
  el.runBtn.disabled = !canRun || isRunning;
  el.debugStepsBtn.disabled = !canDebug || isRunning;
  el.nextStepBtn.disabled = !isDebugRunning || !state.debugPaused;
  el.continueDebugBtn.disabled = !isDebugRunning || !state.debugPaused;
  el.stopBtn.disabled = !isRunning;
  if (!executable && state.keywordPanelOpen) {
    closeKeywordPanel();
  }
  updateExecutionActionLabels(selection);
  if (!isRunning) {
    updateCommandPreview(currentCommand());
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
  renderConfig();
  renderProject();
  refreshRemoteStatuses();
  if (state.currentFile) {
    renderActiveFile();
  } else {
    updateCommandPreview(currentCommand());
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
    updateCommandPreview(currentCommand());
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
  if (!state.currentFile || !isExecutableFile(state.currentFile)) {
    appendLog("warn", "当前文件不支持关键字插入");
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
  el.keywordList.querySelectorAll(".keyword-row[data-index]").forEach((button) => {
    button.addEventListener("click", () => {
      insertKeyword(Number(button.dataset.index));
    });
  });
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
  const snippet = buildKeywordSnippet(keyword);
  CM6.insertText(snippet);
  appendLog("info", `Inserted keyword: ${keyword.name}`);
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

async function generateCurrentCommand() {
  const command = currentCommand();
  updateCommandPreview(command);
  appendLog("info", `Generated command: ${command}`);

  if (typeof api.copyText !== "function") {
    return command;
  }

  try {
    await api.copyText(command);
    appendLog("pass", "Command copied to clipboard");
  } catch (error) {
    appendLog("warn", `Copy command failed: ${errorMessage(error)}`);
  }

  return command;
}

async function saveCurrentFile() {
  if (!state.snapshot || !state.currentFile) {
    appendLog("warn", "No file selected");
    return;
  }
  if (state.readonlySource) {
    appendLog("warn", "只读源码不能保存");
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
    setDirty(false);
    renderMetadata(state.snapshot.metadata);
    appendLog("pass", `Saved ${result.relativePath} (${result.bytes} bytes)`);
  } catch (error) {
    appendLog("error", errorMessage(error));
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
  setRunningState(true, taskId, mode);
  updateCommandPreview(command);
  appendLog("info", `${executionModeLabel(mode)} started: ${sourceLabel}`);

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
    appendLog("error", errorMessage(error));
    if (state.currentTaskId === taskId) {
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
  updateCommandPreview(currentCommand());
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

function previewRunSuite() {
  if (!state.snapshot) {
    appendLog("warn", "No project loaded");
    return;
  }
  const suite = el.suiteDirectory.value || ".";
  const command = `pytest-dsl ${suite} ${configArgs()}`;
  updateCommandPreview(command);
  appendLog("info", `Run suite preview: ${command}`);
}

async function stopCurrentTask() {
  if (!state.currentTaskId) {
    appendLog("warn", "没有正在运行的任务");
    return;
  }

  const taskId = state.currentTaskId;
  appendLog("warn", `Stop requested: ${taskId}`);
  try {
    const result = await api.stopExecution(taskId);
    if (!result || !result.stopped) {
      appendLog("warn", "任务已经结束或不存在");
    }
  } catch (error) {
    appendLog("error", errorMessage(error));
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
      appendLog("warn", `调试指令未发送: ${command}`);
      state.debugPaused = Boolean(state.currentTaskId);
      updateFileActionState();
      return;
    }
    appendLog("info", `Debug command: ${command}`);
  } catch (error) {
    appendLog("error", errorMessage(error));
    state.debugPaused = Boolean(state.currentTaskId);
    updateFileActionState();
  }
}

function handleExecutionEvent(event) {
  if (!event || event.taskId !== state.currentTaskId) {
    return;
  }

  if (event.type === "started") {
    updateCommandPreview(event.command || currentCommand());
    return;
  }

  if (event.type === "stdout" || event.type === "stderr") {
    appendProcessOutput(event.type === "stderr" ? "error" : "info", event.text);
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
    );
    setRunningState(false);
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
    );
    return;
  }

  if (event.phase === "finish") {
    const level = event.status === "failed" ? "error" : "pass";
    appendLog(
      level,
      `Step ${event.status || "done"} line ${event.line || "?"}${event.error ? `: ${event.error}` : ""}`,
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
}

function appendProcessOutput(level, text) {
  String(text || "")
    .replace(/\r\n/g, "\n")
    .split("\n")
    .filter((line) => line.length > 0)
    .forEach((line) => appendLog(level, line));
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
  };
  return labels[mode] || "执行";
}

function currentCommand() {
  if (!state.currentFile || !isExecutableFile(state.currentFile)) {
    return `pytest-dsl ${el.suiteDirectory.value || "."} ${configArgs()}`;
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
  updateCommandPreview("pytest-dsl");
  updateFileActionState();
}

function setDirty(isDirty) {
  state.dirty = isDirty;
  el.dirtyDot.classList.toggle("is-dirty", isDirty);
  if (state.currentFile) {
    renderActiveFile();
  }
}

function updateCommandPreview(command) {
  el.commandPreview.textContent = command.replace(/\s+/g, " ").trim();
}

function appendLog(level, message) {
  const row = document.createElement("div");
  const now = new Date();
  row.className = "log-line";
  row.innerHTML = `
    <span class="log-time">${now.toTimeString().slice(0, 8)}</span>
    <span class="log-level ${level}">${level.toUpperCase()}</span>
    <span>${escapeHtml(message)}</span>
  `;
  el.consoleBody.appendChild(row);
  el.consoleBody.scrollTop = el.consoleBody.scrollHeight;
}

function setAllTreeGroupsCollapsed(collapsed) {
  el.fileTree.querySelectorAll(".tree-group").forEach((group) => {
    group.classList.toggle("is-collapsed", collapsed);
  });
}

function renderSuiteOptions(files) {
  const directories = Array.from(
    new Set(files.map((file) => file.directory || ".")),
  ).sort((left, right) => left.localeCompare(right));
  const preferred = el.suiteDirectory.value;
  el.suiteDirectory.innerHTML =
    directories.length === 0
      ? `<option value=".">.</option>`
      : directories
          .map(
            (directory) =>
              `<option value="${escapeAttr(directory)}">${escapeHtml(directory)}</option>`,
          )
          .join("");
  if (directories.includes(preferred)) {
    el.suiteDirectory.value = preferred;
  }
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
  const language = file.language || detectLanguage(file.relativePath || file.name);
  const name = file.name.toLowerCase();
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
