const api = window.pytestDslGui;

const state = {
  snapshot: null,
  currentFile: null,
  dirty: false,
  filter: "",
  selectedConfigPaths: [],
  selectedSuiteIds: [],
  suiteSelectionTouched: false,
  selectedTreePath: "",
  selectedTreeKind: "directory",
  collapsedTreeDirs: new Set(),
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
  consoleLines: [],
  commandOutputChunks: [],
  console: {
    wrap: true,
    expanded: false,
  },
  commandPreview: {
    command: "pytest-dsl",
    context: "preview",
    persistent: false,
    taskId: null,
  },
  treeContext: null,
  draggedTreeFile: null,
  treeDropTargetPath: null,
  entryDialogResolve: null,
  entryDialogPreviousFocus: null,
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

const COMMAND_CONTEXT_LABELS = {
  preview: "当前命令",
  syntax: "语法检查",
  run: "文件运行",
  debug: "调试",
  suite: "测试套运行",
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
  setEmptyProjectState();
  appendLog("info", "Electron GUI initialized");
  appendLog("info", "请选择要打开的 pytest-dsl 项目");
});

function cacheElements() {
  [
    "projectName",
    "projectRoot",
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
    "treeRefreshBtn",
    "expandAllBtn",
    "collapseAllBtn",
    "branchName",
    "fileFilter",
    "fileTree",
    "treeContextMenu",
    "dirtyDot",
    "activeTab",
    "fileTitle",
    "filePath",
    "mainStage",
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
    "commandContext",
    "commandPreview",
    "bottomConsole",
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
  el.nextStepBtn.addEventListener("click", () => sendDebugCommand("next"));
  el.continueDebugBtn.addEventListener("click", () => sendDebugCommand("continue"));
  el.stopBtn.addEventListener("click", stopCurrentTask);
  el.runAllBtn.addEventListener("click", runSuiteExecution);
  el.copyConsoleBtn.addEventListener("click", copyConsoleOutput);
  el.wrapConsoleBtn.addEventListener("click", toggleConsoleWrap);
  el.expandConsoleBtn.addEventListener("click", toggleConsoleExpanded);
  el.clearConsoleBtn.addEventListener("click", () => clearConsole());
  el.treeRefreshBtn.addEventListener("click", () =>
    refreshProject({ logMessage: "Refreshed project tree" }),
  );
  el.fileTree.addEventListener("contextmenu", handleFileTreeContextMenu);
  el.fileTree.addEventListener("scroll", closeTreeContextMenu);
  el.fileTree.addEventListener("dragstart", handleTreeDragStart);
  el.fileTree.addEventListener("dragend", handleTreeDragEnd);
  el.fileTree.addEventListener("dragover", handleTreeDragOver);
  el.fileTree.addEventListener("dragleave", handleTreeDragLeave);
  el.fileTree.addEventListener("drop", handleTreeDrop);
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
  document.addEventListener("click", (event) => {
    if (!el.treeContextMenu.contains(event.target)) {
      closeTreeContextMenu();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeTreeContextMenu();
    }
  });
  el.suiteTrigger.addEventListener("click", () => {
    el.suitePicker.classList.toggle("is-open");
    el.suiteTrigger.setAttribute(
      "aria-expanded",
      String(el.suitePicker.classList.contains("is-open")),
    );
  });
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
    state.suiteSelectionTouched = false;
    state.selectedTreePath = "";
    state.selectedTreeKind = "directory";
    state.collapsedTreeDirs.clear();
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
  state.suiteSelectionTouched = false;
  state.selectedTreePath = "";
  state.selectedTreeKind = "directory";
  state.collapsedTreeDirs.clear();
  closeTreeContextMenu();
  closeEntryDialog(null);
  clearTreeDragState();
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
  el.suiteSummary.textContent = "打开项目后自动识别";
  el.suiteList.innerHTML = `<p class="empty">打开项目后显示 convention 测试套</p>`;
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
}

function renderFileTree() {
  if (!state.snapshot) {
    return;
  }

  const tree = filterProjectTree(state.snapshot.tree, state.filter);
  const children = tree && Array.isArray(tree.children) ? tree.children : [];
  if (children.length === 0) {
    el.fileTree.innerHTML = `<p class="empty">${state.filter ? "没有匹配的文件或目录" : "项目中没有可编辑文本文件"}</p>`;
    return;
  }

  el.fileTree.innerHTML = children
    .map((node) => renderProjectTreeNode(node, 0))
    .join("");

  el.fileTree.querySelectorAll("[data-tree-action]").forEach((button) => {
    button.addEventListener("click", handleTreeAction);
  });
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
  el.keywordBtn.disabled = !hasFile || readonlySource || !isExecutableFile(state.currentFile);
  el.commandBtn.disabled = false;
  el.syntaxBtn.disabled = !executable || isRunning;
  el.runBtn.disabled = !canRun || isRunning;
  el.debugStepsBtn.disabled = !canDebug || isRunning;
  el.nextStepBtn.disabled = !isDebugRunning || !state.debugPaused;
  el.continueDebugBtn.disabled = !isDebugRunning || !state.debugPaused;
  el.stopBtn.disabled = !isRunning;
  if (el.keywordBtn.disabled && state.keywordPanelOpen) {
    closeKeywordPanel();
  }
  updateExecutionActionLabels(selection);
  previewCommand(currentCommand());
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

async function generateCurrentCommand() {
  const command = currentCommand();
  previewCommand(command, { force: true });
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
  resetConsoleForExecution();
  setRunningState(true, taskId, mode);
  setExecutionCommand(command, { mode, taskId });
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

  const selectedSuiteIds = currentSelectedSuiteIds();
  if (selectedSuiteIds.length === 0) {
    appendLog("warn", "没有可运行的测试套");
    return;
  }
  const yamlVars = selectedConfigSources().map((source) => source.relativePath);
  const taskId = createTaskId("suite");
  const command = suiteCommandLabel(selectedSuiteIds, yamlVars);
  resetConsoleForExecution();
  setRunningState(true, taskId, "suite");
  setExecutionCommand(command, { mode: "suite", taskId });
  appendLog("info", `测试套运行 started: ${selectedSuiteIds.join(", ")}`);

  try {
    await api.startExecution({
      taskId,
      mode: "suite",
      projectRoot: state.snapshot.project.rootPath,
      selectedSuiteIds,
      yamlVars,
    });
  } catch (error) {
    appendLog("error", errorMessage(error));
    if (state.currentTaskId === taskId) {
      releaseExecutionCommand(taskId);
      setRunningState(false);
    }
  }
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
    updateCommandPreview(event.command || currentCommand(), {
      context: commandContextForMode(event.mode),
      persistent: true,
      taskId: event.taskId,
    });
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
    releaseExecutionCommand(event.taskId);
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
  state.commandOutputChunks.push(String(text || ""));
  String(text || "")
    .replace(/\r\n/g, "\n")
    .split("\n")
    .filter((line) => line.length > 0)
    .forEach((line) => appendLog(level, line));
}

function resetConsoleForExecution() {
  clearConsole();
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
  };
  return labels[mode] || "执行";
}

function currentCommand() {
  if (!state.snapshot) {
    return "pytest-dsl";
  }
  if (!state.currentFile || !isExecutableFile(state.currentFile)) {
    return suiteCommandLabel(currentSelectedSuiteIds(), selectedConfigSources().map((source) => source.relativePath));
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
  if (state.currentTaskId || state.commandPreview.taskId) {
    return state.commandPreview.command;
  }
  if (state.commandPreview.persistent && !options.force) {
    return state.commandPreview.command;
  }
  return updateCommandPreview(command, {
    context: "preview",
    persistent: false,
    taskId: null,
  });
}

function setExecutionCommand(command, options = {}) {
  return updateCommandPreview(command, {
    context: commandContextForMode(options.mode),
    persistent: true,
    taskId: options.taskId || null,
  });
}

function releaseExecutionCommand(taskId) {
  if (
    taskId &&
    state.commandPreview.taskId &&
    state.commandPreview.taskId !== taskId
  ) {
    return state.commandPreview.command;
  }
  state.commandPreview.taskId = null;
  state.commandPreview.persistent = true;
  return state.commandPreview.command;
}

function resetCommandPreview(command = "pytest-dsl") {
  return updateCommandPreview(command, {
    context: "preview",
    persistent: false,
    taskId: null,
  });
}

function updateCommandPreview(command, options = {}) {
  const normalized = String(command || "pytest-dsl").replace(/\s+/g, " ").trim() || "pytest-dsl";
  state.commandPreview.command = normalized;
  state.commandPreview.context = options.context || state.commandPreview.context || "preview";
  state.commandPreview.persistent = Boolean(options.persistent);
  state.commandPreview.taskId = options.taskId || null;

  const label = commandContextLabel(state.commandPreview.context);
  el.commandContext.textContent = label;
  el.commandContext.title = label;
  el.commandPreview.textContent = normalized;
  el.commandPreview.title = normalized;
  return normalized;
}

function commandContextForMode(mode) {
  return COMMAND_CONTEXT_LABELS[mode] ? mode : "preview";
}

function commandContextLabel(context) {
  return COMMAND_CONTEXT_LABELS[context] || COMMAND_CONTEXT_LABELS.preview;
}

function appendLog(level, message) {
  const row = document.createElement("div");
  const now = new Date();
  const timestamp = now.toTimeString().slice(0, 8);
  const normalizedMessage = String(message ?? "");
  state.consoleLines.push(`[${timestamp}] ${level.toUpperCase()} ${normalizedMessage}`);
  row.className = "log-line";
  row.innerHTML = `
    <span class="log-time">${timestamp}</span>
    <span class="log-level ${level}">${level.toUpperCase()}</span>
    <span class="log-message">${escapeHtml(normalizedMessage)}</span>
  `;
  el.consoleBody.appendChild(row);
  el.consoleBody.scrollTop = el.consoleBody.scrollHeight;
}

function clearConsole() {
  state.consoleLines = [];
  state.commandOutputChunks = [];
  el.consoleBody.textContent = "";
}

async function copyConsoleOutput() {
  const text = state.commandOutputChunks.join("");
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
  state.console.wrap = !state.console.wrap;
  applyConsoleViewState();
}

function toggleConsoleExpanded() {
  state.console.expanded = !state.console.expanded;
  applyConsoleViewState();
}

function applyConsoleViewState() {
  if (el.bottomConsole) {
    el.bottomConsole.classList.toggle("is-unwrapped", !state.console.wrap);
  }
  if (el.mainStage) {
    el.mainStage.classList.toggle("is-console-expanded", state.console.expanded);
  }
  if (el.wrapConsoleBtn) {
    el.wrapConsoleBtn.textContent = state.console.wrap ? "不换行" : "自动换行";
    el.wrapConsoleBtn.title = state.console.wrap
      ? "长输出改为横向滚动"
      : "长输出改为自动换行";
    el.wrapConsoleBtn.setAttribute("aria-pressed", String(!state.console.wrap));
  }
  if (el.expandConsoleBtn) {
    el.expandConsoleBtn.textContent = state.console.expanded ? "还原" : "展开";
    el.expandConsoleBtn.title = state.console.expanded
      ? "还原运行输出高度"
      : "展开运行输出";
    el.expandConsoleBtn.setAttribute("aria-pressed", String(state.console.expanded));
  }
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

function renderSuiteOptions(suites, suiteTree = null) {
  const availableSuites = Array.isArray(suites) ? suites : [];
  const ids = availableSuites.map((suite) => suite.id);
  const previous = state.selectedSuiteIds.filter((id) => ids.includes(id));
  state.selectedSuiteIds = state.suiteSelectionTouched ? previous : ids;
  updateSuiteSummary(availableSuites);
  el.suiteList.innerHTML =
    availableSuites.length === 0
      ? `<p class="empty">未找到 convention 测试套</p>`
      : renderSuiteTreeNode(suiteTree || buildFlatSuiteTree(availableSuites), 0);
  el.suiteList.querySelectorAll("[data-suite-checkbox]").forEach((input) => {
    input.addEventListener("change", handleSuiteSelectionChange);
  });
  syncSuiteTreeCheckboxStates();
  previewCommand(currentCommand());
}

function renderSuiteTreeNode(node, depth = 0) {
  if (!node) {
    return "";
  }
  const suiteId = node.suiteId;
  const suiteIds = collectSuiteNodeSuiteIds(node);
  const checked = suiteIds.length > 0 && suiteIds.every((id) => state.selectedSuiteIds.includes(id))
    ? " checked"
    : "";
  const counts = `${node.dslCaseCount || 0} DSL / ${node.pythonTestCount || 0} py`;
  const label = suiteId === "__root__" ? "根目录 (__root__)" : node.name;
  return `
    <div class="suite-node" style="--depth: ${depth}">
      <label class="suite-option${suiteId ? "" : " is-group"}">
        ${suiteIds.length > 0
          ? `<input type="checkbox" data-suite-checkbox data-suite-id="${escapeAttr(suiteId || "")}" data-suite-ids="${escapeAttr(JSON.stringify(suiteIds))}"${checked}>`
          : `<span class="suite-spacer"></span>`}
        <span title="${escapeAttr(node.rootPath || node.path || label)}">${escapeHtml(label)}</span>
        <small>${suiteId ? escapeHtml(counts) : ""}</small>
      </label>
      <div class="suite-children">
        ${(node.children || []).map((child) => renderSuiteTreeNode(child, depth + 1)).join("")}
      </div>
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
  state.suiteSelectionTouched = true;
  const input = event.currentTarget;
  const suiteIds = suiteIdsFromSuiteInput(input);
  const selected = new Set(state.selectedSuiteIds);

  suiteIds.forEach((suiteId) => {
    if (input.checked) {
      selected.add(suiteId);
    } else {
      selected.delete(suiteId);
    }
  });

  state.selectedSuiteIds = normalizeSelectedSuiteIds([...selected]);
  syncSuiteTreeCheckboxStates();
  updateSuiteSummary(state.snapshot ? state.snapshot.suites || [] : []);
  previewCommand(
    suiteCommandLabel(state.selectedSuiteIds, selectedConfigSources().map((source) => source.relativePath)),
    { force: true },
  );
}

function collectSuiteNodeSuiteIds(node) {
  if (!node) {
    return [];
  }
  return [
    node.suiteId,
    ...(node.children || []).flatMap(collectSuiteNodeSuiteIds),
  ].filter(Boolean);
}

function syncSuiteTreeCheckboxStates() {
  const selected = new Set(state.selectedSuiteIds);
  el.suiteList.querySelectorAll("[data-suite-checkbox]").forEach((input) => {
    const suiteIds = suiteIdsFromSuiteInput(input);
    const selectedCount = suiteIds.filter((suiteId) => selected.has(suiteId)).length;
    const checked = suiteIds.length > 0 && selectedCount === suiteIds.length;
    const partial = selectedCount > 0 && selectedCount < suiteIds.length;
    input.checked = checked;
    input.indeterminate = partial;
    input.closest(".suite-option")?.classList.toggle("is-partial", partial);
  });
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
  const selected = currentSelectedSuiteIds();
  if (total === 0) {
    el.suiteSummary.textContent = "无测试套";
    return;
  }
  if (selected.length === 0) {
    el.suiteSummary.textContent = "未选择测试套";
    return;
  }
  if (selected.length === total) {
    el.suiteSummary.textContent = `全部测试套 (${total})`;
    return;
  }
  if (selected.length === 1) {
    const suite = suites.find((item) => item.id === selected[0]);
    el.suiteSummary.textContent = suite ? suiteDisplayName(suite) : selected[0];
    return;
  }
  el.suiteSummary.textContent = `${selected.length}/${total} 已选`;
}

function currentSelectedSuiteIds() {
  if (!state.snapshot || !Array.isArray(state.snapshot.suites)) {
    return [];
  }
  const availableIds = state.snapshot.suites.map((suite) => suite.id);
  return state.selectedSuiteIds.filter((id) => availableIds.includes(id));
}

function suiteCommandLabel(selectedSuiteIds, yamlVars) {
  const targets = suiteTargetPathsForSelection(selectedSuiteIds);
  const suiteLabel = targets.length > 0
    ? targets.join(" ")
    : "<未选择测试套>";
  const args = yamlVars.length > 0
    ? ` ${yamlVars.map((item) => `--yaml-vars ${item}`).join(" ")}`
    : "";
  return `pytest ${suiteLabel}${args}`;
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
