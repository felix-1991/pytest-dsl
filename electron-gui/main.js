const path = require("node:path");
const { app, BrowserWindow, clipboard, dialog, ipcMain, Menu } = require("electron");

const {
  createProjectEntry,
  deleteProjectEntry,
  getProjectConfigSnapshot,
  getProjectSnapshot,
  moveProjectEntry,
  readProjectFile,
  renameProjectEntry,
  saveProjectFile
} = require("./src/services/projectService");
const {
  sendExecutionCommand,
  startExecutionTask,
  stopExecutionTask
} = require("./src/services/executionService");
const {
  defaultAllureReportExportName,
  defaultBuildLogExportName,
  exportAllureReportFile,
  exportBuildLogs,
  startBuildTask,
  stopBuildTask
} = require("./src/services/buildService");
const { checkRemoteServers } = require("./src/services/remoteStatusService");
const { listKeywords } = require("./src/services/keywordService");
const {
  findKeywordDefinitions,
  invalidateDefinitionCache,
  prefetchDefinitionCache,
  readSourceFile,
} = require("./src/services/keywordDefinitionService");
const {
  getRuntimeStatus,
  resetRuntimeExecutable,
  saveRuntimeExecutable
} = require("./src/services/runtimeConfigService");

const DEFAULT_PROJECT_ROOT = path.resolve(__dirname, "..");
const PYTHON_DIRECTORY_SELECTION_MODE = "python-directory";

function createWindow() {
  const window = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1120,
    minHeight: 720,
    title: "Pytest DSL Studio",
    backgroundColor: "#f5f7fb",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  });

  window.loadFile(path.join(__dirname, "src", "index.html"));
  return window;
}

// ---- Definition Child Windows ----

const definitionWindows = new Map();   // key: file path → BrowserWindow
const DEFINITION_WINDOW_LRU = [];
const MAX_DEFINITION_WINDOWS = 5;

