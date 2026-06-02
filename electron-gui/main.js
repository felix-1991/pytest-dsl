const path = require("node:path");
const { app, BrowserWindow, clipboard, dialog, ipcMain } = require("electron");

const {
  getProjectConfigSnapshot,
  getProjectSnapshot,
  readProjectFile,
  saveProjectFile
} = require("./src/services/projectService");
const {
  sendExecutionCommand,
  startExecutionTask,
  stopExecutionTask
} = require("./src/services/executionService");
const { checkRemoteServers } = require("./src/services/remoteStatusService");
const { listKeywords } = require("./src/services/keywordService");
const {
  findKeywordDefinitions,
  readSourceFile
} = require("./src/services/keywordDefinitionService");

const DEFAULT_PROJECT_ROOT = path.resolve(__dirname, "..");

function createWindow() {
  const window = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1120,
    minHeight: 720,
    title: "pytest-dsl Local Workbench",
    backgroundColor: "#f5f7fb",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  });

  window.loadFile(path.join(__dirname, "src", "index.html"));
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

    return getProjectSnapshot(result.filePaths[0]);
  });

  ipcMain.handle("project:default", () => getProjectSnapshot(DEFAULT_PROJECT_ROOT));
  ipcMain.handle("project:scan", (_event, projectRoot) => getProjectSnapshot(projectRoot));
  ipcMain.handle("project:config", (_event, projectRoot) => getProjectConfigSnapshot(projectRoot));
  ipcMain.handle("file:read", (_event, projectRoot, relativePath) => readProjectFile(projectRoot, relativePath));
  ipcMain.handle("file:save", (_event, projectRoot, relativePath, content) => (
    saveProjectFile(projectRoot, relativePath, content)
  ));
  ipcMain.handle("remote:check", (_event, servers) => checkRemoteServers(servers));
  ipcMain.handle("keyword:list", (_event, options = {}) => listKeywords({
    ...options,
    projectRoot: options.projectRoot || DEFAULT_PROJECT_ROOT
  }));
  ipcMain.handle("keyword:definition", (_event, options = {}) => findKeywordDefinitions({
    ...options,
    projectRoot: options.projectRoot || DEFAULT_PROJECT_ROOT
  }));
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
}

app.whenReady().then(() => {
  registerIpc();
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