function openDefinitionWindow(event, options) {
  const { projectRoot, definition } = options || {};
  if (!definition || !definition.path) {
    throw new Error("Invalid definition data");
  }

  const fileKey = definition.path;

  // Reuse existing window for the same source file
  let defWindow = definitionWindows.get(fileKey);
  if (defWindow && !defWindow.isDestroyed()) {
    defWindow.focus();
    defWindow.webContents.send("definition:data", {
      projectRoot,
      path: definition.path,
      line: definition.line,
      name: definition.name,
    });
    return { windowId: defWindow.id };
  }

  // Evict LRU window if at capacity
  if (definitionWindows.size >= MAX_DEFINITION_WINDOWS) {
    const oldest = DEFINITION_WINDOW_LRU.shift();
    if (oldest) {
      const oldestWindow = definitionWindows.get(oldest);
      if (oldestWindow && !oldestWindow.isDestroyed()) {
        oldestWindow.close();
      }
      definitionWindows.delete(oldest);
    }
  }

  // Create new definition window
  defWindow = new BrowserWindow({
    width: 900,
    height: 700,
    minWidth: 600,
    minHeight: 400,
    title: `定义: ${definition.name}`,
    parent: BrowserWindow.fromWebContents(event.sender),
    backgroundColor: "#0f172a",
    webPreferences: {
      preload: path.join(__dirname, "preload-definition.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  defWindow.loadFile(path.join(__dirname, "src", "definition-window.html"));

  defWindow.webContents.once("did-finish-load", () => {
    defWindow.webContents.send("definition:data", {
      projectRoot,
      path: definition.path,
      line: definition.line,
      name: definition.name,
    });
  });

  defWindow.on("closed", () => {
    definitionWindows.delete(fileKey);
    const idx = DEFINITION_WINDOW_LRU.indexOf(fileKey);
    if (idx >= 0) DEFINITION_WINDOW_LRU.splice(idx, 1);
  });

  definitionWindows.set(fileKey, defWindow);
  DEFINITION_WINDOW_LRU.push(fileKey);

  return { windowId: defWindow.id };
}

function closeAllDefinitionWindows() {
  definitionWindows.forEach((win) => {
    if (!win.isDestroyed()) win.close();
  });
  definitionWindows.clear();
  DEFINITION_WINDOW_LRU.length = 0;
}

function closeDefinitionWindow(event) {
  const win = BrowserWindow.fromWebContents(event.sender);
  if (win) win.close();
}

function registerIpc() {
  ipcMain.handle("project:open", async () => {
    const result = await dialog.showOpenDialog({
      title: "打开 pytest-dsl 项目",
      properties: ["openDirectory"]
    });

    if (result.canceled || result.filePaths.length === 0) {
      return null;
    }

    const snapshot = getProjectSnapshot(result.filePaths[0]);
    prefetchDefinitionCache(snapshot.project.rootPath);
    return snapshot;
  });

  ipcMain.handle("project:default", () => {
    const snapshot = getProjectSnapshot(DEFAULT_PROJECT_ROOT);
    prefetchDefinitionCache(DEFAULT_PROJECT_ROOT);
    return snapshot;
  });
  ipcMain.handle("project:scan", (_event, projectRoot) => {
    const snapshot = getProjectSnapshot(projectRoot);
    prefetchDefinitionCache(projectRoot);
    return snapshot;
  });
  ipcMain.handle("project:config", (_event, projectRoot) => getProjectConfigSnapshot(projectRoot));
  ipcMain.handle("file:read", (_event, projectRoot, relativePath) => readProjectFile(projectRoot, relativePath));
  ipcMain.handle("file:save", (_event, projectRoot, relativePath, content) => {
    const result = saveProjectFile(projectRoot, relativePath, content);
    if (shouldInvalidateDefinitionCache(relativePath)) {
      invalidateDefinitionCache(projectRoot);
    }
    return result;
  });
  ipcMain.handle("file:create", (_event, projectRoot, options) => {
    const result = createProjectEntry(projectRoot, options);
    if (shouldInvalidateDefinitionCache(options && options.relativePath)) {
      invalidateDefinitionCache(projectRoot);
    }
    return result;
  });
  ipcMain.handle("file:rename", (_event, projectRoot, options) => {
    const oldPath = options && options.relativePath;
    const newName = options && options.newName;
    const newPath = oldPath ? path.posix.join(path.posix.dirname(String(oldPath).replace(/\\/g, "/")), String(newName || "")) : null;
    const result = renameProjectEntry(projectRoot, options);
    if (shouldInvalidateDefinitionCache(oldPath) || shouldInvalidateDefinitionCache(newPath)) {
      invalidateDefinitionCache(projectRoot);
    }
    return result;
  });
  ipcMain.handle("file:move", (_event, projectRoot, options) => {
    const oldPath = options && options.relativePath;
    const newDir = options && options.targetDirectory;
    const result = moveProjectEntry(projectRoot, options);
    if (shouldInvalidateDefinitionCache(oldPath) || shouldInvalidateDefinitionCache(newDir)) {
      invalidateDefinitionCache(projectRoot);
    }
    return result;
  });
  ipcMain.handle("file:delete", (_event, projectRoot, options) => {
    const relativePath = options && options.relativePath;
    const result = deleteProjectEntry(projectRoot, options);
    if (shouldInvalidateDefinitionCache(relativePath)) {
      invalidateDefinitionCache(projectRoot);
    }
    return result;
  });
  ipcMain.handle("remote:check", (_event, servers) => checkRemoteServers(servers));
  ipcMain.handle("keyword:list", (_event, options = {}) => listKeywords({
    ...options,
    projectRoot: options.projectRoot || DEFAULT_PROJECT_ROOT
  }));
  ipcMain.handle("keyword:definition", (_event, options = {}) => findKeywordDefinitions({
    ...options,
    projectRoot: options.projectRoot || DEFAULT_PROJECT_ROOT
  }));
  ipcMain.handle("keyword:definition:invalidate", (_event, projectRoot) => {
    invalidateDefinitionCache(projectRoot || null);
    return { invalidated: true };
  });
  ipcMain.handle("source:read", (_event, options = {}) => readSourceFile(
    options.projectRoot || DEFAULT_PROJECT_ROOT,
    options.path
  ));
  ipcMain.handle("clipboard:write", (_event, text) => {
    clipboard.writeText(String(text || ""));
    return { copied: true };
  });
  ipcMain.handle("execution:start", (event, options) => (
    startExecutionTask(options, {
      onEvent(payload) {
        event.sender.send("execution:event", payload);
      }
    })
  ));
  ipcMain.handle("execution:command", (_event, taskId, command) => (
    sendExecutionCommand(taskId, command)
  ));
  ipcMain.handle("execution:stop", (_event, taskId) => stopExecutionTask(taskId));
  ipcMain.handle("build:start", (event, options) => (
    startBuildTask(options, {
      onEvent(payload) {
        event.sender.send("build:event", payload);
      }
    })
  ));
  ipcMain.handle("build:stop", (_event, buildId) => stopBuildTask(buildId));
  ipcMain.handle("build:download-report", async (event, options = {}) => {
    const result = await dialog.showSaveDialog(BrowserWindow.fromWebContents(event.sender), {
      title: "保存 Allure 报告",
      defaultPath: defaultAllureReportExportName(options.buildId || options.taskId),
      filters: [
        { name: "HTML", extensions: ["html"] },
        { name: "All Files", extensions: ["*"] },
      ],
    });
    if (result.canceled || !result.filePath) {
      return { canceled: true };
    }
    return exportAllureReportFile({
      ...options,
      destinationPath: result.filePath,
    });
  });
  ipcMain.handle("build:download-logs", async (event, options = {}) => {
    const result = await dialog.showSaveDialog(BrowserWindow.fromWebContents(event.sender), {
      title: "保存构建日志",
      defaultPath: defaultBuildLogExportName(options.buildId || options.taskId),
      filters: [
        { name: "Log Files", extensions: ["log", "txt"] },
        { name: "All Files", extensions: ["*"] },
      ],
    });
    if (result.canceled || !result.filePath) {
      return { canceled: true };
    }
    return exportBuildLogs({
      ...options,
      destinationPath: result.filePath,
    });
  });
  ipcMain.handle("runtime:status", (_event, options) => getRuntimeStatus(options));
  ipcMain.handle("runtime:select", async (event, options) => {
    const result = await dialog.showOpenDialog(BrowserWindow.fromWebContents(event.sender), {
      title: options.kind === "allure" ? "选择 Allure 3 可执行文件" : "选择 Python 解释器",
      defaultPath: options.projectRoot,
      properties: runtimeDialogProperties(options.kind, options.selectionMode),
    });
    if (result.canceled || result.filePaths.length === 0) return { canceled: true };
    saveRuntimeExecutable(options.projectRoot, options.kind, result.filePaths[0]);
    return getRuntimeStatus({ projectRoot: options.projectRoot });
  });
  ipcMain.handle("runtime:reset", (_event, options) => {
    resetRuntimeExecutable(options.projectRoot, options.kind);
    return getRuntimeStatus({ projectRoot: options.projectRoot });
  });

  // Definition child window IPC
  ipcMain.handle("window:open-definition", (event, options) => openDefinitionWindow(event, options));
  ipcMain.handle("window:close-all-definitions", () => {
    closeAllDefinitionWindows();
    return { closed: true };
  });
  ipcMain.handle("definition:close", (event) => closeDefinitionWindow(event));
}

function shouldInvalidateDefinitionCache(relativePath) {
  if (!relativePath) return false;
  const normalized = String(relativePath).replace(/\\/g, "/");
  return normalized.endsWith(".resource") || normalized.startsWith("keywords/");
}

function runtimeDialogProperties(kind, selectionMode) {
  if (kind !== "python") {
    return ["openFile"];
  }
  if (selectionMode === PYTHON_DIRECTORY_SELECTION_MODE || !selectionMode) {
    return ["openDirectory", "showHiddenFiles"];
  }
  return ["openDirectory", "showHiddenFiles"];
}

app.whenReady().then(() => {
  registerIpc();
  // 隐藏默认的应用菜单栏（File / Edit / View / Window / Help）
  Menu.setApplicationMenu(null);
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
